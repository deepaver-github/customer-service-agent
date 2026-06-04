"""Password hashing using stdlib scrypt (OWASP-accepted, no extra deps).

Encoded format: ``scrypt$<n>$<r>$<p>$<salt_hex>$<key_hex>``.
"""
from __future__ import annotations

import hashlib
import secrets

# OWASP minimums for scrypt as of 2024.
_N = 16384
_R = 8
_P = 1
_DKLEN = 32
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DKLEN,
        maxmem=64 * 1024 * 1024,
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    if not encoded:
        return False
    try:
        scheme, n, r, p, salt_hex, key_hex = encoded.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    try:
        n_i, r_i, p_i = int(n), int(r), int(p)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
    except ValueError:
        return False
    actual = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n_i,
        r=r_i,
        p=p_i,
        dklen=len(expected),
        maxmem=64 * 1024 * 1024,
    )
    return secrets.compare_digest(actual, expected)
