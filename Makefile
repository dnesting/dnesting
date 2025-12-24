docs/%.html: %.md
	pandoc -f gfm -t html -s -o $@ $<

all: docs/resume.html docs/resume.md

docs/%.md: %.md
	cp $< $@
