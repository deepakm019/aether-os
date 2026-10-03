# Agent guidance

## Project structure

- This is a static, client-side application with no build step or server-side component.
- `index.html` contains the application markup, styles, and JavaScript.
- `manifest.json`, `sw.js`, and `.nojekyll` support the root-deployed GitHub Pages PWA.

## Editing rules

- Keep changes focused and follow the existing vanilla JavaScript and inline CSS patterns unless the task calls for a broader change.
- Preserve GitHub Pages compatibility: use relative paths for local assets and do not introduce a required server-side route or build pipeline.
- Treat vault imports and all persisted data as untrusted. Escape user-controlled text before inserting it into HTML, and do not interpolate imported values into inline JavaScript or event-handler attributes. Prefer delegated event listeners and validate data indexes before use.
- Keep cryptographic operations on the Web Crypto API. Do not log passphrases, derived keys, decrypted vault contents, or other sensitive data.
- Update the service worker cache version when changing app-shell assets. Keep its same-origin app-shell allowlist strict; do not add external origins or arbitrary request caching.
- Keep runtime assets local. Do not add third-party network dependencies, fonts, or analytics.
- Vault and snapshot values must be encrypted before IndexedDB/localStorage writes. New encryption uses Web Crypto AES-GCM; any legacy CBC support is migration-only.
- Do not add dependencies without a clear need. If adding a remote dependency, assess its version pinning, integrity, and data-access implications.

## Validation

- Check modified files for editor diagnostics and JavaScript/JSON syntax errors using available tools.
- For UI changes, verify the affected view and interactions in a browser when possible.
- Browser end-to-end tests use pytest and Playwright. Configure Python, install `requirements-dev.txt`, install Chromium with `python -m playwright install chromium`, then run `python -m pytest`.
- Follow `.github/skills/run-playwright-tests/SKILL.md` when executing or extending the browser test suite.
- Test service-worker behavior on HTTPS or `http://localhost`; `file://` does not support service workers.
- Confirm changes preserve offline behavior and project/task actions when those areas are affected.

## Deployment

- GitHub Pages should deploy from the repository root with **Deploy from a branch**.
- Ensure **Enforce HTTPS** is enabled; Web Crypto and service workers require a secure context.
