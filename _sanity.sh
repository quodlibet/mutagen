#!/bin/sh

if test "$1" = "--help" -o "$1" = "-h"; then
 echo "Usage: $0 --sanity | [TestName] ..."
 exit 0
elif [ "$1" = "--sanity" ]; then
 echo "Running static sanity checks."
 grep "except None:" *.py */*.py
 exit $?
else
 python -c "import tests; tests.unit('$*'.split())"
fi
