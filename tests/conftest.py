import os
import platform

from hypothesis import settings


if "CI" in os.environ:
    # CI can be slow, so be patient
    # Also we can run more tests there

    max_examples = settings.default.max_examples * 5
    if platform.python_implementation() == "PyPy":
        # PyPy is too slow
        max_examples = settings.default.max_examples

    settings.register_profile(
        "ci",
        deadline=settings.default.deadline * 10,
        max_examples=max_examples)
    settings.load_profile("ci")
