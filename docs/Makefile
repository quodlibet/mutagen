all: _rtd_theme
	sphinx-build -Dhtml_theme=_rtd_theme -Dhtml_theme_path=. -b html -n . _build

clean:
	rm -rf _build _rtd_theme

.PHONY: clean

_rtd_theme:
	wget https://github.com/snide/sphinx_rtd_theme/archive/master.tar.gz
	tar --strip-components=1 -zxvf master.tar.gz sphinx_rtd_theme-master/sphinx_rtd_theme
	mv sphinx_rtd_theme _rtd_theme
	rm master.tar.gz
