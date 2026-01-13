from io import BytesIO
from typing import NamedTuple


class FileThing(NamedTuple):
    """
    filename is None if the source is not a filename.
    name is a filename which can be used for file type detection.
    """
    fileobj: BytesIO
    filename: str | bytes | None
    name: str | None
