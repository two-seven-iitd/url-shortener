import pytest

from app.core.base62 import decode_base62, encode_base62


def test_encode_known_values():
    assert encode_base62(0) == "a"
    assert encode_base62(1) == "b"
    assert encode_base62(62) == "ba"
    assert encode_base62(238328) == "baaa"


@pytest.mark.parametrize("num", [0, 1, 61, 62, 1000, 238328, 999999999])
def test_roundtrip(num):
    assert decode_base62(encode_base62(num)) == num


def test_encode_rejects_negative():
    with pytest.raises(ValueError):
        encode_base62(-1)


def test_codes_are_unique_and_ordered_by_id():
    codes = [encode_base62(i) for i in range(1000)]
    assert len(set(codes)) == len(codes)
