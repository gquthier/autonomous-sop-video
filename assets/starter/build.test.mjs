import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, cpSync, readFileSync, writeFileSync, symlinkSync, rmSync, existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';

const source = fileURLToPath(new URL('.', import.meta.url));
const manifest = JSON.parse(readFileSync(join(source, 'sop.json'), 'utf8'));
function fixture(fn) {
  const root = mkdtempSync(join(tmpdir(), 'sop-build-test-'));
  try {
    for (const file of ['build.mjs', 'validate.mjs', 'assets']) cpSync(join(source, file), join(root, file), {recursive:true});
    if (existsSync(join(source, 'node_modules/gsap'))) cpSync(join(source, 'node_modules/gsap'), join(root, 'node_modules/gsap'), {recursive:true});
    const data = structuredClone(manifest);
    const run = () => { writeFileSync(join(root, 'sop.json'), JSON.stringify(data)); return spawnSync(process.execPath, [join(root, 'build.mjs')], {encoding:'utf8', cwd:tmpdir()}); };
    return fn({root, data, run});
  } finally {
    // root is a freshly created, absolute mkdtemp child, never manifest-controlled.
    assert.ok(resolve(root).startsWith(resolve(tmpdir()) + '/sop-build-test-'));
    rmSync(root, {recursive:true, force:true});
  }
}
function buildOK(run) { const p = run(); assert.equal(p.status, 0, p.stderr); }
function motion(html) { return JSON.parse(html.match(/for \(const shot of (\[[^\n]+\])\) \{/)[1]); }

test('offline deterministic build, local script, seek-safe geometry and animation bounds', () => fixture(({root, data, run}) => {
  data.steps[2].zoom = 3; // Pressure-test wide targets, not just the bundled 1.3× view.
  buildOK(run);
  const first = readFileSync(join(root, 'index.html'), 'utf8');
  assert.match(first, /src="\.\/node_modules\/gsap\/dist\/gsap.min.js"/);
  assert.doesNotMatch(first, /<script[^>]*src="https?:/);
  const shots = motion(first);
  for (const [i, shot] of shots.entries()) {
    const target = data.steps[i].target;
    const screen = data.screenshots.find(s => s.id === data.steps[i].screenshot);
    const scale = Math.min(1200/screen.width,675/screen.height);
    const x = (1200-screen.width*scale)/2+target.x*scale;
    const y = (675-screen.height*scale)/2+target.y*scale;
    assert.ok(x*shot.zoom+shot.pan.x >= -1e-7);
    assert.ok(y*shot.zoom+shot.pan.y >= -1e-7);
    assert.ok((x+target.width*scale)*shot.zoom+shot.pan.x <= 1200+1e-7);
    assert.ok((y+target.height*scale)*shot.zoom+shot.pan.y <= 675+1e-7);
  }
  assert.ok(shots[2].zoom < 3, 'requested 3× zoom must not crop the wide target');
  assert.doesNotMatch(first, /fromTo\([^\n]*scene-inner/, 'scene content must be visible at exact cut boundaries');
  // Exercise generated animation wiring without needing a browser/network.
  const ends = [];
  const timeline = {fromTo(_target,_from,to,at) { ends.push(at+to.duration); return this; }};
  const script = first.match(/<script>\n([\s\S]+?)<\/script>/)[1];
  const window = {__timelines:{}};
  vm.runInNewContext(script, {gsap:{timeline:() => timeline}, window});
  assert.equal(window.__timelines.main, timeline);
  assert.ok(Math.max(...ends) <= 24+1e-7);
  buildOK(run); assert.equal(readFileSync(join(root, 'index.html'), 'utf8'), first);
}));

const invalid = {
  'unsafe ID': d => {d.steps[0].id='a" onclick="bad';},
  'duplicate ID': d => {d.steps[1].id=d.steps[0].id;},
  'duplicate screenshot': d => {d.screenshots.push(d.screenshots[0]);},
  'unsupported canvas': d => {d.canvas.width=1080;},
  'string duration': d => {d.steps[0].duration='8';},
  'empty checklist': d => {d.steps[0].checklist=[];},
  'unknown screenshot': d => {d.steps[0].screenshot='nope';},
  'target outside image': d => {d.steps[0].target.x=2000;},
  'zero zoom': d => {d.steps[0].zoom=0;},
  'wrong native dimensions': d => {d.screenshots[0].width=1400;},
  'overlapping captions': d => {d.steps[0].captions.push({...d.steps[0].captions[0]});},
  'caption exceeds scene': d => {d.steps[0].captions[0].end=20;},
  'sub-millisecond caption': d => {d.steps[0].captions=[{start:0,end:.00001,text:'too short'}];},
  'non-boolean redaction': d => {d.screenshots[0].redacted='yes';},
  'lone surrogate title': d => {d.steps[0].title='bad\ud800';},
  'invalid captured date': d => {d.screenshots[0].capturedAt='2026-02-30';},
  'unreviewed real capture': d => {d.screenshots[0].kind='capture';d.screenshots[0].redacted=false;},
  'URL screenshot': d => {d.screenshots[0].path='https://example.invalid/a.svg';},
  'traversal screenshot': d => {d.screenshots[0].path='../a.svg';},
  'backslash screenshot': d => {d.screenshots[0].path='assets\\screenshots\\demo-1.svg';},
  'missing voice': d => {d.narration.mode='provided';},
  'silent mode with voice': d => {d.steps[0].voice={path:'assets/x.wav',duration:1};},
};
for (const [name, mutate] of Object.entries(invalid)) test(`reject ${name} before overwriting outputs`, () => fixture(({root,data,run}) => {
  mutate(data);
  writeFileSync(join(root, 'index.html'), 'sentinel html'); writeFileSync(join(root, 'timeline.json'), 'sentinel json');
  const p = run(); assert.notEqual(p.status, 0); assert.match(p.stderr, /Invalid manifest:/);
  assert.equal(readFileSync(join(root, 'index.html'), 'utf8'), 'sentinel html');
  assert.equal(readFileSync(join(root, 'timeline.json'), 'utf8'), 'sentinel json');
}));

test('encode filename URL metacharacters and escape text/attributes', () => fixture(({root,data,run}) => {
  const path = 'assets/screenshots/a #?%"&.svg';
  cpSync(join(root, data.screenshots[0].path), join(root, path)); data.screenshots[0].path=path;
  data.steps[0].title='<x "&\'>';
  buildOK(run);
  const html = readFileSync(join(root, 'index.html'), 'utf8');
  assert.match(html, /a%20%23%3F%25%22%26\.svg/);
  assert.match(html, /&lt;x &quot;&amp;&#39;&gt;/);
}));

test('reject symlink escape and redirected generated output', () => fixture(({root,data,run}) => {
  symlinkSync('/etc/hosts', join(root, 'assets/outside.svg')); data.screenshots[0].path='assets/outside.svg';
  assert.match(run().stderr, /asset escapes project/);
  data.screenshots[0].path=manifest.screenshots[0].path;
  symlinkSync(join(root, 'sop.json'), join(root, 'index.html'));
  assert.match(run().stderr, /Unsafe generated output/);
}));

test('reject manifest alias to generated output without changing source', () => fixture(({root,data}) => {
  const original = JSON.stringify(data);
  writeFileSync(join(root,'index.html'),original);
  symlinkSync(join(root,'index.html'),join(root,'sop.json'));
  const p=spawnSync(process.execPath,[join(root,'build.mjs')],{encoding:'utf8'});
  assert.notEqual(p.status,0); assert.match(p.stderr,/aliases an input/);
  assert.equal(readFileSync(join(root,'sop.json'),'utf8'),original);
  assert.equal(existsSync(join(root,'timeline.json')),false);
}));

test('short scenes complete motion before trailing hold', () => fixture(({root,data,run}) => {
  for (const step of data.steps) {step.duration=2;step.captions=[{start:0,end:1.9,text:'Short example'}];}
  buildOK(run);
  for (const s of motion(readFileSync(join(root, 'index.html'),'utf8'))) assert.ok(2.1*s.pace <= s.duration-.25+1e-9);
}));

for (const [width,height,target] of [[800,1600,{x:0,y:0,width:800,height:1600}], [2000,500,{x:1800,y:400,width:200,height:100}], [100,100,{x:1,y:1,width:1,height:1}]]) {
  test(`target fits under zoom for ${width}×${height}`, () => fixture(({root,data,run}) => {
    const shot=data.screenshots[0];
    shot.width=width;shot.height=height;
    writeFileSync(join(root,shot.path),`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"></svg>`);
    data.steps[0].target=target;data.steps[0].zoom=3;
    buildOK(run);
    const s=motion(readFileSync(join(root,'index.html'),'utf8'))[0];
    const scale=Math.min(1200/width,675/height);
    const x=(1200-width*scale)/2+target.x*scale,y=(675-height*scale)/2+target.y*scale;
    assert.ok(x*s.zoom+s.pan.x>=-1e-7 && y*s.zoom+s.pan.y>=-1e-7);
    assert.ok((x+target.width*scale)*s.zoom+s.pan.x<=1200+1e-7);
    assert.ok((y+target.height*scale)*s.zoom+s.pan.y<=675+1e-7);
  }));
}

test('missing/corrupted local GSAP fails with actionable offline preflight', () => fixture(({root,run}) => {
  if (existsSync(join(root, 'node_modules/gsap/dist/gsap.min.js'))) writeFileSync(join(root, 'node_modules/gsap/dist/gsap.min.js'), 'corrupt');
  const p=run(); assert.notEqual(p.status,0); assert.match(p.stderr, /Local GSAP 3.12.7 preflight failed/); assert.match(p.stderr, /npm ci/);
}));


test('measured local narration, offset, volume and trailing hold', t => {
  if (spawnSync('ffprobe', ['-version'], {encoding:'utf8'}).status !== 0) return t.skip('ffprobe not installed');
  fixture(({root,data,run}) => {
    // Original one-second silent PCM fixture, no voice synthesis or downloads.
    const wav = Buffer.alloc(44+16000);
    wav.write('RIFF'); wav.writeUInt32LE(wav.length-8,4); wav.write('WAVEfmt ',8);
    wav.writeUInt32LE(16,16); wav.writeUInt16LE(1,20); wav.writeUInt16LE(1,22);
    wav.writeUInt32LE(8000,24); wav.writeUInt32LE(16000,28); wav.writeUInt16LE(2,32); wav.writeUInt16LE(16,34);
    wav.write('data',36); wav.writeUInt32LE(16000,40);
    writeFileSync(join(root,'assets/voice.wav'),wav);
    data.narration.mode='provided';
    for (const step of data.steps) step.voice={path:'assets/voice.wav',offset:0,duration:1,volume:0};
    buildOK(run);
    const html=readFileSync(join(root,'index.html'),'utf8');
    assert.match(html, /data-start="0" data-duration="1" data-track-index="3" data-volume="0"/);
    data.steps[0].voice.duration=.5;
    assert.match(run().stderr,/voice duration does not match ffprobe/);
    data.steps[0].voice.duration=1; data.steps[0].voice.offset=7;
    assert.match(run().stderr,/trailing hold/);
    data.steps[0].voice.offset=0; data.steps[0].voice.volume=2;
    assert.match(run().stderr,/voice.volume/);
    data.steps[0].voice.volume=0;
    for (const field of ['offset','volume']) {
      const original=data.steps[0].voice[field]; data.steps[0].voice[field]=null;
      assert.match(run().stderr,new RegExp(`voice.${field}`)); data.steps[0].voice[field]=original;
    }
    // A valid WAV may have any suffix: never let output generation destroy it.
    writeFileSync(join(root,'index.html'),wav);
    for (const step of data.steps) step.voice.path='index.html';
    const aliased=run(); assert.notEqual(aliased.status,0); assert.match(aliased.stderr,/aliases an input/);
    assert.deepEqual(readFileSync(join(root,'index.html')),wav);
  });
});
