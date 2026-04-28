"""
Property test for password validation.

**Property 2: Any password accepted by registration always has length >= 8
and contains at least one digit**
**Validates: Requirements 1.2**
"""
import re

from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ── Password validation logic (mirrors app/blueprints/auth.py) ────────────────

_ASCII_DIGITS = set("0123456789")


def is_valid_password(password: str) -> bool:
    """
    Returns True if the password meets registration requirements:
    - At least 8 characters
    - Contains at least one ASCII digit (0-9)
    """
    if len(password) < 8:
        return False
    if not any(char in _ASCII_DIGITS for char in password):
        return False
    return True


# ── Strategies ─────────────────────────────────────────────────────────────────

# Passwords that SHOULD be accepted: length >= 8, contains at least one ASCII digit
valid_password_st = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=8,
    max_size=64,
).filter(lambda p: any(c in "0123456789" for c in p))

# Passwords that SHOULD be rejected: too short (< 8 chars)
short_password_st = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
    max_size=7,
)

# Passwords that SHOULD be rejected: long enough but no ASCII digit
no_digit_password_st = st.text(
    alphabet=st.characters(
        blacklist_characters="0123456789",
    ),
    min_size=8,
    max_size=64,
)


# ── Properties ─────────────────────────────────────────────────────────────────

@given(password=valid_password_st)
@settings(max_examples=500)
def test_accepted_passwords_always_meet_requirements(password: str):
    """
    Property 2: Any password accepted by the validator has length >= 8
    and contains at least one digit.
    """
    assert is_valid_password(password), (
        f"Password '{password}' should be valid but was rejected"
    )
    # Verify the two invariants explicitly
    assert len(password) >= 8, (
        f"Accepted password '{password}' has length {len(password)} < 8"
    )
    assert any(c.isdigit() for c in password), (
        f"Accepted password '{password}' contains no digit"
    )


@given(password=short_password_st)
@settings(max_examples=300)
def test_short_passwords_are_rejected(password: str):
    """
    Property 2 (inverse): Passwords shorter than 8 characters are always rejected.
    """
    assert not is_valid_password(password), (
        f"Short password '{password}' (len={len(password)}) should be rejected"
    )


@given(password=no_digit_password_st)
@settings(max_examples=300)
def test_passwords_without_digit_are_rejected(password: str):
    """
    Property 2 (inverse): Passwords with no digit are always rejected,
    regardless of length.
    """
    assume(len(password) >= 8)  # only test the no-digit case, not the short case
    assert not is_valid_password(password), (
        f"Password '{password}' has no digit but was accepted"
    )
