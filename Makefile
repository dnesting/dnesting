docs/%.pdf: %.md
	pandoc -o $@ $<

all: docs/resume.pdf docs/resume.md

docs/%.md: %.md
	cp $< $@
