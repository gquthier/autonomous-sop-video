# Production and verification

## Teaching structure

Start with the visible result and prerequisites. For each step show the route, control, action, expected state, and a concise check. Distinguish the main procedure from optional permissions or product variants. End with two or three success checks and the most likely recovery path. Avoid fixed video lengths: duration follows clear instruction and the actual voice.

Use an agreed pilot before scaling a series. An existing approved video is the style reference; extract representative frames and transition timing. If asked to analyze every frame, decode all frames and record which were inspected at full size versus on contact sheets. Do not call a handful of samples a frame-by-frame review.

## Visual grammar

Default canvas 1920×1080, 30 fps. Pure white background; blue titles/accents; navy body text. A 1200×675 capture viewport occupies the left; a 500px wide checklist sits on the right. Captions use the lower safe region. The starter's geometry is intentionally conservative; edit the generator if a different aspect ratio or layout is requested.

Use the real screenshot as a persistent subject. The target rectangle is in its native pixels. Convert it using the same fit scale/offset as the image, then animate the camera wrapper, halo, and cursor together. Keep the whole control label visible. An oversized target may require less zoom, a crop, or a separate close-up. Never use coordinates from a resized thumbnail without transforming them.

A hover halo is not evidence of a completed click. Show a click animation only when the captured before/after state supports it. If a consequential action was not executed, say so beside the button and avoid a fabricated success screen. An already-existing configuration must be labeled as an example, not the result of the preceding draft.

Show the new modal/tab when the process changes location. Prefer a real close-up of a setting to a decorative icon. Avoid adding stock imagery merely to increase the image count. Keep the full section name visible before zooming into the exact control.

## Minimal HyperFrames contract

`index.html` has a standalone `div[data-composition-id="main"]` in `body`, declared width/height/duration, and a root sized with CSS `width:100%;height:100%`. Every timed clip has a unique `id`, `.clip`, `data-start`, `data-duration`, and `data-track-index`. One paused GSAP timeline is registered at `window.__timelines['main']` after construction. Do not manually start playback or use clocks/random state.

The renderer owns clip visibility and media playback. Animate children/camera wrappers, not timed clip `display`/`visibility`. An audio element needs its own unique ID, `src`, and timing; do not add `crossorigin`. Keep audio outside plain timed scene wrappers. Use actual audio duration. Root duration must include all clips and final holds. Avoid CSS/GSAP transforms competing on the same property.

The starter uses system fonts and a pinned GSAP CDN script. For exact typography across machines, ship licensed font files and declare local `@font-face`. To work offline, vendor GSAP under its applicable license and update the script URL; verify the renderer cache/dependencies beforehand.

## QA sequence

1. Run `sop.py validate sop.json --probe`. It checks files, dimensions, coordinates, unique IDs, durations, caption bounds, and voice lengths. It cannot prove that a target is the correct button, the instructions are true, or the privacy masks are complete.
2. Run `node build.mjs` and `npm run check -- --json`. A skipped browser audit is not a pass. Inspect lint/runtime/layout/contrast results, including warnings that matter to this composition.
3. Capture every scene midpoint and the start/hold/end of important zooms. Inspect the full frames. Verify each target stays inside the capture viewport and no caption overlaps the side checklist. Test the narrated beginning/end of each step.
4. Open the preview, then render within the existing authorization. On supported hardware `--workers 1 --gpu` uses less temporary disk than a multiworker PNG render. Check free disk and renderer output rather than estimating success from process duration.
5. Inspect the actual MP4 with ffprobe. Decode samples from every scene and key transitions, and listen to beginning/middle/end plus each corrected voice edit. A source preview alone is insufficient. Measure loudness/true peak, correct audible problems, and recheck only affected parts plus final mux integrity.
6. Export captions/chapters, embed chapters, then verify them with `ffprobe -show_chapters -of json delivery/video.mp4`. Inspect the chapter boundaries against the picture. Players vary in whether they expose chapter navigation.

The QA report records dimensions, fps, duration, audio/voice identity, probe results, chapter count, sampled timestamps, actual playback/listening performed, and unresolved limitations. Keep private logs and raw captures outside the public source package. Verify the source archive contents before publishing.
