#!/bin/bash
# ./run_wine.sh 2.7 setup.py test
# ./run_wine.sh 3.4 setup.py test

DIR=$(mktemp -d)
export WINEPREFIX="$DIR/_wine_env"
export WINEDLLOVERRIDES="mscoree,mshtml="
mkdir -p "$WINEPREFIX"

if [ "$1" == "2.7" ]
then
    wget -P "$DIR" -c "http://www.python.org/ftp/python/2.7.11/python-2.7.11.msi"
    wine msiexec /a "$DIR/python-2.7.11.msi" /qb
    PYDIR="$WINEPREFIX/drive_c/Python27"
elif [ "$1" == "3.4" ]
then
    wget -P "$DIR" -c "http://www.python.org/ftp/python/3.4.4/python-3.4.4.msi"
    wine msiexec /a "$DIR/python-3.4.4.msi" /qb
    PYDIR="$WINEPREFIX/drive_c/Python34"
else
    exit 1
fi

wine "$PYDIR/python.exe" ${@:2}
exit_code=$?
wineserver --wait
rm -Rf "$DIR"
exit $exit_code
