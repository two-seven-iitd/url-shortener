CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
BASE = len(CHARSET)


def encode_base62(num: int) -> str:
    """Convert a non-negative integer to a base62 string."""
    if num < 0:
        raise ValueError("num must be non-negative")
    if num == 0:
        return CHARSET[0]

    result = []
    while num > 0:
        num, rem = divmod(num, BASE)
        result.append(CHARSET[rem])

    return "".join(reversed(result))


def decode_base62(code: str) -> int:
    """Convert a base62 string back to an integer."""
    num = 0
    for char in code:
        num = num * BASE + CHARSET.index(char)
    return num
