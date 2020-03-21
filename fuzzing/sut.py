# -*- coding: utf-8 -*-

import sys
import afl
import os

from fuzztools import run_all


def main():
    run_all(b"smoke test")

    buffer = sys.stdin.buffer
    while afl.loop(1000):
        data = buffer.read()
        try:
            run_all(data)
        finally:
            buffer.seek(0)


if __name__ == '__main__':
    main()
    os._exit(0)
