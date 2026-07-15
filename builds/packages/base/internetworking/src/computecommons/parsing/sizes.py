from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from computecommons.units import ByteSize

_SIZE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*([KMGTPE]?i?B?|bytes?)?\s*$", re.IGNORECASE)
_FACTORS = {
    "": 1, "B": 1, "BYTE": 1, "BYTES": 1,
    "K": 1000, "KB": 1000, "KI": 1024, "KIB": 1024,
    "M": 1000**2, "MB": 1000**2, "MI": 1024**2, "MIB": 1024**2,
    "G": 1000**3, "GB": 1000**3, "GI": 1024**3, "GIB": 1024**3,
    "T": 1000**4, "TB": 1000**4, "TI": 1024**4, "TIB": 1024**4,
    "P": 1000**5, "PB": 1000**5, "PI": 1024**5, "PIB": 1024**5,
    "E": 1000**6, "EB": 1000**6, "EI": 1024**6, "EIB": 1024**6,
}


def parse_byte_size(value: str) -> ByteSize:
    match = _SIZE.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid byte size: {value!r}")
    number_text, unit = match.groups()
    try:
        number = Decimal(number_text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid byte size: {value!r}") from exc
    if number < 0:
        raise ValueError("Byte size cannot be negative")
    factor = _FACTORS[(unit or "").upper()]
    byte_count = int((number * factor).to_integral_value(rounding=ROUND_HALF_UP))
    return ByteSize(byte_count)
