# Backlog

Working list of planned features and improvements. Each item ships in its own PR with tests. Usability is an estimate of daily value for a typical user, not a measured result.

Status was refreshed on 17 Oct 2026 by checking the app code. Items marked **Partly** have some of the feature in place; the remaining gap is listed.

## Bug fixes (first)

- **Name overlap in split view on phones.** Names collide on small screens when choosing who is involved. Fix the layout and add a 320 px test.

## Shipped

| # | Item | Notes |
|---|---|---|
| 2 | Configurable timer | Preset focus lengths (`setFocusLen`) |
| 5 | Today shows top 3 tasks | "Top 3" on Today, with start-focus action |
| 6 | Calendar export (.ics) | `BEGIN:VCALENDAR` export |
| 7 | Auto-sort on completion | Tasks only; goals and milestones not yet covered |
| 10 | Reminder snooze presets | `snoozeReminder` |
| 13 | WhatsApp share link (wa.me) | |
| 14 | Habit streaks with calendar heat map | Heat grid in habit view |
| 15 | Upcoming bills | "Upcoming bills" panel, next 30 days |
| 22 | Trash: days remaining before deletion | "days left" shown |
| 23 | Decision journal with review loop | Awaiting-reconciliation rule |
| 26 | Goals: progress bars and next step | Progress bars on goal cards |
| 27 | Weekly review prompt (auto-filled) | Home card covers Monday through today |
| 30 | Workouts: repeat last session, personal bests | |
| 36 | Browser reminders (notifications) | Notification API with permission request |
| 44 | Prompt builder | |

Also shipped: polish for timer input theme; converter speed, area, time and data categories.

## Partly shipped

| # | Item | Already in place | Still missing |
|---|---|---|---|
| 1 | Backups with timestamp | Backup and export actions exist | Confirm the filename includes a timestamp |
| 3 | Unit converter (ft↔m, lb↔kg, etc.) | Converter with speed, area, time, data | Confirm length and weight categories |
| 4 | Offline weekly review page | Weekly review modal | A standalone page that works offline |
| 9 | Focus: end-of-session note logged to task | Focus completion saves time | Note prompt at session end |
| 11 | Quick-add expense from Today | Expense entry exists | Quick-add from Today specifically |
| 16 | Shareable weekly PNG card | PNG export code exists | Confirm it is wired to the weekly review |
| 21 | Notes: pin notes, search inside text | Pinned and search in minimal mode; search in main workspace | Confirm pin and text search in main notes |
| 25 | Planner: auto-fill open windows | Open-window finder exists | Auto-fill the planner from open windows |
| 31 | Money: monthly planned vs actual | Budgets and decision actuals | Monthly planned vs actual view |
| 38 | Settings export and import | Full workspace export and restore | Settings-only export and import |
| 8 | Work board: drag between tabs | Drag in minimal mode only | Drag tasks between Work tabs |
| 32 | Voice capture via Siri Shortcuts | Quick Capture home-screen shortcut | Siri Shortcuts integration |

## Planned

| # | Item | Type | Usability |
|---|---|---|---|
| 12 | Email digest (copy-paste summary) | Integration | 85% |
| 17 | Share target for Inbox (phone share sheet) | Integration | 75% |
| 18 | Kiosk focus card for a spare tablet | Integration | 75% |
| 19 | Recurring tasks: show next 3 occurrences | Extra | 75% |
| 20 | Calendar week view with category colours | Extra | 75% |
| 24 | QR tags (scan to open a task or timer) | Integration | 70% |
| 28 | Money CSV import | Integration | 65% |
| 29 | Voice announcement on completion (setting) | Feature | 65% |
| 33 | Markdown export (Obsidian-friendly) | Integration | 60% |
| 34 | Memory: "on this day" view | Extra | 60% |
| 35 | Theme preview before applying | Extra | 60% |
| 37 | Bulk import from other apps (Todoist, Notion, etc.) | Integration | 55% |
| 39 | Commute and transit "leave by" times | Integration | 45% |
| 42 | Device sync via QR and WebRTC (on hold: needs a decision on signalling and network use, see PR notes) | Integration | 30% |
| 43 | Code snippets in Notes | Feature | 85% |
| 45 | Prompt library (save, tag, search prompts) | Feature | 80% |

## Parked

- **On-device language parsing.** Needs a model download, WebGPU, and a CSP exception. Revisit only if rule-based parsing proves insufficient.

## Conventions

- Each item needs unit or browser tests, plus a responsive check at 320, 390, 768, and 1280 px.
- Items that add third-party code, network calls, or data leaving the browser need a Legal page update first (see `RELEASE.md`).
- Item numbers are stable. Do not renumber when items are added or removed.
