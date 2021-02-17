
from mutagen._iff import is_valid_chunk_id


def test_is_valid_chunk_id():
    assert not is_valid_chunk_id("")
    assert is_valid_chunk_id("QUUX")
    assert not is_valid_chunk_id("FOOBAR")
