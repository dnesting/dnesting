SHELL := /bin/zsh

ALL_MD_FILES := $(shell find docs -name lib -prune -o -type f -name "*.md" -print)
ALL_HTML_FILES := $(patsubst %.md,%.html,$(ALL_MD_FILES))

all: $(ALL_HTML_FILES) docs/resume.pdf

clean:
	rm -f docs/index.html docs/resume.pdf docs/resume.html docs/resume.md

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
