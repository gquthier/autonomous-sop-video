# Real captures and narration

## Capture evidence

Use the environment's approved computer/browser tools for the connected session. Prefer the user's chosen browser; a different capture route should be explained if it affects their workflow. Inspect a fresh screenshot after navigation: an accessibility tree can update while a browser compositor still shows an older frame. Reopen the task tab/window and verify pixels before proceeding.

For a supplied screen recording, preserve source timestamps and derive the relevant stills or clips from the recording. The bundled starter animates still captures. Continuous video clips use the renderer’s media contract.

For each used image record: source app/URL without tokens, capture date, language, relevant account/UI variant, native width/height, exact visible control text, and whether the action was observed, drafted, executed, or shown from an existing example. The manifest records the minimum; put fuller notes in `provenance.json`.

Capture read-only pages and drafts when sufficient. Account mutations follow the permission boundaries in [SKILL.md](../SKILL.md). When a real action was authorized, record the resulting evidence. Cancel only demonstration drafts created by this run, when cancellation is safe and authorized. Leave a pre-existing or shared/autosaved draft unchanged when ownership or cancellation effects are unclear, and report it.

Redact personal names, emails, IDs, avatars, tokens, client data, and unwanted branding in the asset pixels before composition. Use opaque masks/crops that survive zooming; translucent overlays can leak text. Keep buttons and their labels unobscured. Review every exported image, every animated crop, and the inspected final frames. Place private raw captures outside the source directory and archive allowlist. The `redacted` flag records that this review happened.

If current UI cannot be observed, use dated official material only with clear attribution and limitations, or provide a labeled storyboard. Synthetic UI is for the bundled technical demo. A real walkthrough uses observed captures or a labeled storyboard.

## Narration modes

Before sending private scripts, audio, or screens to any provider, confirm that destination/use is authorized. Use only narration and camera media authorized for this tutorial's audience and destination. Webcam reuse is a separate opt-in. Voice cloning requires explicit speaker consent for that use and an approved sample. Get approval before switching to a fallback voice.

**ElevenLabs:** use the available authorized connector or configured API. Discover current supported models from the provider/API; model availability and limits change. Pick a voice in the requested language, generate a short sample if a voice is not already approved, then keep voice ID, model ID, language, stability/speed/style settings consistent. Record usage returned by the provider. Credentials stay in the local environment and out of the repository. The skill does not include an ElevenLabs account or API credits.

**Provided/recorded voice:** use the user's supplied narration or an authorized recording tool. Transcribe and align it, preserving the speaker's intended wording. Trim only agreed mistakes/silence, or list proposed rerecords. `provided` means existing audio; the helper does not control a microphone.

**Native narration:** use a narration capability actually available in the environment. Speech comes from that tool's own generate entry point; record the route and the output hash. A local reimplementation of the model is not that tool. Verify language, duration, output format, model/voice identity when exposed, and usage. If none of the chosen narration routes is available, finish the visual/script preparation and report the missing voice route; label any interim export as silent.

Measure each finished clip with ffprobe, then set `voice.duration`, `voice.offset`, and a scene duration from that measurement, with readable time before and after speech. Start around a calm tutorial pace and adjust to content density and the user's approved sample.

Align captions to word timing against the actual audio with an available transcription/alignment tool; correct technical names using the approved script. The bundled demo captions are manually timed and explicitly silent.

Aim for clear speech, consistent loudness, and headroom. A useful stereo web starting point is around −16 LUFS integrated and true peak at or below −1 dBTP; verify the actual output and the destination's requirements. Background music is optional and stays under the instruction. Listening coverage is the picture-and-sound release gate.

Primary provider documentation: https://elevenlabs.io/docs/overview/models . Verify the current model page when choosing a model.
