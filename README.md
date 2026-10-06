<div align="center">

# AstralSurge OS

### Your personal command center for focus, projects, fitness, and finances.

Plan your days, move work forward, track your habits, and understand your money — in one private, local-first workspace.

<a href="https://deepakm019.github.io/aether-os/"><strong>🚀 Get Started</strong></a>

<br>

**No account required · Encrypted local vault · Works offline after first load**

</div>

---

## What you can do

| 🧭 Plan | 🎯 Execute | 💰 Understand |
| --- | --- | --- |
| Organize work with guided pathways, an Eisenhower matrix, and a calendar. | Track projects on a Kanban board, focus with custom session tags, and log workouts with your own categories. | Manage budgets and transactions. |

Navigation is arranged into collapsible dimensions so you can open only the areas you need. **Goal Roadmaps** includes four editable starting points for launching a portfolio project, learning a skill, building a fitness routine, and growing an emergency fund. Your calendar brings together task due dates, workout sessions, finance transactions, and scheduled budget items. **Plan your day** is focused on four inputs: available hours, fixed meetings and travel, lunch and tea breaks, and energy mode plus one main task. It generates a conflict-checked day agenda, picks supporting tasks from unfinished Task Board work using mode, energy, and priority, and shows open time alongside scheduled blocks. Deep mode reserves longer focus time, balanced mode mixes focus and lighter work, and low-energy mode limits workload and uses shorter sessions. Regenerating a day asks before replacing its existing schedule. **Habits & Reminders** keeps recurring habits, one-time alarms, and simple time tools separate from day planning. **Money Overview**, **Budget & Bills**, and **Transactions** separate the monthly financial summary, spending limits and recurring expenses, and the full ledger into focused screens. Financial and planner data are stored in the encrypted vault.

Alarms and schedule reminders are checked while the app is open; browser notifications require permission and a supported browser. They are not guaranteed to fire after the app or browser is closed. The displayed clock uses your device's clock and time-zone settings. In the budget, add a monthly projection as a provisional decision, then mark it done and enter the actual amount to compare the locked cost with the projection. Monthly totals roll over automatically while earlier decisions remain available in the archive. Notes live in your encrypted workspace alongside the rest of your data.

## Get started

1. Open [AstralSurge OS](https://deepakm019.github.io/aether-os/).
2. Choose **Login as New** to create a vault, or **Unlock Workspace** to open an existing one.
3. Set a unique passphrase of at least 16 characters. Keep it safe: the app cannot recover it.
4. Add a task, note, workout, or budget item and explore the sidebar.
5. Export encrypted backups regularly from **Checkpoints**.

> **Already have a vault?** Use the same browser and site origin where you created it, or import your encrypted backup bundle.

## Notes before you begin

- **Your data stays in this browser.** This is a static, client-side app with no account or cloud sync. Vault and checkpoint records are encrypted with AES-256-GCM before being saved in browser storage.
- **Keep your passphrase and backups safe.** Losing your passphrase or clearing browser storage can make your local vault unavailable. Store exported backups somewhere secure and separate from this device.
- **Use a trusted origin.** GitHub Pages sites hosted under the same `github.io` hostname share browser storage across project paths. For sensitive data, use a dedicated origin and do not enter your passphrase on an untrusted page.
- **Use HTTPS.** Web Crypto and service-worker features require a secure context. The hosted app uses HTTPS; for local testing, serve it from `http://localhost` rather than opening the file directly.
- **Refresh the offline app shell.** Use **Privacy & Security → Clear offline cache & refresh** to remove the app-shell cache and reload. This does not delete your encrypted vault or checkpoints, but downloading the app again requires a network connection.
- **No runtime third-party services.** The app has no required backend or third-party runtime requests. It uses browser APIs, system fonts, Unicode symbols, and Canvas.

## Run locally

The app has no build step or server-side component. From the repository root, start any static HTTP server and open the page at `http://localhost`. For example, with Python:

```powershell
python -m http.server 8000
```

Then visit [http://localhost:8000](http://localhost:8000).

## Deploy to GitHub Pages

1. Push the repository to GitHub.
2. Open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, select your branch and the **/(root)** folder, then save.
4. Enable **Enforce HTTPS**.

The root `index.html`, `manifest.json`, and `sw.js` files are required for the Pages entry point and PWA support. `.nojekyll` disables Jekyll processing. The service worker caches only the same-origin app shell and does not cache arbitrary or third-party requests.

## Run browser tests

The Playwright end-to-end suite covers the main screens, navigation, data-entry workflows, encrypted local storage, external-request absence, and service-worker app-shell behavior.

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest
```

See the [Playwright test skill](./.github/skills/run-playwright-tests/SKILL.md) for focused test commands.

## License

This repository does not currently include a license file. Do not assume permission to reuse, modify, or redistribute the project code; contact the project owner for permission.
