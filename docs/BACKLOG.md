# Backlog

Working list of planned features and improvements. Each item ships in its own PR with tests. Usability is an estimate of daily value for a typical user, not a measured result.

## Bug fixes (first)

- **Name overlap in split view on phones.** Names collide on small screens when choosing who is involved. Fix the layout and add a 320 px test.

## Planned items

| # | Item | Type | Usability |
|---|---|---|---|
| 1 | Backups with timestamp | Extra | 95% |
| 2 | Configurable timer | Feature | 90% |
| 3 | Unit converter (ft↔m, lb↔kg, etc.) | Feature | 90% |
| 4 | Offline weekly review page | Extra | 90% |
| 5 | Today shows top 3 tasks, one-tap timer start | Extra | 90% |
| 6 | Calendar export (.ics) | Integration | 85% |
| 7 | Auto-sort on completion | Feature | 85% |
| 8 | Work board: drag between tabs | Extra | 85% |
| 9 | Focus: end-of-session note logged to task | Extra | 85% |
| 10 | Reminder snooze presets | Extra | 85% |
| 11 | Quick-add expense from Today | Extra | 85% |
| 12 | Email digest (copy-paste summary) | Integration | 85% |
| 43 | Code snippets in Notes | Feature | 85% |
| 44 | Prompt builder (form to structured prompt) | Feature | 85% |
| 13 | WhatsApp share link (wa.me) | Integration | 80% |
| 14 | Habit streaks with calendar heat map | Feature | 80% |
| 15 | Upcoming bills on Today (next 7 days) | Extra | 80% |
| 16 | Shareable weekly PNG card | Integration | 80% |
| 45 | Prompt library (save, tag, search prompts) | Feature | 80% |
| 17 | Share target for Inbox (phone share sheet) | Integration | 75% |
| 18 | Kiosk focus card for a spare tablet | Integration | 75% |
| 19 | Recurring tasks: show next 3 occurrences | Extra | 75% |
| 20 | Calendar week view with category colours | Extra | 75% |
| 21 | Notes: pin notes, search inside text | Extra | 75% |
| 22 | Trash: days remaining before deletion | Extra | 75% |
| 23 | Decision journal with review loop | Feature | 70% |
| 24 | QR tags (scan to open a task or timer) | Integration | 70% |
| 25 | Planner: auto-fill open windows | Extra | 70% |
| 26 | Goals: progress bars and next step | Extra | 70% |
| 27 | Weekly review prompt (auto-filled) | Extra | 70% |
| 28 | Money CSV import | Integration | 65% |
| 29 | Voice announcement on completion (setting) | Feature | 65% |
| 30 | Workouts: repeat last session, personal bests | Extra | 65% |
| 31 | Money: monthly planned vs actual | Extra | 65% |
| 32 | Voice capture via Siri Shortcuts | Integration | 60% |
| 33 | Markdown export (Obsidian-friendly) | Integration | 60% |
| 34 | Memory: "on this day" view | Extra | 60% |
| 35 | Theme preview before applying | Extra | 60% |
| 36 | Browser reminders (notifications) | Integration | 55% |
| 37 | Bulk import from other apps (Todoist, Notion, etc.) | Integration | 55% |
| 38 | Settings export and import | Extra | 50% |
| 39 | Commute and transit "leave by" times | Integration | 45% |
| 42 | Device sync via QR and WebRTC | Integration | 30% |

## Parked

- **On-device language parsing.** Needs a model download, WebGPU, and a CSP exception. Revisit only if rule-based parsing proves insufficient.

## Conventions

- Each item needs unit or browser tests, plus a responsive check at 320, 390, 768, and 1280 px.
- Items that add third-party code, network calls, or data leaving the browser need a Legal page update first (see `RELEASE.md`).
- Item numbers are stable. Do not renumber when items are added or removed.
