#!/bin/bash
# ./run_wine.sh 2.7.11 setup.py test
# ./run_wine.sh 3.4.4 setup.py test

DIR=$(mktemp -d)
export WINEPREFIX="$DIR/_wine_env"
export WINEDLLOVERRIDES="mscoree,mshtml="
export WINEDEBUG="-all"
mkdir -p "$WINEPREFIX"

VERSION="$1"
TEMP=${VERSION//./}
DIRNAME="Python"${TEMP:0:2}

wget -P "$DIR" -c "https://www.python.org/ftp/python/$VERSION/python-$VERSION.msi"
wine msiexec /a "$DIR/python-$VERSION.msi" /qb

PYTHONEXE="$WINEPREFIX/drive_c/$DIRNAME/python.exe"
wine "$PYTHONEXE" ${@:2}
exit_code=$?
wineserver --wait
rm -Rf "$DIR"
exit $exit_code
