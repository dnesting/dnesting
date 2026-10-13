SHELL := /bin/zsh

# ── The site is an Astro project in portfolio/ (GitHub Pages serves docs/) ─────
.DEFAULT_GOAL := help
.PHONY: help dev build deploy

help:
	@echo "Site = Astro project in portfolio/  (GitHub Pages serves docs/)."
	@echo ""
	@echo "  make dev     run locally at http://localhost:4321"
	@echo "  make build   build the site + résumé PDF into portfolio/dist"
	@echo "  make deploy  build, publish to docs/, commit & push  (goes LIVE)"
	@echo ""
	@echo "(The pandoc rules below are the retired old pipeline; the blog is now"
	@echo " static under portfolio/public/.)"

dev:
	cd portfolio && npm run dev

build:
	cd portfolio && npm run build:all

deploy:
	cd portfolio && npm run deploy

# ── Legacy pandoc pipeline (retired) ──────────────────────────────────────────

ALL_MD_FILES := $(shell find docs -name lib -prune -o -type f -name "*.md" -print)
ALL_HTML_FILES := $(patsubst %.md,%.html,$(ALL_MD_FILES))

.PHONY: all clean

SBPL_PREFIX := docs/2026/macos-sandbox-sbpl-reference/index
PORTFOLIO_TEMPLATE := template-portfolio.html

all: $(ALL_HTML_FILES) $(SBPL_PREFIX).html

clean:
	rm -f docs/index.html $(SBPL_PREFIX).{md,html}

$(SBPL_PREFIX).md: sandbox/extract_sb_rules.py sandbox/operation-reference.md.tmpl sandbox/requirements.txt
	mkdir -p $(shell dirname "$@")
	uv run --with-requirements sandbox/requirements.txt \
		python3 sandbox/extract_sb_rules.py
	cp sandbox/generated/operation-reference.md $@

$(SBPL_PREFIX).html: $(SBPL_PREFIX).md template.html
	pandoc -f gfm --section-divs --template=template.html --standalone -V body-class=wide-reference -t html -o $@ $<

#docs/%.pdf: %.md
#	pandoc -f gfm $(PANDOC) -t pdf -o $@ $<

# Portfolio pages use the bespoke dark template (more specific stem wins).
docs/index.html: docs/index.md $(PORTFOLIO_TEMPLATE)
	pandoc -f gfm --template=$(PORTFOLIO_TEMPLATE) --standalone -t html -o $@ $<

docs/projects/%/index.html: docs/projects/%/index.md $(PORTFOLIO_TEMPLATE)
	mkdir -p $(dir $@)
	pandoc -f gfm --template=$(PORTFOLIO_TEMPLATE) --standalone -t html -o $@ $<

docs/%.html: %.md template.html
	pandoc -f gfm --template=template.html --standalone -t html -o $@ $<

%.html: %.md template.html
	pandoc -f gfm --template=template.html --standalone -t html -o $@ $<
