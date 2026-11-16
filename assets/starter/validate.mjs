// Standalone build preflight; no network or third-party dependencies.
import {readFileSync, realpathSync, statSync} from 'node:fs';
import {resolve, relative, isAbsolute, extname} from 'node:path';
import {spawnSync} from 'node:child_process';

const fail = message => { throw new Error(`Invalid manifest: ${message}`); };
const object = (v, label) => { if (!v || typeof v !== 'object' || Array.isArray(v)) fail(`${label} must be an object`); return v; };
const text = (v, label, max = Infinity) => { if (typeof v !== 'string' || !v.trim() || [...v].length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\p{Surrogate}]/u.test(v)) fail(`${label} must be nonempty text (maximum ${max} characters)`); };
const number = (v, label, min = 0, max = Number.MAX_SAFE_INTEGER / 1000) => { if (typeof v !== 'number' || !Number.isFinite(v) || v < min || v > max) fail(`${label} must be finite and between ${min} and ${max}`); return v; };
const list = (v, label) => { if (!Array.isArray(v) || !v.length) fail(`${label} must be a nonempty array`); return v; };
const slug = (v, seen, label) => { if (typeof v !== 'string' || !/^[a-z][a-z0-9-]*$/.test(v) || seen.has(v)) fail(`${label} must be a unique lowercase slug`); seen.add(v); };
const choice = (v, allowed, label) => { if (!allowed.includes(v)) fail(`${label} must be one of ${allowed.join(', ')}`); };

export function asset(root, value) {
  // Backslashes, URL schemes, controls, traversal and symlink escapes must never
  // acquire different browser/filesystem interpretations. URL-encode at output.
  if (typeof value !== 'string' || !value || /[\\:\u0000-\u001f\u007f-\u009f\p{Surrogate}]/u.test(value) || isAbsolute(value) || value.split('/').some(p => !p || p === '..' || p === '.')) fail('asset paths must be relative project paths without traversal, controls, or URL schemes');
  let path;
  try { path = realpathSync(resolve(root, value)); if (!statSync(path).isFile()) fail(`not a regular asset: ${value}`); }
  catch (error) { fail(`missing asset ${value}: ${error.message}`); }
  const rel = relative(realpathSync(root), path);
  if (rel === '..' || rel.startsWith('../') || isAbsolute(rel)) fail(`asset escapes project: ${value}`);
  return path;
}
export const assetURL = value => './' + value.split('/').map(encodeURIComponent).join('/');

function probe(path) {
  const p = spawnSync('ffprobe', ['-v', 'error', '-show_format', '-show_streams', '-of', 'json', path], {encoding:'utf8', maxBuffer: 4 * 1024 * 1024});
  if (p.error || p.status !== 0) fail(`ffprobe required for voice/other image formats; ${p.error?.message || p.stderr.trim()}`);
  try { return JSON.parse(p.stdout); } catch { fail(`invalid ffprobe response for ${path}`); }
}
function imageDimensions(path) {
  const extension = extname(path).toLowerCase();
  if (!['.png', '.svg', '.jpg', '.jpeg', '.webp'].includes(extension)) fail('screenshots must be static PNG/SVG/JPEG/WebP images');
  if (extension === '.png') {
    const b = readFileSync(path);
    if (b.length < 24 || b.subarray(0,8).toString('hex') !== '89504e470d0a1a0a' || b.subarray(12,16).toString() !== 'IHDR') fail('invalid PNG header');
    return [b.readUInt32BE(16), b.readUInt32BE(20)];
  }
  if (extension === '.svg') {
    const source = readFileSync(path, 'utf8');
    const tag = source.match(/<svg\b[^>]*>/i)?.[0];
    if (!tag) fail('SVG root missing');
    const attr = name => tag.match(new RegExp(`\\s${name}\\s*=\\s*(["'])(.*?)\\1`))?.[2];
    const viewBox = attr('viewBox');
    if (viewBox) {
      const parts = viewBox.trim().split(/[\s,]+/).map(Number);
      if (parts.length !== 4 || !parts.every(Number.isFinite)) fail('invalid SVG viewBox');
      return parts.slice(2);
    }
    return [Number(attr('width')), Number(attr('height'))];
  }
  const stream = probe(path).streams?.find(s => s.codec_type === 'video');
  if (!stream || !['mjpeg', 'png', 'webp'].includes(stream.codec_name)) fail(`not a supported static image: ${path}`);
  return [stream.width, stream.height];
}

export function validate(data, root) {
  object(data, 'manifest');
  if (data.version !== 1) fail('version must be 1');
  text(data.title, 'title'); text(data.language, 'language');
  if (data.series !== undefined) text(data.series, 'series', 100);
  const canvas = object(data.canvas, 'canvas');
  if (canvas.width !== 1920 || canvas.height !== 1080 || canvas.fps !== 30) fail('canvas must be 1920×1080 at 30fps');
  const mode = object(data.narration, 'narration').mode;
  choice(mode, ['demo-silent', 'provided', 'elevenlabs', 'native'], 'narration.mode');
  const screens = new Map(), screenIDs = new Set();
  for (const screen of list(data.screenshots, 'screenshots')) {
    object(screen, 'screenshot'); slug(screen.id, screenIDs, 'screenshot.id');
    choice(screen.kind, ['synthetic', 'capture'], 'screenshot.kind');
    text(screen.source, 'screenshot.source'); text(screen.capturedAt, 'screenshot.capturedAt');
    if (! /^(?!0000)\d{4}-\d{2}-\d{2}$/.test(screen.capturedAt) || !Number.isFinite(Date.parse(screen.capturedAt)) || new Date(screen.capturedAt).toISOString().slice(0,10) !== screen.capturedAt) fail('capturedAt must be a real YYYY-MM-DD date');
    if (screen.redacted !== undefined && typeof screen.redacted !== 'boolean') fail('redacted must be a boolean');
    if (screen.kind === 'capture' && screen.redacted !== true) fail('capture requires redacted: true after privacy review');
    const path = asset(root, screen.path);
    if (extname(path).toLowerCase() === '.svg' && screen.kind !== 'synthetic') fail('SVG is reserved for synthetic examples');
    number(screen.width, 'screenshot.width', 1); number(screen.height, 'screenshot.height', 1);
    const [w,h] = imageDimensions(path);
    if (w !== screen.width || h !== screen.height) fail(`screenshot dimensions do not match file: ${screen.id}`);
    screens.set(screen.id, screen);
  }
  let cursor = 0;
  const ids = new Set();
  for (const step of list(data.steps, 'steps')) {
    object(step, 'step'); slug(step.id, ids, 'step.id');
    text(step.title, 'step.title', 65); text(step.instruction, 'step.instruction', 180); text(step.chapter, 'step.chapter');
    if (step.tip !== undefined) text(step.tip, 'step.tip', 180);
    number(step.duration, 'step.duration', 2); number(cursor + step.duration, 'total duration');
    const shot = screens.get(step.screenshot); if (!shot) fail(`unknown screenshot: ${step.screenshot}`);
    const t = object(step.target, 'step.target');
    number(t.x, 'target.x'); number(t.y, 'target.y'); number(t.width, 'target.width', 1); number(t.height, 'target.height', 1);
    if (t.x+t.width > shot.width || t.y+t.height > shot.height) fail('target exceeds screenshot bounds');
    number(step.zoom === undefined ? 1.5 : step.zoom, 'step.zoom', 1, 3);
    const checklist = list(step.checklist, 'step.checklist');
    if (checklist.length > 4) fail('maximum four checklist items');
    for (const item of checklist) { object(item, 'checklist item'); text(item.text, 'checklist.text', 74); choice(item.state, ['todo','current','done'], 'checklist.state'); }
    let previous = 0;
    for (const c of list(step.captions, 'step.captions')) {
      object(c, 'caption'); number(c.start, 'caption.start'); number(c.end, 'caption.end'); text(c.text, 'caption.text', 145);
      if (c.start < previous || c.start >= c.end || c.end > step.duration) fail('captions overlap, have zero length, or exceed scene');
      if (Math.round((cursor+c.start)*1000) >= Math.round((cursor+c.end)*1000)) fail('caption collapses at millisecond export precision');
      previous = c.end;
    }
    if (step.voice !== undefined) object(step.voice, 'step.voice');
    if (mode === 'demo-silent' && step.voice !== undefined) fail('demo-silent cannot contain voices');
    if (mode !== 'demo-silent') {
      const voice = object(step.voice, 'step.voice');
      const path = asset(root, voice.path);
      number(voice.duration, 'voice.duration', .01); number(voice.offset === undefined ? .5 : voice.offset, 'voice.offset'); number(voice.volume === undefined ? .88 : voice.volume, 'voice.volume', 0, 1);
      if ((voice.offset === undefined ? .5 : voice.offset) + voice.duration > step.duration - .25) fail('voice requires at least .25s trailing hold');
      const info = probe(path);
      if (!info.streams?.some(s => s.codec_type === 'audio')) fail('voice has no audio stream');
      const measured = Number(info.format?.duration);
      if (!Number.isFinite(measured) || Math.abs(measured - voice.duration) > .08) fail('voice duration does not match ffprobe (80ms tolerance)');
    }
    cursor += step.duration;
  }
  return data;
}
