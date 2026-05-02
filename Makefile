SHELL := /bin/zsh

ALL_MD_FILES := $(shell find docs -name lib -prune -o -type f -name "*.md" -print)
ALL_HTML_FILES := $(patsubst %.md,%.html,$(ALL_MD_FILES))

.PHONY: all clean

SBPL_PREFIX := docs/2026/macos-sandbox-sbpl-reference/index

all: $(ALL_HTML_FILES) $(SBPL_PREFIX).html docs/resume.pdf

clean:
	rm -f docs/index.html docs/resume.pdf docs/resume.html docs/resume.md $(SBPL_PREFIX).{md,html}

$(SBPL_PREFIX).md: sandbox/extract_sb_rules.py sandbox/operation-reference.md.tmpl sandbox/requirements.txt
	mkdir -p $(shell dirname "$@")
	uv run --with-requirements sandbox/requirements.txt \
		python3 sandbox/extract_sb_rules.py
	cp sandbox/generated/operation-reference.md $@

$(SBPL_PREFIX).html: $(SBPL_PREFIX).md template.html
	pandoc -f gfm --section-divs --template=template.html --standalone -V body-class=wide-reference -t html -o $@ $<

#docs/%.pdf: %.md
#	pandoc -f gfm $(PANDOC) -t pdf -o $@ $<

docs/%.html: %.md template.html
	pandoc -f gfm --template=template.html --standalone -t html -o $@ $<

%.html: %.md template.html
	pandoc -f gfm --template=template.html --standalone -t html -o $@ $<

%.pdf: %.html
	docker run -it --rm \
		-v $(PWD):/work \
		-v $(PWD)/docs/site.css:/site.css \
		-e XDG_CONFIG_HOME=/tmp \
		-e XDG_CACHE_HOME=/tmp \
		-e DBUS_SESSION_BUS_ADDRESS=disabled: \
		registry.lab.lan/chromium:dev \
		chromium \
		--no-sandbox \
		--headless \
		--autoplay-policy=no-user-gesture-required \
		--no-first-run \
		--disable-gpu \
		--use-fake-ui-for-media-stream \
		--use-fake-device-for-media-stream \
		--disable-sync \
		--no-sandbox \
		--no-crashpad \
		--disable-crash-reporter \
		--print-to-pdf=/work/$@ \
		--no-pdf-header-footer \
		file:///work/$< \
		| grep -v "ERROR:dbus"

#		--no-margins \
