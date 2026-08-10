---
layout: ../layouts/Base.astro
title: "Colophon — David Nesting"
description: "How this site is built."
---

# Colophon

You've reached the part of the site that explains itself. Fitting.

This site is a static [Astro](https://astro.build/) build. Every page shares one
`Base.astro` layout — the header, footer, and the hash-routed detail modals — so the
homepage, this page, and anything I add later stay consistent without copy-paste.

## How it's made

- **Astro** — static generation, ~zero client JavaScript. The only script on the page is the one that runs the detail modals.
- **One hand-written stylesheet** — a light theme, system `--sans` / `--mono` fonts, and an `@media print` block that turns the homepage into a clean two-page résumé. (The "Résumé PDF" link *is* that page, printed headless with Chromium.)
- **Inline SVG** for the architecture diagrams — no diagramming library, no runtime.
- **Optimized images** served from `public/`; the Moon's projection-mapping clip is a compressed H.264 loop.

No trackers, no analytics, no cookie banner. If something here looks broken — well, I void warranties.
