#!/usr/bin/env bash
# One command to put the site live.
#   1. builds the Astro site + résumé PDF into dist/
#   2. publishes dist/ → ../docs/ (the folder GitHub Pages serves)
#   3. commits and pushes to master; Pages rebuilds automatically
# Run it as:  npm run deploy   (from portfolio/)   — or:  make deploy   (from repo root)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"   # portfolio/
repo="$(cd "$here/.." && pwd)"             # repo root

cd "$here"
echo "▶ Building site + résumé PDF…"
npm run build:all

echo "▶ Publishing dist/ → docs/ (what GitHub Pages serves)…"
rsync -a --delete dist/ "$repo/docs/"

cd "$repo"
git add -A
if git diff --cached --quiet; then
  echo "✔ Published to docs/, but nothing new to commit."
  exit 0
fi
git commit -q -m "Deploy site ($(date '+%Y-%m-%d %H:%M'))" \
  -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin master
echo "✔ Pushed. GitHub Pages will rebuild from docs/ in ~1–2 minutes → https://dnesting.com/"
