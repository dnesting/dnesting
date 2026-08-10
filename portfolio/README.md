# portfolio/ — working area for the new site

This is the durable home for the new portfolio/résumé (moved out of `/tmp` scratch).
Nothing here is published yet; `docs/` still serves the old site.

## What's here
- `index.html` — the interactive résumé (hero, capabilities, experience timeline,
  showcase tiles → modals, embedded trunk'd architecture diagram, print/PDF styles).
- `detail_copy.md` — first-person draft copy for each tile's modal.
- `t2_incidents.png` — screenshot used as the trunk'd tile cover.
- `photos/` — **drop your images here.**

## Dropping photos
Put images in `photos/` with descriptive names, and tell me which project/role each
belongs to (e.g. `luna-relief-wall.jpg`, `opm-mainframe.jpg`). I'll wire them into the
right modal (Luna gallery, the OPM items, etc.) and size/crop as needed.

## Next step
Decide the site generator (Astro / Hugo / Eleventy). That turns this single `index.html`
into per-page Markdown + a small amount of structured data for the experience/projects,
and gives photos a proper assets pipeline. The print/PDF work and the diagram carry over
unchanged.
