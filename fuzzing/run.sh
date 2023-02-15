#!/bin/bash

set -e

export PYTHONPATH="$(pwd)/.."
export AFL_HANG_TMOUT=1000
export AFL_SKIP_CPUFREQ=1
export AFL_NO_AFFINITY=1
export AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

EXAMPLES=_examples
RESULTS=_results

mkdir -p "$RESULTS"
mkdir -p "$EXAMPLES"

cp -f ../tests/data/* "$EXAMPLES"

for i in `seq 2 $(nproc)`; do
    py-afl-fuzz -i "$EXAMPLES" -o "$RESULTS" -S "worker-$i"  -- $(which python) sut.py > /dev/null 2>&1 &
done

py-afl-fuzz -i "$EXAMPLES" -o "$RESULTS" -M "main" -- $(which python) sut.py > /dev/null 2>&1 &
watch -n 1 -c afl-whatsup -s "$RESULTS"
pkill afl-fuzz
