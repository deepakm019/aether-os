# AstralSurge OS

AstralSurge OS is a client-side productivity workspace. The app is a static site: it has no build step or server-side component. It makes no third-party runtime requests; interface icons use Unicode glyphs, charts use Canvas, and typography uses system fonts.
The finance view groups expenses by budget category, tracks recurring items and paid status, records paid items in the transaction ledger, and estimates remaining monthly category budgets. Amounts can be hidden from view.
https://deepakm019.github.io/aether-os/

## Deploy to GitHub Pages

1. Push the repository to GitHub.
2. In the repository, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, select your branch and the **/(root)** folder, then save.
4. Under **Settings → Pages**, enable **Enforce HTTPS**. The app's vault encryption uses the Web Crypto API, which requires a secure context (HTTPS or localhost).
5. Wait for Pages to finish deploying, then open the HTTPS site.

**Origin security:** GitHub Pages sites served from the same `*.github.io` hostname share a browser origin, even when they use different repository paths. A less-trusted Pages project under the same account can access this app's origin-wide IndexedDB and localStorage, including the encrypted vault envelope, and could present a deceptive unlock screen. Use a dedicated custom domain/origin for sensitive data and do not host less-trusted Pages projects on that origin. The app displays a warning when it detects a `github.io` hostname, but a static client-side app cannot enforce origin isolation.

The root `index.html`, `manifest.json`, and `sw.js` files are required for the Pages entry point and PWA support. `.nojekyll` disables Jekyll processing. The service worker caches only the same-origin app shell (`/`, `index.html`, and `manifest.json`); it does not cache arbitrary or third-party requests. The first visit and later app updates require a connection to GitHub Pages. The Content Security Policy blocks third-party script, font, image, and connection loads, but permits inline script and style for the current single-file app; it is not a complete defense against same-origin script injection.

## Local encrypted data

Vault and checkpoint data are encrypted in the browser with PBKDF2-HMAC-SHA-256 (600,000 iterations) derived AES-256-GCM keys before they are written to IndexedDB. The versioned envelope records the KDF and iteration count. The earlier AES-GCM envelope (100,000 iterations) remains readable and is upgraded after unlock. If IndexedDB is unavailable, the app may use localStorage as a fallback, but it only accepts encrypted vault envelopes there. The backup-reminder timestamp is non-sensitive metadata. Use a long, unique passphrase (at least 16 characters; four or more unrelated words are recommended). The app cannot recover data if you lose your passphrase; export backups regularly.

Older OpenSSL-format AES-CBC vaults remain readable for migration using the browser's Web Crypto API. On a successful unlock, the vault is re-encrypted in the current AES-GCM format. Legacy AES-CBC is used only for this compatibility migration and is not used for new writes. AES-CBC does not authenticate legacy ciphertext, so migrate old vaults and keep an independent backup.

This protects stored data at rest from casual inspection but does not protect data while the vault is unlocked, against malicious browser extensions or code supplied by the hosting origin, or against device compromise. GitHub Pages still handles ordinary requests for the site itself.

## Local use

For service-worker testing, serve the repository over `http://localhost` rather than opening `index.html` as a `file://` URL. Web Crypto and service workers require HTTPS or localhost.

## Browser tests

The Playwright end-to-end suite covers every main screen, mobile navigation, core data-entry workflows, encrypted local storage, external-request absence, and the service-worker app-shell allowlist.

1. Configure a Python environment and install the development dependencies: `python -m pip install -r requirements-dev.txt`.
2. Install Chromium for Playwright: `python -m playwright install chromium`.
3. Run the tests: `python -m pytest`.

See [the Playwright test skill](./.github/skills/run-playwright-tests/SKILL.md) for focused test commands and agent execution guidance.

## License

This repository does not currently include a license file. Do not assume permission to reuse, modify, or redistribute the project code; contact the project owner for permission. The app has no third-party runtime libraries or remote assets.
