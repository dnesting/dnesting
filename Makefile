docs/%.pdf: %.md
	pandoc -o $@ $<

all: docs/resume.pdf
