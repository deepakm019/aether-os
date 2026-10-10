# AstralSurge OS

A personal operating system for planning, focus, money, habits and notes. It is a single HTML file that runs entirely in your browser. Nothing is sent to a server. Your data lives in this browser's IndexedDB, and you can export it as a backup file.

## Running it

Open the app over HTTP, not by double-clicking the file. IndexedDB does not work reliably from `file://` URLs.

```bash
python3 -m http.server 8765
# then open http://127.0.0.1:8765/AstralSurge_OS_v3.html
```

## Feature list

### Daily use
- **Today** with a quick capture box. Type an idea and press Enter. It lands in your Inbox.
- **Energy check-in** (morning wizard, editable from Today).
- **Recommendations** for the next best action, with the evidence shown.
- **Work** board with Inbox, To Do, In Progress and Completed tabs. Task inspector with subtasks, XP and images.
- **Recurring tasks**: set a task to repeat every day, every weekday, or every week. Completing it creates the next instance, dated correctly (weekends are skipped for "every weekday").
- **Tags** on tasks, shown on cards and in the inspector, and searchable.
- **Focus** timer with categories, duration presets, pause and resume, and automatic time logging on tasks.
- **Plan** planner blocks and scheduling into open 45-minute windows.
- **Calendar**, **Reminders** (with snooze), **Habits**, **Goals** with milestones, **Workouts**, **Notes**, **Memory**, **Timer** and **Stopwatch**.
- **Money**: budgets, expenses (quick capture), recurring bills, and decisions that reconcile planned against actual spend.
- **Progress**: XP, levels, badges, weekly reviews.

### Safety and recovery
- **Trash**: deleting a task or note moves it to Trash. Items stay for 30 days, then are removed automatically on load. You can restore or delete forever from Vault → Recovery.
- **Daily snapshots**: one automatic snapshot per day, keeping the newest 5. Restore any of them from Vault → Recovery.
- **Undo restore**: before any restore (backup file, checkpoint, snapshot or encrypted storage), the current data is saved. Undo it for 24 hours from Vault → Recovery.
- **Restore preview**: before replacing anything, you see per list how many items the backup adds and how many would be removed.
- **Backup nudges**: Vault shows the last backup date and how many changes have happened since. Today surfaces a backup recommendation after 7 days or if you have never backed up. It appears when no higher-priority item is competing for attention.
- **Readable backups** (JSON, versioned, with a schema number) and **recovery exports** that leave out images to keep the file small.
- **Checkpoints**: a manual save point you can compare against and restore.
- **Encrypted vault**: AES-GCM, with a key derived from your passphrase via PBKDF2. A recovery key can unlock the same vault. Encrypted backups stay encrypted.
- **Read-only protection**: if saved data cannot be read, the app stops writing so the unreadable record is never overwritten.
- **Import validation**: malformed files, files from a newer app version, and files with wrong list types are rejected with a clear message, and existing data is left alone.
- **Older backups import cleanly**: bare state files from earlier versions are upgraded. Running timers in imported backups are restored paused, never running.

### Look and feel
- Dark, light and automatic themes; accent colours; wallpapers; ambient effects.
- Nine font styles: system, friendly, rounded, geometric, editorial serif, classic serif, condensed, monospace and high readability.
- Hide amounts toggle for privacy in public.
- Works on phones (tested at 320, 390 and 768 px widths) and desktop.

## Where your data lives

| IndexedDB key | Contents |
|---|---|
| `workspace` | Your current data (compressed; encrypted when the vault is on) |
| `checkpoint` | Your manual checkpoint |
| `auto_checkpoints` | Up to 5 daily snapshots |
| `undo_snapshot` | The state before the last restore, kept for 24 hours |
| assets | Attached images, stored separately |

localStorage is used only as a fallback. If IndexedDB is unavailable, a copy of the workspace (up to 8 MB) is kept there. It also stores the beta acknowledgement and two ambient-effect preferences.

## Limits to know about

- **Single browser.** Data is per browser profile and per origin. Clearing site data erases it. Export a backup regularly.
- **Multiple open tabs** are not coordinated. Two tabs writing at once can overwrite each other.
- **Snapshots need the app to be opened.** A snapshot is taken on first load each day. For encrypted vaults, it is taken only after you unlock.
- **Undo is one step.** It reverts the most recent restore, not an arbitrary history.
- **Trash covers tasks and notes.** Other items (habits, budgets, goals) are deleted immediately, as before.
- **Recurring tasks** create their next instance when you complete the task. Missed occurrences are not back-filled.
- **"Changes since backup"** counts saves, so creating a new workspace counts as one change.
- **Browser storage can be evicted** by the browser under pressure. The app requests persistent storage, but the browser decides. Regular backups remain the real protection.

## Tests

All suites drive the real app in headless Chromium through Playwright. Run them against the server above.

| Suite | Checks | What it covers |
|---|---|---|
| `astralsurge_core_playwright_tests.py` | 32 | Boot, check-in, timer and stopwatch, money baseline, subtasks, reminders, overflow on every route |
| `astralsurge_ui_regression_tests.py` | 45 | Layout at four widths, font and timezone settings, focus spacing, tag separation, inspector |
| `persistence_tests.py` | 45 | Backup round trip into an empty browser, legacy migration, older imports, bad files, recovery exports, encryption, checkpoints, read-only protection, fonts, tags, focus |
| `sweep_tests.py` | 19 | Habits, notes, goals, workouts, expenses, decisions, search, calendar, reviews, reminders, completion, settings, encrypted restore |
| `features_v3_tests.py` | 31 | Quick capture, recurrence rules and editor, trash (restore, delete forever, 30-day expiry), daily snapshots, undo and its 24-hour expiry, restore preview, backup nudges |
| `e2e_journey_tests.py` | 21 | One continuous user story on a phone-sized viewport: capture, recurring task, trash, backup, restore, undo, reload, encryption, lock, unlock, snapshot restore in the vault |

Total: **193 checks**.

```bash
python3 astralsurge_core_playwright_tests.py
python3 astralsurge_ui_regression_tests.py
python3 persistence_tests.py
python3 sweep_tests.py
python3 features_v3_tests.py
python3 e2e_journey_tests.py
```

The suites expect the app at `http://127.0.0.1:8765/AstralSurge_OS_v3.html`, served from the folder that contains this README (the persistence, sweep, features and journey suites). The core and UI suites read the app from the same folder as the script.

## Release notes (this version)

- Added trash for tasks and notes with 30-day retention.
- Added daily automatic snapshots (newest 5), with restore from Vault.
- Added undo for restores, available for 24 hours.
- Added a restore preview that shows what each restore would add and remove.
- Added quick capture on Today.
- Added recurring tasks (daily, weekdays, weekly).
- Added backup nudges and a changes-since-backup counter.
- Fixed: the encrypted storage restore button never worked; restoring a plain backup into an encrypted vault could drop encryption; unreadable saved data could be overwritten at startup; the checkpoint restore path was not covered by tests.
- Accessibility: labelled the theme, suggestions and density dropdowns.
