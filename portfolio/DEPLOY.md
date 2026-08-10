# Deploying the portfolio

**Status: not live yet.** `dnesting.com` still serves the old site from `docs/`.
Everything below is prepared but intentionally not executed — flipping the live
site is the one deliberate step left.

## What's ready
- `astro build` → `dist/` (static, custom domain at root; `public/CNAME` = `dnesting.com`).
- `npm run build:all` → builds the site **and** regenerates `dist/resume.pdf` (headless
  Chromium via Docker), copying it to `public/resume.pdf` so it's committed and served
  without needing Chromium in CI.
- A dormant GitHub Actions workflow: `.github/workflows/deploy-portfolio.yml`
  (manual-trigger only).

## Option A — GitHub Actions (recommended)
1. Commit `portfolio/` (including `public/resume.pdf`).
2. Repo **Settings → Pages → Source: GitHub Actions**.
3. Run the **"Deploy portfolio (Astro → Pages)"** workflow (Actions tab → Run workflow),
   or add a `push` trigger to it.
4. Confirm the custom domain (`dnesting.com`) in Settings → Pages.

## Option B — build into `docs/` (matches the current habit)
1. Set `outDir: '../docs'` in `astro.config.mjs` (and keep `docs/` clean of the old
   pandoc output).
2. `npm run build:all`, commit `docs/`.
3. Pages stays on "deploy from branch → /docs".

## Before every deploy
Re-run `npm run build:all` so `public/resume.pdf` reflects the latest résumé content,
and commit it.

## Still to migrate off the old site
The blog posts and the SBPL reference under `docs/2026/**` are still pandoc-built. They
need porting into Astro (a `blog`/`writing` collection) before `docs/` can be fully
retired. Until then, keep those pages if switching to Option A.
