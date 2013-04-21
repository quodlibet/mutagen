# create man pages in ./_man

all: mid3iconv.1 mid3v2.1 moggsplit.1 mutagen-inspect.1 mutagen-pony.1

setup:
	mkdir -p _man

%.1:%.rst setup
	rst2man $< > _man/$@

.PHONY: setup
