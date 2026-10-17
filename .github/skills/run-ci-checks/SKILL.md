---
name: run-ci-checks
description: Reproduce the GitHub Actions CI pipeline for AstralSurge OS locally (static gate, Playwright tests, Python dependency audit, secret scan) before committing or opening a PR.
---

# Run the CI checks locally

Use this skill before committing, before opening or updating a pull request, or when a CI job fails and you need to reproduce it. It mirrors `.github/workflows/ci.yml` in the same order CI uses.

CodeQL runs only in GitHub Actions. It cannot be reproduced locally, so check its result on the PR instead.

## 1. Static build gate

```bash
npm run check
```

This is the same as the `static-checks` job. It has no dependencies, runs on Node 20 or newer (CI uses Node 22), and must pass before any other job runs. It checks:

- the inline app script parses,
- no `eval` or `new Function`,
- the Content-Security-Policy is present, does not allow `unsafe-eval`, and restricts `connect-src`,
- no external script, link, or CSS URL references in `index.html`,
- `sw.js` parses, has a versioned `CACHE_NAME`, and caches no external origins,
- app-shell files exist, `manifest.json` parses, `CNAME` and `.nojekyll` are present.

If you changed `index.html`, `sw.js`, or any app-shell file, bump `CACHE_NAME` in `sw.js` (for example `astralsurge-os-v5.41` to `v5.42`). The gate checks that the name is versioned, but `AGENTS.md` requires the bump.

## 2. Browser tests (Playwright)

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install --with-deps chromium
python -m pytest
```

This is the `browser-tests` job. `npm run test` runs the same pytest command. `tests/conftest.py` starts the local server, so you do not need to run one yourself. To iterate on one suite, see `.github/skills/run-playwright-tests/SKILL.md`.

The `--with-deps` flag installs the Linux system libraries that Chromium needs. CI uses it, so match it locally on Linux.

## 3. Python dependency audit

```bash
python -m pip install --upgrade pip pip-audit
pip-audit -r requirements-dev.txt --strict
```

This is the `dependency-audit` job. `--strict` fails on any known vulnerability, including those with no fix available. If a finding has no fix, record the decision in the PR description instead of silencing it.

## 4. Secret scan (gitleaks)

```bash
docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:v8.24.3 \
  detect --source=/repo --redact --exit-code=1 --no-banner
```

This is the `secret-scan` job. It needs Docker and scans the full git history, so run it from a full clone. If Docker is not available, say so in your report rather than marking the scan as passed. Never disable the scan or add an allowlist entry to get a pass; rotate the exposed secret and remove it from history instead.

## Reporting

Report each step as passed, failed, or not run, with the reason for anything not run. Quote the failing line from the output. Do not describe a step as passed unless its command exited with code 0.

## Rules that apply here

- `AGENTS.md` requires `npm run check` before every commit and CI to pass before merging. Do not bypass the static gate or the secret scan.
- If a change touches attachments, vault data, or encryption, also verify the behaviour listed in `AGENTS.md` in a browser. The test suites do not cover every path.
