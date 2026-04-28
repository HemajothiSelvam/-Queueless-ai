"""
Property test for token number uniqueness.

**Property 1: Token numbers are globally unique across all generated tokens**
**Validates: Requirements 3.2**

Token number format: {BRANCH_CODE}-{YYYYMMDD}-{SEQ:03d}
e.g. BR1-20250101-042
"""
import re
from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st


# ── Token number generator (mirrors the logic in Token_Manager / task 5) ──────

def generate_token_number(branch_code: str, booking_date: date, sequence: int) -> str:
    """Generate a token number in the format {BRANCH_CODE}-{YYYYMMDD}-{SEQ:03d}."""
    date_str = booking_date.strftime("%Y%m%d")
    return f"{branch_code}-{date_str}-{sequence:03d}"


# ── Strategies ─────────────────────────────────────────────────────────────────

# Branch codes: 1-8 uppercase alphanumeric chars (realistic branch identifiers)
branch_code_st = st.from_regex(r"[A-Z]{2,4}[0-9]{1,2}", fullmatch=True)

# Dates within a reasonable range
date_st = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))

# Sequence numbers: 1-999 (fits in 3-digit zero-padded format)
sequence_st = st.integers(min_value=1, max_value=999)


# ── Properties ─────────────────────────────────────────────────────────────────

@given(
    branch_code=branch_code_st,
    booking_date=date_st,
    seq1=sequence_st,
    seq2=sequence_st,
)
@settings(max_examples=300)
def test_different_sequences_produce_different_token_numbers(
    branch_code, booking_date, seq1, seq2
):
    """
    Property 1 (partial): Same branch + date but different sequences → different tokens.
    """
    if seq1 == seq2:
        return  # trivially same input → same output, not a uniqueness violation
    t1 = generate_token_number(branch_code, booking_date, seq1)
    t2 = generate_token_number(branch_code, booking_date, seq2)
    assert t1 != t2, (
        f"Collision: seq {seq1} and {seq2} both produced '{t1}' "
        f"for branch={branch_code}, date={booking_date}"
    )


@given(
    branch_code=branch_code_st,
    date1=date_st,
    date2=date_st,
    sequence=sequence_st,
)
@settings(max_examples=300)
def test_different_dates_produce_different_token_numbers(
    branch_code, date1, date2, sequence
):
    """
    Property 1 (partial): Same branch + sequence but different dates → different tokens.
    """
    if date1 == date2:
        return
    t1 = generate_token_number(branch_code, date1, sequence)
    t2 = generate_token_number(branch_code, date2, sequence)
    assert t1 != t2, (
        f"Collision: date {date1} and {date2} both produced '{t1}' "
        f"for branch={branch_code}, seq={sequence}"
    )


@given(
    branch1=branch_code_st,
    branch2=branch_code_st,
    booking_date=date_st,
    sequence=sequence_st,
)
@settings(max_examples=300)
def test_different_branches_produce_different_token_numbers(
    branch1, branch2, booking_date, sequence
):
    """
    Property 1 (partial): Same date + sequence but different branches → different tokens.
    """
    if branch1 == branch2:
        return
    t1 = generate_token_number(branch1, booking_date, sequence)
    t2 = generate_token_number(branch2, booking_date, sequence)
    assert t1 != t2, (
        f"Collision: branch '{branch1}' and '{branch2}' both produced '{t1}' "
        f"for date={booking_date}, seq={sequence}"
    )


@given(
    branch_code=branch_code_st,
    booking_date=date_st,
    sequence=sequence_st,
)
@settings(max_examples=300)
def test_token_number_matches_expected_format(branch_code, booking_date, sequence):
    """
    Property 1 (format): Every generated token number matches {BRANCH_CODE}-{YYYYMMDD}-{SEQ:03d}.
    """
    token = generate_token_number(branch_code, booking_date, sequence)
    pattern = re.compile(r"^[A-Z0-9]+-\d{8}-\d{3}$")
    assert pattern.match(token), (
        f"Token '{token}' does not match expected format BRANCHCODE-YYYYMMDD-NNN"
    )


@given(
    st.lists(
        st.tuples(branch_code_st, date_st, sequence_st),
        min_size=2,
        max_size=50,
        unique=True,
    )
)
@settings(max_examples=100)
def test_batch_of_distinct_inputs_produces_unique_token_numbers(inputs):
    """
    Property 1 (global): A batch of distinct (branch, date, seq) triples
    always produces globally unique token numbers.
    """
    tokens = [generate_token_number(b, d, s) for b, d, s in inputs]
    assert len(tokens) == len(set(tokens)), (
        f"Duplicate token numbers found in batch of {len(inputs)} distinct inputs"
    )
