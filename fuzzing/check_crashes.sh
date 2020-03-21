#!/bin/bash

set -e

export PYTHONPATH="$(pwd)/.."
RESULTS=_results

python fuzztools.py "$RESULTS"