all: docs/resume.pdf docs/resume.html docs/resume.md

#docs/%.pdf: %.md
#	pandoc -f gfm $(PANDOC) -t pdf -o $@ $<

docs/%.html: %.md resume-template.html
	pandoc -f gfm --template=resume-template.html -t html -o $@ $<

docs/%.pdf: docs/%.html
	docker run -it --rm -v $(PWD):/work registry.lab.lan/chromium:dev chromium --headless --disable-gpu --no-sandbox --print-to-pdf=/work/$@ --no-margins file:///work/$<

docs/%.md: %.md
	cp $< $@

