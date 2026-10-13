#!/usr/bin/env bash
# Generate resume.pdf from the built site by printing the homepage with its
# @media print stylesheet, using the lab headless-chromium image.
# Run AFTER `npm run build` (or use `npm run build:all`). Requires Docker.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f dist/index.html ]; then
  echo "dist/index.html not found — run 'npm run build' first." >&2
  exit 1
fi

PORT=8799
python3 -m http.server "$PORT" --directory dist >/dev/null 2>&1 &
SRV=$!
trap 'kill "$SRV" 2>/dev/null || true' EXIT
sleep 1

HOSTIP="$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1)"

docker run --rm --user 0 --tmpfs /work -e HOME=/work \
  -v "$PWD/dist":/out \
  registry.lab.lan/chromium:dev chromium \
  --no-sandbox --headless=new --disable-gpu \
  --enable-unsafe-swiftshader --use-gl=angle --use-angle=swiftshader \
  --user-data-dir=/work/cr --no-pdf-header-footer --virtual-time-budget=6000 \
  --print-to-pdf=/out/resume.pdf \
  "http://$HOSTIP:$PORT/" 2>&1 | grep -iv dbus || true

# The résumé is meant to be two pages. Fail the build if it grows a third, so a
# new bullet can't silently push it over. Needs poppler (`brew install poppler`);
# where pdfinfo is missing the check is skipped with a warning, not an error.
MAX_PAGES=2
if command -v pdfinfo >/dev/null 2>&1; then
  pages="$(pdfinfo dist/resume.pdf | awk '/^Pages:/{print $2}')"
  if [ "${pages:-0}" -gt "$MAX_PAGES" ]; then
    echo "resume.pdf is ${pages} pages; the limit is ${MAX_PAGES}." >&2
    echo "Tighten the @media print block in src/styles/global.css, or cut content." >&2
    exit 1
  fi
  echo "résumé is ${pages} page(s) (limit ${MAX_PAGES})"
else
  echo "warning: pdfinfo not found — skipping the ${MAX_PAGES}-page check." >&2
fi

# Keep a copy in public/ so `npm run dev` can also serve /resume.pdf.
cp -f dist/resume.pdf public/resume.pdf
echo "wrote dist/resume.pdf (and public/resume.pdf)"
