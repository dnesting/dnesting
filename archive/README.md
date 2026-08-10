# archive/

Parked concepts and explorations that we want to keep but are **not** currently
part of the site under `docs/`. Nothing here is built or deployed.

## spatial-pointcloud/

A homepage concept where the five "pages" (Home, trunkd, telescope, sdrlight,
Moon) share one 3-D space. Each title is rendered by real points distributed
through a point cloud; the camera orbits between pages, and from a given page's
vantage those points **align** into that page's title (anamorphic), while from
any other angle they read as ordinary cloud specks. There is no time-based
motion — movement comes only from moving between pages.

Key properties of the latest takes (`s4` dark / `s5` light):
- Titles are a small minority of points vs. the background cloud; the word reads
  because points **converge** (dense) head-on and **disperse** off-angle —
  purely geometric, no opacity/colour fading.
- The cloud occupies only the top ~third of the page; body content sits below.
- Primary nav is five centred rounded-rect tiles; the current page is styled
  differently.

Runnable: open any `*.html` directly, or run `python3 -m http.server` in
`spatial-pointcloud/` and browse `index.html`. three.js is vendored in
`spatial-pointcloud/vendor/three.module.js`, imported as an ES module.

Files: `s1_spatial` (first pan sketch), `s2_orbit`/`s3_paint` (earlier
full-viewport takes), `s4_orbit_dark`/`s5_paint_light` (latest). `*.png` are
reference thumbnails.
