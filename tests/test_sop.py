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
        self.root = Path(self.temp.name) / 'project'
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
