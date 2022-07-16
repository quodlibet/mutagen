all:
	python3 -m sphinx -j auto -b html -n . _build

clean:
	rm -rf _build

linkcheck:
	sphinx-build -b linkcheck -n . _build

watch:
	sphinx-autobuild -j auto -b html -n . _build

.PHONY: clean watch linkcheck
