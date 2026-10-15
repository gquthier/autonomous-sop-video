# `sop.json` and helper contract

The runnable example in `assets/starter/sop.json` is the canonical minimal project. Modify data, run the validator, then regenerate `index.html` with `node build.mjs`. Hand edits to generated HTML are overwritten by the next build; edit the generator for layout changes.

## Top level

- `version: 1`, `title`, `language`, optional `series` label.
- `canvas: {width: 1920, height: 1080, fps: 30}`. Other layouts require adapting the generator/validator.
- `narration.mode`: `demo-silent`, `provided`, `elevenlabs`, or `native`. Non-demo modes require a measured voice clip on every step. Long continuous narration can be split into meaningful measured step clips before composition.
- `screenshots`: unique slug `id`, project-relative `path`, exact native `width`/`height`, `kind` (`capture`/`synthetic`), `source`, `capturedAt` (`YYYY-MM-DD`), and `redacted: true` for reviewed real captures. PNG dimensions are read directly; SVG is reserved for labeled synthetic demos; other supported image formats need `--probe`.
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

All times are seconds relative to that step. Native target coordinates are measured in the original image, before fitting or zoom. At most four checklist items; use short text (the validator imposes conservative layout bounds). Captions must be non-overlapping and fit entirely within the step. Voice duration must match ffprobe within 80ms when `--probe` is used, with at least 250ms of final hold. The validator does not align speech automatically.

## Commands

From the skill root, `python3 scripts/sop.py init <new-directory>` copies the standalone starter and refuses nonempty directories. `validate <project>/sop.json --probe` checks project data and media. All asset references must remain inside the project, including resolved symlinks.

`chapters <project>/sop.json --output <delivery-directory>` validates the same timeline and writes:

- `captions.srt`, `captions.vtt`: global timed subtitles.
- `chapters.txt`: human/player description timestamps.
- `chapters.vtt`: chapter intervals, separate from subtitle cues.
- `chapters.ffmetadata`: millisecond precision chapter definitions for FFmpeg.
- `validation.json`: computed timeline, caption cues, and validation status.

`embed <input.mp4> <chapters.ffmetadata> <new-output.mp4>` uses FFmpeg stream copy and refuses an existing destination. The metadata must be generated from the final manifest. After muxing verify `ffprobe -v error -show_chapters -show_format -of json <new-output.mp4>`; chapter sidecars are still necessary for players that ignore embedded chapters.

These helpers intentionally do not authenticate, create narration, take screenshots, render with a browser, or publish. The agent coordinates those available capabilities and records their evidence.
