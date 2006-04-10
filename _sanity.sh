#!/bin/sh

set -e

if test "$1" = "--help" -o "$1" = "-h"; then
    echo "Usage: $0 --sanity | [TestName] ..."
    exit 0
elif [ "$1" = "--sanity" ]; then
    echo "Running static sanity checks."
    grep "except None:" *.py */*.py
else
    python -c "import tests; raise SystemExit(tests.unit('$*'.split()))"
fi
