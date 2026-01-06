SHELL := /bin/zsh

all: docs/resume.pdf docs/resume.html docs/resume.md

clean:
	rm -f docs/resume.pdf docs/resume.html docs/resume.md

#docs/%.pdf: %.md
#	pandoc -f gfm $(PANDOC) -t pdf -o $@ $<

docs/%.html: %.md resume-template.html
	pandoc -f gfm --template=resume-template.html -t html -o $@ $<

docs/%.pdf: docs/%.html
	docker run -it --rm \
		-v $(PWD):/work \
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
		--no-margins \
		file:///work/$< \
		| grep -v "ERROR:dbus"

docs/%.md: %.md
	cp $< $@

