"""Identifiers are masked, including Indian ones; normal business text is left alone."""
import pytest

from kb.pii import redact


@pytest.mark.parametrize("text, entity", [
    ("Aadhaar 4731 8926 5400", "IN_AADHAAR"),
    ("PAN BQMPM4821K", "IN_PAN"),
    ("Mobile +91 98220 41567", "PHONE_NUMBER"),
    ("mail ramesh.gaikwad74@gmail.com today", "EMAIL_ADDRESS"),
    ("Salary account 50100234567812, HDFC Bank", "IN_BANK_ACCOUNT"),
    ("UPI kavita.j@oksbi", "IN_UPI"),
    ("card 4111 1111 1111 1111", "CREDIT_CARD"),
])
def test_identifier_is_masked(text, entity):
    masked, counts = redact(text)
    assert counts == {entity: 1}
    assert f"<{entity}>" in masked


def test_aadhaar_needs_a_valid_checksum():
    # same shape, wrong Verhoeff check digit: it's just a number
    assert redact("Ref 4731 8926 5401")[1] == {}


@pytest.mark.parametrize("text", [
    "Total order value Rs 52,68,800 before GST.",
    "VS-200 needs 415 V three phase, plus or minus 10 percent.",
    "Replace the seal kit (part VS2-SK-11) from lot ST-0926.",
    "Assigned to asha.kulkarni@vardhanpumps.in, due 28 October 2026.",
])
def test_business_text_is_untouched(text):
    assert redact(text) == (text, {})
