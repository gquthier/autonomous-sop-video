# Production and verification

## Teaching structure

Start with the visible result and prerequisites. For each step show the route, control, action, expected state, and a concise check. Distinguish the main procedure from optional permissions or product variants. End with two or three success checks and the most likely recovery path. Duration follows clear instruction and the actual voice. Pilot count is the Scope step in [SKILL.md](../SKILL.md).

An existing approved video is the style reference; extract representative frames and transition timing. If asked to analyze every frame, decode all frames and record which were inspected at full size versus on contact sheets.

## Visual grammar

Use the starter canvas and layout enforced by `scripts/sop.py`, `assets/starter/validate.mjs`, and `assets/starter/build.mjs`: white background, blue titles and accents, navy body text, the capture viewport on the left, the checklist on the right, captions in the lower safe region. Edit the generator and the validator together when a different aspect ratio or layout is requested.

Use the real screenshot as a persistent subject. The target rectangle is in its native pixels. Convert it using the same fit scale/offset as the image, then animate the camera wrapper, halo, and cursor together. Keep the whole control label visible. An oversized target may require less zoom, a crop, or a separate close-up.

Show a click animation only when the captured before/after state supports it. If a consequential action was not executed, say so beside the button. Label an already-existing configuration as an example.

Show the new modal/tab when the process changes location. Prefer a real close-up of a setting to a decorative icon. Keep the full section name visible before zooming into the exact control.

## Minimal HyperFrames contract

`index.html` has a standalone `div[data-composition-id="main"]` in `body`, declared width/height/duration, and a root sized with CSS `width:100%;height:100%`. Every timed clip has a unique `id`, `.clip`, `data-start`, `data-duration`, and `data-track-index`. Register one paused GSAP timeline at `window.__timelines['main']` after construction, and leave playback, clocks, and random state to the renderer.

The renderer owns clip visibility and media playback. Animate children and camera wrappers. Leave timed-clip `display` and `visibility` to the renderer. An audio element needs its own unique ID, `src`, and timing, and no `crossorigin` attribute. Keep audio outside plain timed scene wrappers. Use actual audio duration. Root duration must include all clips and final holds. One owner per animated property: CSS or GSAP, not both.

The starter uses system fonts and a local, lockfile-pinned GSAP dependency. Install and build with the [quickstart](../README.md#quickstart). Read `assets/starter/THIRD_PARTY.md` before redistribution or use. For exact typography across machines, ship licensed local fonts. Offline rendering requires the pinned HyperFrames CLI, a supported browser, and the renderer dependencies, in addition to the offline build.

## QA sequence

1. Run `sop.py validate sop.json --probe`. It checks files, dimensions, coordinates, unique IDs, durations, caption bounds, and voice lengths. It cannot prove that a target is the correct button, the instructions are true, or the privacy masks are complete.
2. Run `node build.mjs` and `npm run check -- --json`. Inspect lint/runtime/layout/contrast results, including warnings that matter to this composition.
3. Capture every scene midpoint and the start/hold/end of important zooms. Inspect the full frames. Verify each target stays inside the capture viewport and no caption overlaps the side checklist. Test the narrated beginning/end of each step.
4. Open the preview, then render within the existing authorization. Check free disk and renderer output.
5. Inspect the actual MP4 with ffprobe. Decode samples from every scene and key transitions, and listen through the entire final narration including every edit boundary. Check pronunciation, intelligibility, omissions, clipping, and subtitle timing. Partial listening is interim QA: record its coverage and leave the audio gate unverified. Measure loudness and true peak, correct audible problems, and recheck the corrected final mux.
6. Export captions and chapters, embed them with the manifest `embed` command, and verify chapters the way that command specifies. Inspect the chapter boundaries against the picture.

The QA report records dimensions, fps, duration, audio/voice identity, probe results, chapter count, sampled timestamps, actual playback/listening performed, and unresolved limitations.

## Release gates (fail closed)

Before marking a real SOP complete, record the following in the project's QA report. Missing evidence leaves the output **draft/unverified** and names the missing gate. Each delivery records its own gates.

| Gate | Required evidence |
| --- | --- |
| Scope and permissions | Authorized pilot count from the Scope step, audience/destination, account actions actually performed, and the narration-mode authorization. |
| Truth | The Evidence-step record for every step: source/date, action status, exact visible label, and expected result. |
| Privacy | The capture-and-audio redaction review: reviewer, inspected assets/timestamps, and raw/private source kept outside the package. |
| Structure and render | Exact validation/build/check/render commands, exit codes, renderer/browser versions, warnings and skipped checks. Final MP4 probe. |
| Picture and sound | Per-scene frame timestamps, zoom start/hold/end and transition coverage, control readability, caption timing, and the listening coverage from QA step 5. |
| Delivery | Final artifact identifiers/hashes, chapters/subtitles checked against the final mux, the package allowlist below, outstanding limitations, and approved publication scope. |

Package from an explicit allowlist, not the entire working directory. Include only the intended manifest, reviewed media, generator, runtime dependencies/license notices, and requested sidecars/QA notes. Leave `.git`, `.env`, credentials, browser profiles, `node_modules`, private logs, raw captures, backups, and intermediate renders out unless specifically cleared. Inspect the archive's actual member list and spot-check its contents before sharing.

A useful QA entry is `gate: pass/fail/unverified; evidence: command/artifact/timestamps; limitation: ...`. Keep authorization and personal-data records local; the public QA copy discloses non-sensitive verification facts.
