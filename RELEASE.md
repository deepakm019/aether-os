# Release checklist

Maintainer-only. These items are not shown in the app.

## Before any public release

- [ ] **Contact channel.** Publish a real support and privacy contact (email, form or issue tracker). Add it to the Legal page as a short "Contact" section. Do not ship a placeholder address.
- [ ] **Licence files.** Add a `LICENSE` file (and `NOTICE` if needed) and set the matching `license` field in `package.json`. Currently `package.json` says `UNLICENSED`, and no licence file exists.
- [ ] **Legal review.** Have a qualified lawyer review the Legal page for your jurisdiction. Check consumer-law wording, the liability cap and currency (the cap is currently in INR), and the indemnity clause. The page is not legal advice.
- [ ] **Hosting notices.** If the app is hosted (for example on GitHub Pages), confirm section 06 names the actual host and any notification or OS services it uses.
- [ ] **Run `npm run verify`** (static gate and browser suites) and confirm the CI run on the release commit is green.
- [ ] **Bump `CACHE_NAME`** in `sw.js` whenever app-shell files change, so installed clients receive the update.

## Before enabling a new kind of data handling

Update the Legal page **before** you turn any of these on:

- [ ] Analytics or telemetry
- [ ] Cloud sync or accounts (authentication)
- [ ] Payments or subscriptions
- [ ] Advertising
- [ ] Third-party APIs that receive user data
- [ ] Remote AI or any service that processes user content

Each of these changes what data leaves the browser, so the privacy and data-handling wording must change first.

## After each release

- [ ] Re-check that the README feature list and test counts match the shipped build.
- [ ] Tag the release commit (for example `v5.25`) and add a changelog entry.
- [ ] Re-check the Legal page date and version, if you show one.
