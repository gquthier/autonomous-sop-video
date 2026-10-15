---
name: sop-video
description: Produce narrated, step-by-step SOP videos from verified software workflows, with real screenshots, targeted button zooms, a side checklist, subtitles, and chapters. Use for customer tutorials, team onboarding, and repeatable operating procedures.
---

# SOP Video

Turn an observed workflow into a video a beginner can follow without guessing. Deliver editable source, the MP4, captions, chapter metadata, and a short evidence report. Default language is the user's language; use French when requested. The default look is white, blue, and restrained.

## Start from the actual request

Read the existing brief and assets before asking questions. Resolve only unknowns that change the result: the task, audience, software/version, narration mode, and output destination. Respect a request for one pilot before producing a series.

Write `BRIEF.md` in the output project with the result the learner should reach, prerequisites, scope, language, narration, authorized actions, and delivery formats. A request to make/export a video already authorizes its local render. Do not add a routine approval gate. Public uploads and real account changes require the corresponding authorization.

## Assign one accountable producer

When delegation is available, assign **one** producer agent using [agents/producer.md](agents/producer.md). Give it bounded file ownership, the brief, capture permissions, and acceptance criteria. The coordinating agent reviews the result and delivers it. Do not split scenes among many agents unless the user requests parallel production.

The producer may use a verified model through an available agent runtime or provider CLI. Follow [references/models.md](references/models.md) for selection, a short motion test, model identity, and usage evidence. Never invent a model identifier or silently rename an ambiguous request such as “O3.5”. If the requested runtime is unavailable, state the limitation and use the current agent for independent preparation; ask only if a required model choice blocks production.

Without a delegation tool, perform the same producer role in the current agent and say so. `agents/openai.yaml` describes discovery; it does not create a background agent or choose a model automatically.

## Produce the video

1. **Observe the procedure.** Read [references/capture-and-audio.md](references/capture-and-audio.md). Use the permitted browser/native capture tool, connected session, supplied recording, or verified public documentation. Record the exact screen, button text, native image dimensions, capture date, UI variant, and whether an action was actually executed. Never invent UI for a real product.
2. **Write the teaching script.** One action or decision per beat: where to go, what to click, what to check, what success looks like. Give the necessary prerequisite and the common blocking case. Avoid narrating a click that the video cannot show. Add an indicative screenshot for each actionable step and each changed modal/tab; reuse a screen with a new crop when that is clearer.
3. **Create or use the voice first.** Choose ElevenLabs, an authorized supplied/recorded voice, or the environment's available narration tool. Measure actual audio duration before arranging scenes. Keep voice/model/settings stable across a series. Preserve natural pauses and add enough hold time to inspect buttons. Never generate a voice silently when the user selected their own recording.
4. **Build the visual sequence.** Follow [references/production.md](references/production.md). Use the runnable starter below or adapt the approved project. White `#FFFFFF` background, blue `#1565D8` titles/accents, navy `#102A43` text. A large screenshot occupies the left; a short action checklist stays on the right. Move the camera to actual button coordinates, keep the relevant label visible, and use one cursor/halo. Add explanatory panels only when they improve understanding.
5. **Caption and chapter it.** Align captions with measured speech and split into readable cues. Do not let a cue survive its scene. Chapters must use the same timeline as the rendered video; deliver text/VTT chapters and embed them into the MP4. Player chapter UI varies, so retain the sidecar files.
6. **Verify and deliver.** Run the manifest validator and renderer checks, inspect every scene, watch the key click transitions, and verify the exported MP4 separately. Report real limitations and actual actions taken. A file existing is not proof of playback or correct framing.

## Runnable starter

The included demo uses **synthetic UI**, explicitly labeled on screen, and has **no narration**. It is a technical example, not evidence about a real application.

Requirements: Python 3.10+, Node.js compatible with the selected HyperFrames version, FFmpeg/ffprobe, and the renderer's supported Chrome. `npx` downloads the pinned renderer on first use; GSAP is fetched from its declared CDN during compilation. Local preview/render does not require an ElevenLabs account. Use the current renderer documentation if a dependency check fails.

From this skill's directory:

```bash
python3 scripts/sop.py init /path/to/new-sop
cd /path/to/new-sop
node build.mjs
npm run check
npm run preview -- --background
npm run render -- --quality delivery --output renders/video.mp4 --workers 1
```

For GPU encoding, add `--gpu` only when supported. The starter pins a tested renderer version for reproducibility; verify upgrades before changing it. If the HyperFrames skill is installed, use its current composition and verification guidance. This package includes the essential contract and works without a private skill directory.

Set `SKILL_DIR` to this skill's installed directory, then:

```bash
python3 "$SKILL_DIR/scripts/sop.py" validate sop.json --probe
python3 "$SKILL_DIR/scripts/sop.py" chapters sop.json --output delivery
python3 "$SKILL_DIR/scripts/sop.py" embed renders/video.mp4 delivery/chapters.ffmetadata delivery/video.mp4
```

`init` refuses a nonempty destination. `embed` refuses overwriting an output and copies streams without re-encoding. See [references/manifest.md](references/manifest.md) for fields and timing. The helper does not generate voices, log into websites, or upload files.

## Acceptance criteria

- The learner can locate every described button and see the resulting state, or a clearly stated unexecuted/example state.
- Screen data is anonymized in the actual exported pixels. Public source contains only approved assets; never bundle private raw captures, credentials, cookies, or session files.
- Small UI text remains readable at the intended viewing size; zooms preserve context. No checklist/caption overlap or unexplained idle periods.
- Audio has no clipped speech, abrupt cuts, missing phrases, or unstable voice changes. Use a consistent measured loudness and inspect peaks.
- Captions and chapters agree with the final duration. The final frame holds a useful result/checklist rather than accidental black.
- Delivery includes MP4, SRT, VTT, chapter text/VTT, editable source, screenshot provenance, model/voice usage evidence when available, and a QA report stating what was actually tested.

If capture, narration, rendering, or publishing is blocked, complete independent authorized work and state the exact missing capability. Do not describe a storyboard, synthetic screen, or silent preview as the finished narrated SOP.
