# Real captures and narration

## Capture evidence

Use the environment's approved computer/browser tools for the connected session. Prefer the user's chosen browser; a different capture route should be explained if it affects their workflow. Inspect a fresh screenshot after navigation: an accessibility tree can update while a browser compositor still shows an older frame. A stale or blank capture is not a real screenshot of the expected state. Reopen the task tab/window and verify pixels before proceeding.

For a supplied screen recording, preserve source timestamps and derive the relevant stills or clips from the recording. The bundled starter animates still captures; continuous video clips require the renderer’s media contract rather than pretending the helper records or edits them automatically.

For each used image record: source app/URL without tokens, capture date, language, relevant account/UI variant, native width/height, exact visible control text, and whether the action was observed, drafted, executed, or shown from an existing example. The manifest records the minimum; put fuller notes in `provenance.json`.

Capture read-only pages and drafts when sufficient. Do not grant access, send invitations, publish, delete, spend, or change a real account merely to complete a screen sequence. If the user authorizes the real action separately, record the resulting evidence accurately. Cancel demonstration drafts after capturing them.

Redact personal names, emails, IDs, avatars, tokens, client data, and unwanted branding in the asset pixels before composition. Use opaque masks/crops that survive zooming; translucent overlays can leak text. Keep buttons and their labels unobscured. Review every exported image and every animated crop. Place private raw captures outside the source directory and archive allowlist. The `redacted` flag is a recorded review, not an automatic privacy guarantee.

If current UI cannot be observed, use dated official material only with clear attribution and limitations, or provide a labeled storyboard. Synthetic UI is appropriate for the bundled technical demo, never as an unlabeled substitute for a real product walkthrough.

## Narration modes

**ElevenLabs:** use the available authorized connector or configured API. Discover current supported models from the provider/API; model availability and limits change. Pick a suitable French voice (or the requested language), generate a short sample if a voice is not already approved, then keep voice ID, model ID, language, stability/speed/style settings consistent. Record usage returned by the provider. Do not expose credentials or search unrelated credential stores. The skill does not include an ElevenLabs account or API credits.

**Provided/recorded voice:** use the user's supplied narration or an authorized recording tool. Transcribe and align it, preserving the speaker's intended wording. Trim only agreed mistakes/silence, or list proposed rerecords. Do not clone a speaker merely because an audio file was provided. `provided` means existing audio; the helper does not control a microphone.

**Native narration:** use a narration capability actually available in the environment. Verify language, duration, output format, model/voice identity when exposed, and usage. Do not promise native TTS if no such tool exists. If none of the chosen narration routes is available, finish the visual/script preparation and report the missing voice route; label any interim export as silent.

Measure each finished clip with ffprobe, then set `voice.duration`, `voice.offset`, and a scene duration that leaves readable time before/after speech. Prefer voice-first timing to speeding up speech to fit an arbitrary video duration. Start around a calm tutorial pace and adjust to content density and the user's approved sample.

Align captions against the actual audio with an available transcription/alignment tool; correct technical names using the approved script. Whole-sentence estimates are insufficient for final karaoke/word timing. The bundled demo captions are manually timed and explicitly silent.

Aim for clear speech, consistent loudness, and headroom rather than a universal preset. A useful stereo web starting point is around −16 LUFS integrated and true peak at or below −1 dBTP; verify the actual output and the destination's requirements. Background music is optional and should not obscure instructions. Do not claim you listened when you only measured or transcribed.

Primary provider documentation: https://elevenlabs.io/docs/overview/models . Verify it when choosing a model; do not label a hardcoded historical model “latest”.
