# Local animation dependency

GSAP is pinned to **3.12.7** in package.json and package-lock.json. This version is already present in the local npm cache used to test this starter. It replaces the former runtime CDN request for 3.14.2. It is **not MIT-licensed**: © 2025 GreenSock, author Jack Doyle. The package carries the [GreenSock Standard license notice](https://gsap.com/standard-license); review those terms for your distribution/use case. Its original copyright/license banner is retained, unmodified, in the installed artifact. No third-party code is vendored in this starter.

Install and build with the [quickstart](../../README.md#quickstart). npm verifies the locked archive's SHA-512 integrity. HyperFrames preview, check, and render scripts are separately pinned and may use the network through npx; they are outside this offline build and test set.

The build resolves GSAP **inside this project**, checks version 3.12.7 and the SHA-256 of dist/gsap.min.js, and emits a project-relative script reference into HTML. Keep node_modules/gsap with the project when previewing or rendering, or run the locked install at its new location. Open index.html with that dependency and its media. The integrity checks detect corruption or accidental replacement of the pinned file. An edit to this generator or lockfile is outside those checks.

The build validates the manifest fields it consumes before writing index.html and timeline.json. Narration and non-PNG/SVG image formats also require local **ffprobe**. PNG dimensions are checked from the header; synthetic SVG dimensions from the root attributes. Assets are trusted, reviewed local files. Active SVG from an untrusted source stays out of the project. Build output is deterministic. HyperFrames checks and the release gates still run.
