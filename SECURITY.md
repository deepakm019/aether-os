# Security policy

AstralSurge OS stores all data in the browser. The app code makes no network requests for user data.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's private vulnerability reporting
(Security tab → Report a vulnerability) on this repository. Include steps to reproduce, the affected
version (shown in `sw.js` as `CACHE_NAME`), and the impact you observed.

## Scope

- Encrypted vault and backup handling (Web Crypto AES-GCM, PBKDF2 key derivation).
- Import validation for backup and recovery files.
- Cross-site scripting through stored or imported data.
- Service-worker caching behaviour.

Hosting-provider logs (GitHub Pages) are outside this project's control.
