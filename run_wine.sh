#!/bin/bash
# ./run_wine.sh 2.7.12 python
# ./run_wine.sh 2.7.12 cmd
# ./run_wine.sh 3.4.4 python
# ./run_wine.sh 3.4.4 cmd

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
PIPEXE="$WINEPREFIX/drive_c/$DIRNAME/Scripts/pip.exe"
wget "https://bootstrap.pypa.io/get-pip.py"
wine "$PYTHONEXE" get-pip.py
rm get-pip.py
wine "$PIPEXE" install pytest
wine "$PIPEXE" install coverage

if [ "$2" == "cmd" ]; then
    wineconsole --backend=curses
elif [ "$2" == "python" ]; then
    wine "$PYTHONEXE" ${@:3}
else
    wine ${@:2}
fi

exit_code=$?
wineserver --wait
rm -Rf "$DIR"
exit $exit_code
