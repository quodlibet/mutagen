Fuzzing
=======

Local fuzzing via `python-afl <https://github.com/jwilk/python-afl>`__ and `afl++
  <https://aflplus.plus/>`__:

* Install afl, for example ``sudo apt install afl++`` on Debian/Ubuntu
* ``poetry install --with fuzzing``
* ``poetry shell``
* Add some example files into ``_examples``
* ``./run.sh`` will start multiple afl-fuzz instances
* CTRL+C to stop
* Run ``./check_crashes.sh`` to get a summary of the errors found

Fuzzing via `OSS-Fuzz <https://github.com/google/oss-fuzz>`__:

* mutagen was initially added here: https://github.com/google/oss-fuzz/pull/10072
* The integration code is here: https://github.com/google/oss-fuzz/tree/master/projects/mutagen
* Maintainers get emails about new findings, and after 90 days they are made public
* Already public crash results can be found here: https://bugs.chromium.org/p/oss-fuzz/issues/list?q=label:Proj-mutagen
* Once fixed in mutagen, the reports will be closed automatically
