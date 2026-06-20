from io import BytesIO
from typing import NamedTuple


class FileThing(NamedTuple):
    fileobj: BytesIO
    filename: str | bytes | None
    name: str | bytes
