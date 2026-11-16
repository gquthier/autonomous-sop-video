"""Functional invariants; run: python3 -m unittest discover -s tests -v."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sop', ROOT / 'scripts/sop.py')
sop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sop)


class SOPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve() / 'project'
        shutil.copytree(ROOT / 'assets/starter', self.root)
        self.path = self.root / 'sop.json'
        self.data = json.loads(self.path.read_text())

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.path.write_text(json.dumps(self.data))

    def assert_invalid(self, expected):
        self.save()
        with self.assertRaisesRegex(ValueError, expected):
            sop.validate(self.path)

    @unittest.skipUnless(shutil.which('node'), 'Node required for differential preflight')
    def test_python_node_shared_adversarial_corpus(self):
        original = copy.deepcopy(self.data)
        cases = [
            (('title',), 'A\x00B', False), (('title',), '\ufeff', False),
            (('title',), 'A\tB\nC', True), (('title',), 'bad\ud800', False),
            (('series',), 'x'*101, False),
            (('screenshots',0,'capturedAt'), '0000-01-01', False),
            (('screenshots',0,'capturedAt'), '2024-02-29', True),
            (('screenshots',0,'path'), './'+original['screenshots'][0]['path'], False),
            (('screenshots',0,'path'), 'assets//screenshots/demo-1.svg', False),
            (('steps',0,'zoom'), None, False), (('steps',0,'voice'), None, False),
            (('steps',0,'captions'), [{'start':.0044,'end':.0045,'text':'half-up rounding'}], True),
            (('steps',0,'captions'), [{'start':.0041,'end':.0044,'text':'collapsed cue'}], False),
            (('steps',0,'tip'), 'x'*181, False),
        ]
        script = "import {validate} from './validate.mjs'; import {readFileSync} from 'node:fs'; try {validate(JSON.parse(readFileSync('sop.json','utf8')),process.cwd())} catch(e) {console.error(e.message);process.exit(1)}"
        for path, value, expected in cases:
            with self.subTest(path=path, value=repr(value)):
                self.data=copy.deepcopy(original); target=self.data
                for key in path[:-1]: target=target[key]
                target[path[-1]]=value; self.save()
                try: sop.validate(self.path); python_ok=True
                except ValueError: python_ok=False
                node=subprocess.run(['node','--input-type=module','-e',script],cwd=self.root,capture_output=True,text=True)
                self.assertEqual(python_ok,expected)
                self.assertEqual(node.returncode==0,expected,node.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node required for SVG differential preflight')
    def test_svg_stroke_width_is_not_native_width(self):
        shot=self.data['screenshots'][0]
        image=self.root / shot['path']
        image.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" stroke-width="1" width="{shot["width"]}" height="{shot["height"]}"></svg>')
        sop.validate(self.path)
        script="import {validate} from './validate.mjs'; import {readFileSync} from 'node:fs'; validate(JSON.parse(readFileSync('sop.json','utf8')),process.cwd())"
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_real_starter_timeline_and_dimensions(self):
        _, report = sop.validate(self.path)
        self.assertEqual(report['duration'], 24)
        self.assertEqual([c['start'] for c in report['timeline']], [0, 8, 16])
        self.assertEqual([c['start'] for c in report['captions']], [.5, 8.5, 16.5])

    def test_duplicate_ids_rejected(self):
        self.data['steps'][1]['id'] = self.data['steps'][0]['id']
        self.assert_invalid('unique')

    def test_native_target_bounds(self):
        self.data['steps'][0]['target']['x'] = 1439
        self.assert_invalid('outside native screenshot')

    def test_source_dimension_mismatch(self):
        self.data['screenshots'][0]['width'] = 1600
        self.assert_invalid('declared dimensions')

    def test_traversal_and_symlink_escape(self):
        self.data['screenshots'][0]['path'] = '../outside.svg'
        self.assert_invalid('relative project paths')
        outside = Path(self.temp.name) / 'outside.svg'
        outside.write_text('<svg width="1440" height="810"/>')
        (self.root / 'link.svg').symlink_to(outside)
        self.data['screenshots'][0]['path'] = 'link.svg'
        self.assert_invalid('out-of-project')

    def test_caption_boundaries_and_overlap(self):
        self.data['steps'][0]['captions'][0]['end'] = 8.01
        self.assert_invalid('exceed the step')
        self.data['steps'][0]['captions'][0]['end'] = 7
        self.data['steps'][0]['captions'].append({'start':6, 'end':7.5, 'text':'Overlap'})
        self.assert_invalid('overlap')

    def test_silent_mode_does_not_claim_a_voice(self):
        self.data['narration']['mode'] = 'provided'
        self.assert_invalid('require a voice asset')

    def test_captions_and_chapter_export_agree(self):
        out = self.root / 'delivery'
        report = sop.export(self.path, out)
        self.assertEqual(len(report['timeline']), 3)
        self.assertIn('00:00:08.500 --> 00:00:15.700', (out/'captions.vtt').read_text())
        self.assertIn('00:00:08,500 --> 00:00:15,700', (out/'captions.srt').read_text())
        metadata = (out/'chapters.ffmetadata').read_text()
        self.assertIn('START=16000\nEND=24000', metadata)
        self.assertEqual(metadata.count('[CHAPTER]'), 3)

    def test_malformed_nested_shapes_raise_helpful_value_errors(self):
        original = copy.deepcopy(self.data)
        cases = [
            ((), []), (('canvas',), []), (('narration',), None),
            (('narration', 'mode'), []), (('screenshots',), {}),
            (('screenshots', 0), []), (('screenshots', 0, 'id'), {}),
            (('screenshots', 0, 'kind'), []), (('steps',), {}),
            (('steps', 0), None), (('steps', 0, 'id'), 4),
            (('steps', 0, 'checklist', 0), 'text'),
            (('steps', 0, 'checklist', 0, 'state'), []),
            (('steps', 0, 'target'), []), (('steps', 0, 'screenshot'), {}),
            (('steps', 0, 'voice'), []), (('steps', 0, 'voice'), None),
            (('steps', 0, 'captions'), 'text'),
            (('steps', 0, 'captions', 0), None),
            (('steps', 0, 'tip'), {}), (('steps', 0, 'zoom'), None),
            (('series',), []),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                self.data = copy.deepcopy(original)
                if not path:
                    self.data = value
                else:
                    target = self.data
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                self.assert_invalid('expected|must|require')

    def test_strict_version_canvas_and_calendar_dates(self):
        for value in (True, 1.0, '1'):
            self.data['version'] = value
            self.assert_invalid('version')
        self.data['version'] = 1
        for key in ('width', 'height', 'fps'):
            original = self.data['canvas'][key]
            for value in (True, float(original)):
                self.data['canvas'][key] = value
                self.assert_invalid('canvas')
            self.data['canvas'][key] = original
        for value in ('2025-02-29', '2024-04-31', '0000-01-01', '2024-13-01', '2024-1-01'):
            self.data['screenshots'][0]['capturedAt'] = value
            self.assert_invalid('valid calendar date')
        self.data['screenshots'][0]['capturedAt'] = '2024-02-29'
        self.save()
        sop.validate(self.path)

    def test_unsafe_numbers_and_precision(self):
        for value in (True, float('nan'), float('inf'), -float('inf'), 10**400, 1e308):
            self.data['steps'][0]['duration'] = value
            self.assert_invalid('finite|safe millisecond')
            with self.assertRaises(ValueError):
                sop.timestamp(value)
        self.data['steps'][0]['duration'] = 8
        self.data['steps'][0]['captions'][0].update(start=.50001, end=.50002)
        self.assert_invalid('millisecond')
        self.data['steps'][0]['captions'][0].update(start=.5, end=7)
        for step in self.data['steps']:
            step['duration'] = sop.MAX_TIME / 2
        self.assert_invalid('cumulative duration')

    def test_voice_volume_and_optional_fields(self):
        audio = self.root / 'voice.wav'
        audio.write_bytes(b'placeholder; no probing in this test')
        self.data['narration']['mode'] = 'provided'
        for step in self.data['steps']:
            step['voice'] = {'path': 'voice.wav', 'duration': 1}
        for value in (True, None, [], -1, 1.01, float('nan'), 10**400):
            self.data['steps'][0]['voice']['volume'] = value
            self.assert_invalid('voice.volume')
        for value in (0, 1):
            self.data['steps'][0]['voice']['volume'] = value
            self.save()
            sop.validate(self.path)
        self.data['steps'][0].pop('tip', None)
        self.data['steps'][0].pop('zoom', None)
        self.save()
        sop.validate(self.path)

    def test_literal_export_text_cannot_inject_cues_or_chapters(self):
        text = '<b>A & B</b>\r\n\n00:00:01.000 --> 00:00:02.000\tInjected\u2028line'
        self.data['steps'][0]['captions'][0]['text'] = text
        self.data['steps'][0]['chapter'] = text + '\n[CHAPTER]\nkey=val;#\\'
        self.save()
        out = self.root / 'delivery'
        sop.export(self.path, out)
        for name in ('captions.vtt', 'captions.srt', 'chapters.vtt'):
            result = (out / name).read_text()
            self.assertIn('&lt;b&gt;A &amp; B&lt;/b&gt;', result)
            self.assertIn('--&gt;', result)
            self.assertNotIn('\x00', result)
            self.assertEqual(result.count(' --> '), 3)
        metadata = (out / 'chapters.ffmetadata').read_text()
        self.assertEqual(metadata.count('\n[CHAPTER]\n'), 3)
        self.assertIn('key\\=val\\;\\#\\\\', metadata)
        self.assertEqual(len((out / 'chapters.txt').read_text().splitlines()), 3)

    def test_export_no_clobber_and_symlink_destinations(self):
        out = self.root / 'delivery'
        sop.export(self.path, out)
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        with self.assertRaisesRegex(ValueError, 'existing destination'):
            sop.export(self.path, out)
        self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})
        for target in (self.path, self.root / self.data['screenshots'][0]['path']):
            destination = self.root / ('export-' + target.suffix[1:])
            destination.mkdir()
            (destination / 'captions.srt').symlink_to(target)
            original = target.read_bytes()
            with self.assertRaises(ValueError):
                sop.export(self.path, destination)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(len(list(destination.iterdir())), 1)
        outside = Path(self.temp.name).resolve() / 'outside'
        outside.mkdir()
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        for destination in (self.root / 'linked', self.root / 'linked/nested'):
            with self.assertRaises(ValueError):
                sop.export(self.path, destination)
        self.assertEqual(list(outside.iterdir()), [])
        dangling = self.root / 'dangling'
        dangling.mkdir()
        (dangling / 'captions.srt').symlink_to(outside / 'missing')
        with self.assertRaises(ValueError):
            sop.export(self.path, dangling)
        self.assertFalse((outside / 'missing').exists())

    def test_text_requires_visible_valid_unicode(self):
        for value in ('\x00\r\n\t', '\ud800'):
            self.data['steps'][0]['captions'][0]['text'] = value
            self.assert_invalid('text|Unicode')

    def test_manifest_destination_and_hardlink_are_never_overwritten(self):
        destination = self.root / 'collision'
        destination.mkdir()
        renamed = destination / 'captions.srt'
        renamed.write_text(json.dumps(self.data))
        # Assets are relative to the manifest directory: copy the fixture references.
        shutil.copytree(self.root / 'assets', destination / 'assets')
        before = renamed.read_bytes()
        with self.assertRaisesRegex(ValueError, 'existing destination'):
            sop.export(renamed, destination)
        self.assertEqual(renamed.read_bytes(), before)
        other = self.root / 'hardlinked'
        other.mkdir()
        (other / 'validation.json').hardlink_to(self.path)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            sop.export(self.path, other)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(list(other.iterdir())), 1)

    def test_malformed_svg_viewbox_is_value_error(self):
        screen = self.data['screenshots'][0]
        image = self.root / screen['path']
        for value in ('0 0 100', '0 0 NaN 810', '0 0 1440 Infinity'):
            image.write_text(f'<svg viewBox="{value}"/>')
            self.assert_invalid('invalid SVG dimensions')

    def test_init_refuses_existing_data(self):
        result = subprocess.run(['python3', str(ROOT/'scripts/sop.py'), 'init', str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.path.is_file())

    @unittest.skipUnless(shutil.which('ffprobe'), 'ffprobe not installed')
    def test_measured_audio_duration_and_clipping(self):
        voice_dir = self.root / 'assets/voice'
        voice_dir.mkdir()
        with wave.open(str(voice_dir/'test.wav'), 'w') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            stream.writeframes(b'\0\0' * 16000)
        self.data['narration']['mode'] = 'provided'
        for step in self.data['steps']:
            step['voice'] = {'path':'assets/voice/test.wav', 'offset':.5, 'duration':1}
        self.save()
        self.assertTrue(sop.validate(self.path, probe=True)[1]['mediaProbed'])
        self.data['steps'][0]['voice']['duration'] = 1.5
        self.save()
        with self.assertRaisesRegex(ValueError, 'differs from ffprobe'):
            sop.validate(self.path, probe=True)
        self.data['steps'][0]['voice']['duration'] = 7.5
        self.assert_invalid('clipped')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools not installed')
    def test_embedded_mp4_chapters_are_readable(self):
        out = self.root / 'delivery'
        sop.export(self.path, out)
        source, final = self.root/'source.mp4', self.root/'chaptered.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=white:s=64x64:r=1:d=24','-c:v','libx264','-pix_fmt','yuv420p',str(source)], check=True)
        subprocess.run(['python3',str(ROOT/'scripts/sop.py'),'embed',str(source),str(out/'chapters.ffmetadata'),str(final)], check=True, capture_output=True)
        chapters = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_chapters','-of','json',str(final)],text=True))['chapters']
        self.assertEqual(len(chapters), 3)
        self.assertEqual([float(c['start_time']) for c in chapters], [0,8,16])
        self.assertEqual(float(chapters[-1]['end_time']), 24)
        self.assertEqual(chapters[-1]['tags']['title'], 'Contrôler le résultat')

    @unittest.skipUnless(shutil.which('node'), 'Node not installed')
    def test_generator_builds_real_assets_and_timing(self):
        if not (self.root / 'node_modules/gsap/dist/gsap.min.js').is_file():
            if not shutil.which('npm'):
                self.skipTest('npm not installed; required to provision locked build dependency')
            # Explicit offline install only: never fetch dependencies during unit tests.
            subprocess.run(['npm', 'ci', '--offline', '--ignore-scripts', '--no-audit', '--no-fund'],
                           cwd=self.root, check=True, capture_output=True)
        subprocess.run(['node','build.mjs'],cwd=self.root,check=True,capture_output=True)
        output = json.loads((self.root/'timeline.json').read_text())
        self.assertEqual(output['duration'],24)
        self.assertEqual(output['steps'][-1]['start'],16)
        html = (self.root/'index.html').read_text()
        self.assertNotIn('<audio',html)
        self.assertIn('data-duration="24"',html)
        self.assertEqual(html.count('class="screenshot"'),3)


if __name__ == '__main__':
    unittest.main()
