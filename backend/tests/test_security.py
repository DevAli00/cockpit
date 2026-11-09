from datetime import timedelta

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET = "x" * 48


def test_password_roundtrip_and_salting() -> None:
    h1, h2 = hash_password("correct horse"), hash_password("correct horse")
    assert h1 != h2 and "correct horse" not in h1
    assert verify_password("correct horse", h1)
    assert not verify_password("wrong", h1)


def test_verify_password_with_garbage_hash_is_false_not_error() -> None:
    assert not verify_password("x", "not-a-hash")


def test_token_roundtrip() -> None:
    tok = create_access_token("user-1", SECRET, timedelta(minutes=5))
    assert decode_access_token(tok, SECRET) == "user-1"


def test_expired_token_rejected() -> None:
    tok = create_access_token("user-1", SECRET, timedelta(seconds=-1))
    with pytest.raises(InvalidTokenError):
        decode_access_token(tok, SECRET)


def test_token_signed_with_other_secret_rejected() -> None:
    tok = create_access_token("user-1", "y" * 48, timedelta(minutes=5))
    with pytest.raises(InvalidTokenError):
        decode_access_token(tok, SECRET)


def test_garbage_token_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("abc.def.ghi", SECRET)
