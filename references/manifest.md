# `sop.json` and helper contract

The runnable example in `assets/starter/sop.json` is the canonical minimal project. Install, build, and check with the [quickstart](../README.md#quickstart). Modify data, run the Python validator with `--probe`, then regenerate `index.html` with `node build.mjs`. The Node build repeats lightweight preflight. Its SVG dimension-header reader is not a complete XML parser, so Python validation and browser/media review still run. Hand edits to generated HTML are overwritten by the next build; edit the generator for layout changes.

## Top level

- `version: 1`, `title`, `language`, optional `series` label.
- `canvas`: starter width, height, and fps. The validator rejects other values. Other layouts require adapting the generator and the validator together.
- `narration.mode`: `demo-silent`, `provided`, `elevenlabs`, or `native`. Non-demo modes require a measured voice clip on every step. Long continuous narration can be split into meaningful measured step clips before composition.
- `screenshots`: unique slug `id`, project-relative `path`, exact native `width`/`height`, `kind` (`capture`/`synthetic`), `source`, `capturedAt` (`YYYY-MM-DD`), and `redacted: true` after the capture-and-audio review for real captures. PNG dimensions are read directly; SVG is reserved for labeled synthetic demos; JPEG and WebP need `--probe`.
- `steps`: an ordered nonempty list. The cumulative durations form the only timeline. IDs are unique lowercase slugs.

## A narrated step

```json
{
  "id": "save",
  "title": "Enregistrer la configuration",
  "instruction": "Relisez les options, puis repérez Enregistrer.",
  "chapter": "Vérifier et enregistrer",
  "duration": 14.2,
  "screenshot": "settings-reviewed",
  "target": {"x": 1080, "y": 620, "width": 220, "height": 62},
  "zoom": 1.6,
  "checklist": [
    {"text": "Vérifier le compte sélectionné", "state": "done"},
    {"text": "Relire les options", "state": "current"},
    {"text": "Confirmer seulement les droits nécessaires", "state": "todo"}
  ],
  "voice": {"path": "assets/voice/save.mp3", "offset": 0.6, "duration": 11.8, "volume": 0.88},
  "captions": [
    {"start": 0.6, "end": 5.2, "text": "Vérifiez les options affichées."},
    {"start": 5.2, "end": 12.4, "text": "Le bouton Enregistrer permet de confirmer votre choix."}
  ],
  "tip": "Exemple : aucune modification réelle n’a été appliquée."
}
```

Text must be valid nonempty Unicode, without lone surrogates or controls except tab/CR/LF. Optional fields may be omitted, not explicitly null. Dates are real calendar dates in years 0001–9999. Asset paths reject empty/dot/traversal segments, backslashes, controls and URL schemes. Character limits, zoom range, checklist count, caption bounds, voice-duration tolerance, and trailing hold are the rejections from `scripts/sop.py` and `assets/starter/validate.mjs`.

All times are seconds relative to that step. Export timestamps use nonnegative nearest-millisecond half-up rounding; a caption must remain nonzero after rounding. Native target coordinates are measured in the original image, before fitting or zoom. The validator does not align speech automatically.

## Commands

Use a trusted project with a single writer for builds, exports, and asset edits. Build preflight rejects generated-output aliases to manifest, media, or dependency inputs, plus symlink or hardlinked outputs, before writing either generated file.

Exports create new sidecars only. Choose a fresh output directory for each revision. The POSIX writer rejects symlink files and directory ancestors (including aliases such as `/tmp` or `/var`); pass the canonical absolute directory path if necessary. A conflict is checked before ordinary writes. Disk errors or concurrent changes can leave an incomplete bundle; deliver only a complete bundle. Subtitle payloads are flattened to one physical line and escaped as literal text; check the intended player, especially SRT entity display.

From the skill root, `python3 scripts/sop.py init <new-directory>` copies the standalone starter and refuses nonempty directories. `validate <project>/sop.json --probe` checks project data and media. All asset references must remain inside the project, including resolved symlinks.

`chapters <project>/sop.json --output <delivery-directory>` validates the same timeline and writes:

- `captions.srt`, `captions.vtt`: global timed subtitles.
- `chapters.txt`: human/player description timestamps.
- `chapters.vtt`: chapter intervals, separate from subtitle cues.
- `chapters.ffmetadata`: millisecond precision chapter definitions for FFmpeg.
- `validation.json`: computed timeline, caption cues, and validation status.

`embed <input.mp4> <chapters.ffmetadata> <new-output.mp4>` uses FFmpeg stream copy onto a new destination. The metadata must be generated from the final manifest. After muxing verify `ffprobe -v error -show_chapters -show_format -of json <new-output.mp4>`. Keep the chapter sidecars for players that ignore embedded chapters.
