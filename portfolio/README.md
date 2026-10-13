# portfolio/ — the dnesting.com site

An Astro static site. It builds both the web portfolio and `resume.pdf`: the PDF is
the homepage printed headless with Chromium, so the `@media print` block in
`src/styles/global.css` *is* the résumé layout.

## Commands

    npm run dev        # http://localhost:4321
    npm run build      # site → dist/
    npm run build:all  # site + resume.pdf (needs Docker + registry.lab.lan)
    npm run deploy     # build, publish to ../docs/, commit and push — goes LIVE

## Where content lives

| What | File |
|---|---|
| Hero copy, capability chips | `src/data/site.ts` |
| Experience timeline | `src/content/experience.mdx` |
| Showcase projects (tile + modal) | `src/content/projects/*.mdx` |
| Contact line, nav, footer | `src/layouts/Base.astro` |
| Which GitHub repos appear under "Recent contributions" | `src/data/activity.config.mjs` |
| All styling, including the print/résumé rules | `src/styles/global.css` |

Older articles under `public/2026/` and `public/projects/trunkd/` are pre-built HTML
from the pandoc rules in the repo-root Makefile; they use `public/site.css`, not the
Astro layout.

## The résumé is two pages

`scripts/build-pdf.sh` fails the build if `resume.pdf` grows to three. Note that print
lays out at 720px — under the 760px mobile breakpoint — so mobile rules apply to the
PDF unless the print block overrides them.
