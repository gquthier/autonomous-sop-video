// Deterministic local build. See THIRD_PARTY.md for the pinned GSAP preflight.
import { readFileSync, writeFileSync, lstatSync, realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { validate, assetURL, asset } from './validate.mjs';
const root = fileURLToPath(new URL('.', import.meta.url));
const data = validate(JSON.parse(readFileSync(new URL('./sop.json', import.meta.url), 'utf8')), root);
// Resolve from this project only, not an unrelated ancestor node_modules directory.
const gsapPath = 'node_modules/gsap/dist/gsap.min.js';
let gsapSource;
try {
  const meta = JSON.parse(readFileSync(asset(root, 'node_modules/gsap/package.json'), 'utf8'));
  gsapSource = readFileSync(asset(root, gsapPath));
  if (meta.version !== '3.12.7' || createHash('sha256').update(gsapSource).digest('hex') !== '5468a19b889d234135baaad67b35ac892701f45fe3328b27eeab3aa4f4a479a7') throw new Error('pinned GSAP artifact differs');
} catch (error) {
  throw new Error(`Local GSAP 3.12.7 preflight failed: ${error.message}. Run npm ci --ignore-scripts --no-audit --no-fund (add --offline to prohibit downloads). No build-time downloads are performed.`);
}
// Refuse input/output aliases, redirected or shared outputs before either write.
const inputPaths = new Set(['sop.json', 'build.mjs', 'validate.mjs', 'node_modules/gsap/package.json', gsapPath,
  ...data.screenshots.map(s => s.path), ...data.steps.filter(s => s.voice).map(s => s.voice.path)
].map(path => asset(root, path)));
for (const name of ['index.html', 'timeline.json']) {
  const output = new URL(name, import.meta.url);
  if (inputPaths.has(fileURLToPath(output))) throw new Error(`Generated output aliases an input: ${name}`);
  try { const s = lstatSync(output); if (!s.isFile() || s.nlink !== 1 || realpathSync(output) !== fileURLToPath(output)) throw new Error(`Unsafe generated output: ${name}`); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}
if (process.argv.includes('--preflight')) { console.log(JSON.stringify({ok:true, preflight:true, gsap:'3.12.7', steps:data.steps.length})); process.exit(0); }
const seconds = value => Number(value.toFixed(9));
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json = value => JSON.stringify(value).replace(/</g, '\\u003c');
const screens = Object.fromEntries(data.screenshots.map(s => [s.id, s]));
const W = 1200, H = 675;
let cursor = 0;
const timeline = data.steps.map(s => { const item = {...s, start: seconds(cursor)}; cursor = seconds(cursor + s.duration); return item; });
const total = cursor;
const frames = [], captions = [], voices = [], motion = [];
for (const [i, step] of timeline.entries()) {
  const shot = screens[step.screenshot];
  if (!shot) throw new Error(`Missing screenshot: ${step.screenshot}`);
  const scale = Math.min(W / shot.width, H / shot.height);
  const fittedW = shot.width * scale, fittedH = shot.height * scale;
  const ox = (W - fittedW) / 2, oy = (H - fittedH) / 2;
  const rect = { x: ox + step.target.x * scale, y: oy + step.target.y * scale, w: step.target.width * scale, h: step.target.height * scale };
  const halo = {x: Math.max(0, rect.x - 7), y: Math.max(0, rect.y - 7)};
  halo.w = Math.min(W, rect.x + rect.w + 7) - halo.x;
  halo.h = Math.min(H, rect.y + rect.h + 7) - halo.y;
  // Requested zoom is a ceiling: preserve the target rather than cropping it.
  const zoom = Math.max(1, Math.min(step.zoom ?? 1.5, W / (rect.w + 14), H / (rect.h + 14)));
  const pace = Math.min(1, (step.duration - .25) / 2.1);
  // Clamp the pan so the camera covers the viewport while keeping the target centered.
  const pan = {x: Math.min(0, Math.max(W * (1 - zoom), W / 2 - (rect.x + rect.w / 2) * zoom)), y: Math.min(0, Math.max(H * (1 - zoom), H / 2 - (rect.y + rect.h / 2) * zoom))};
  const prefix = `step-${step.id}`;
  const sourceLabel = shot.kind === 'synthetic' ? 'Interface fictive · exemple de démonstration' : `Capture réelle · ${shot.capturedAt}`;
  frames.push(`<section id="${prefix}" class="clip scene" data-start="${step.start}" data-duration="${step.duration}" data-track-index="1">
    <div class="scene-inner">
      <div class="eyebrow">${esc(data.series || 'PROCÉDURE PAS À PAS')} <span>${String(i+1).padStart(2,'0')} / ${String(timeline.length).padStart(2,'0')}</span></div>
      <h1>${esc(step.title)}</h1>
      <div class="viewport"><div id="${prefix}-camera" class="camera" data-layout-allow-overflow="true">
        <img class="screenshot" src="${esc(assetURL(shot.path))}" alt="${esc(step.title)}" style="left:${ox}px;top:${oy}px;width:${fittedW}px;height:${fittedH}px" />
        <div id="${prefix}-halo" class="halo" style="left:${halo.x}px;top:${halo.y}px;width:${halo.w}px;height:${halo.h}px"></div>
        <svg id="${prefix}-cursor" class="cursor" style="left:${rect.x+rect.w*.72}px;top:${rect.y+rect.h*.66}px" viewBox="0 0 36 44" aria-hidden="true"><path d="M4 3L4 33L13 25L19 39L25 36L19 23L31 23Z" fill="#1565D8" stroke="#fff" stroke-width="3"/></svg>
      </div></div>
      <div class="capture-label">${esc(sourceLabel)}</div>
      <aside><div class="step-label">À FAIRE</div><h2>${esc(step.instruction)}</h2><ul>${step.checklist.map(item => `<li class="${esc(item.state)}"><span class="marker">${item.state === 'done' ? '✓' : item.state === 'current' ? '→' : '○'}</span><span>${esc(item.text)}</span></li>`).join('')}</ul><div class="tip">${esc(step.tip || 'Mettez la vidéo en pause pour reproduire cette étape.')}</div></aside>
    </div>
  </section>`);
  motion.push({id: prefix, start: step.start, duration: step.duration, zoom, pan, pace});
  if (step.voice) voices.push(`<audio id="${prefix}-voice" class="clip" src="${esc(assetURL(step.voice.path))}" data-start="${seconds(step.start + (step.voice.offset ?? .5))}" data-duration="${step.voice.duration}" data-track-index="3" data-volume="${step.voice.volume ?? .88}"></audio>`);
  for (const [j, c] of step.captions.entries()) captions.push(`<div id="${prefix}-caption-${j}" class="clip caption" data-start="${seconds(step.start+c.start)}" data-duration="${seconds(c.end-c.start)}" data-track-index="4"><span>${esc(c.text)}</span></div>`);
}
const html = `<!doctype html>
<html lang="${esc(data.language)}" data-resolution="landscape"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080"><title>${esc(data.title)}</title>
<!-- GSAP 3.12.7 © 2025 GreenSock; Standard license: https://gsap.com/standard-license -->
<script src="${assetURL(gsapPath)}"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}html,body{width:1920px;height:1080px;overflow:hidden;background:#fff;font-family:system-ui,sans-serif;color:#102A43}#root{position:relative;width:100%;height:100%;overflow:hidden}#background{position:absolute;inset:0;background:#fff}.scene{position:absolute;inset:0}.scene-inner{position:absolute;inset:0}.eyebrow{position:absolute;left:80px;top:40px;right:80px;font-size:20px;font-weight:650;letter-spacing:2px;color:#1565D8}.eyebrow span{float:right}h1{position:absolute;left:80px;top:86px;width:1760px;font-size:48px;font-weight:700;line-height:1.12;color:#1565D8}.viewport{position:absolute;left:80px;top:177px;width:1200px;height:675px;overflow:hidden;outline:2px solid #D4E3F5;border-radius:18px;background:#F5F8FC}.camera{position:absolute;left:0;top:0;width:1200px;height:675px;transform-origin:0 0}.screenshot{position:absolute;display:block}.halo{position:absolute;border:5px solid #1565D8;background:#1565D812;border-radius:12px}.cursor{position:absolute;width:36px;height:44px}.capture-label{position:absolute;left:84px;top:866px;font-size:21px;color:#49657F}aside{position:absolute;left:1340px;top:177px;width:500px;height:675px;padding:28px 30px;background:#F5F8FC;border:1px solid #D4E3F5;border-radius:18px}.step-label{font-size:20px;font-weight:700;color:#1565D8;letter-spacing:2px}h2{font-size:29px;line-height:1.27;margin:18px 0 28px;font-weight:650}ul{list-style:none;display:flex;flex-direction:column;gap:18px}li{display:flex;gap:14px;font-size:26px;line-height:1.28;color:#49657F}li.current{color:#1565D8;font-weight:650}li.done{color:#102A43}.marker{flex:0 0 26px}.tip{position:absolute;left:30px;right:30px;bottom:26px;border-top:1px solid #D4E3F5;padding-top:20px;font-size:22px;line-height:1.3;color:#49657F}.caption{position:absolute;left:120px;right:120px;bottom:52px;text-align:center;font-size:36px;line-height:1.3;color:#102A43}.caption span{display:inline-block;padding:14px 26px;background:#F1F6FD;border:1px solid #D4E3F5;border-radius:16px;max-width:1640px;text-wrap:balance}#progress-track{position:absolute;left:0;top:0;width:1920px;height:4px;background:#EAF1FB}#progress{height:4px;width:1920px;background:#1565D8;transform-origin:left center}.demo{position:absolute;right:80px;bottom:14px;color:#49657F;font-size:16px}
</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="${total}" data-width="1920" data-height="1080">
<div id="background"></div>${frames.join('\n')}${voices.join('\n')}${captions.join('\n')}
<div id="progress-track"><div id="progress"></div></div>${data.narration.mode === 'demo-silent' ? '<div class="demo">DÉMO SILENCIEUSE · aucune connexion réelle</div>' : ''}</div>
<script>
const timeline = gsap.timeline({paused:true});
for (const shot of ${json(motion)}) {
  const pace = shot.pace;
  // Keep scene content visible at exact clip boundaries; fading from zero causes white flashes.
  timeline.fromTo('#'+shot.id+'-camera',{x:0,y:0,scale:1},{x:shot.pan.x,y:shot.pan.y,scale:shot.zoom,duration:1.1*pace,ease:'power2.inOut'},shot.start+pace);
  timeline.fromTo('#'+shot.id+'-halo',{opacity:0},{opacity:1,duration:.25*pace},shot.start+.7*pace);
  timeline.fromTo('#'+shot.id+'-cursor',{opacity:0,x:34,y:32},{opacity:1,x:0,y:0,duration:.65*pace,ease:'power2.out'},shot.start+.8*pace);
}
timeline.fromTo('#progress',{scaleX:0},{scaleX:1,duration:${total},ease:'none'},0);
window.__timelines = window.__timelines || {};
window.__timelines['main']=timeline;
</script></body></html>`;
writeFileSync(new URL('./index.html', import.meta.url), html);
writeFileSync(new URL('./timeline.json', import.meta.url), JSON.stringify({duration:total,steps:timeline.map(s=>({id:s.id,start:s.start,duration:s.duration,chapter:s.chapter}))}, null, 2)+'\n');
console.log(JSON.stringify({ok:true,steps:timeline.length,duration:total,narration:data.narration.mode}));
