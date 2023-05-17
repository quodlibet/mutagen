import os

from hypothesis import settings


if "CI" in os.environ:
    # CI can be slow, so be patient
    # Also we can run more tests there
    settings.register_profile(
        "ci",
        deadline=settings.default.deadline * 10,
        max_examples=settings.default.max_examples * 5)
    settings.load_profile("ci")
