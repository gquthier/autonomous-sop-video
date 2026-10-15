# Model selection and provenance

A model name is an execution choice, not a guarantee of good motion design. The user's explicit preference has priority when that model exists and is available through an authorized runtime.

1. Inspect the installed agent/provider runtime's supported model list or official model documentation. Record the date and source. If an identifier is ambiguous (for example “O3.5”), ask one precise clarification while continuing independent capture/script work; never infer a nonexistent release or silently map it to a different family.
2. Choose the requested model, or a verified current capable model when the user asked for the newest. Opus-family coding models may be used through a supported runtime when available, but this package does not require a specific vendor, account, or version.
3. Give it a representative 10–20 second scene: real screenshot, native target rectangle, caption timing, white/blue layout, and the renderer contract. Judge visible correctness, seekable motion, legibility, and valid output before committing the whole video. Reuse an already-validated equivalent pilot when nothing relevant changed.
4. Record the actual response/runtime `model` or canonical model ID, provider/runtime version, requested model, and reported input/output/cache usage or cost. A friendly agent name or requested CLI flag alone is not proof of the model that ran. If the provider exposes no identity or usage, record `unknown` rather than guessing.
5. When a requested model is unavailable, report the limitation and the concrete fallback. Keep using a validated model for a series unless the user requests a change or a new short test demonstrates a useful improvement.

Suggested private project evidence (`model-usage.json`):

```json
{
  "requestedModel": "provider-specific ID or user wording",
  "actualModel": null,
  "provider": "runtime name",
  "verifiedAt": "YYYY-MM-DD",
  "identityEvidence": "provider response field, or unknown",
  "usage": null,
  "cost": null,
  "costMeaning": "unknown; estimates are not proof of a charge",
  "motionTest": {"result": "pending", "evidence": []}
}
```

Keep tokens, credentials, raw private prompts, and hidden reasoning out of the public package. A usage report may include counts and provider-reported estimates, not secret-bearing runtime logs. Do not claim universal superiority, zero cost, or subscription billing from a CLI estimate.
