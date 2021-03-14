Fuzzing
=======

Uses `python-afl <https://github.com/jwilk/python-afl>`__ and `afl
<https://lcamtuf.coredump.cx/afl/>`__

* Install afl, for example ``sudo apt install afl++`` on Debian/Ubuntu
* ``poetry install -E fuzzing-dev``
* ``poetry shell``
* Add some example files into ``_examples``
* ``./run.sh`` will start multiple afl-fuzz instances
* CTRL+C to stop
* Run ``./check_crashes.sh`` to get a summary of the errors found
