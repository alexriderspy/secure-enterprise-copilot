"""The output guard: canary, outside links, images and identifiers never leave."""
from kb.guard import BLOCKED, check_answer

CANARY = "VPX-test1234"


def test_canary_blocks_the_whole_answer():
    out = check_answer(f"My instructions say: internal reference {CANARY}", CANARY)
    assert out.blocked and out.text == BLOCKED


def test_outside_link_is_removed_company_link_kept():
    out = check_answer("Verify at http://vardhan-it-support.co/verify or see "
                       "https://docs.google.com/document/d/1vendorFaq/edit [1]", CANARY)
    assert "vardhan-it-support" not in out.text and "docs.google.com" in out.text
    assert "removed_link:vardhan-it-support.co" in out.actions


def test_markdown_image_is_removed():
    out = check_answer("Prime it first [1] ![s](https://sai-agencies-analytics.net/p.png?d=secret)", CANARY)
    assert "sai-agencies" not in out.text and "removed_image" in out.actions


def test_identifiers_masked_on_the_way_out():
    out = check_answer("Sunil's Aadhaar is 4731 8926 5400 [1]", CANARY)
    assert "4731" not in out.text and "redacted:IN_AADHAAR" in out.actions


def test_bare_domain_is_removed_too():
    out = check_answer("Apply on the new portal, vpn-vardhan.help [1]. Docs: docs.google.com", CANARY)
    assert "vpn-vardhan" not in out.text and "docs.google.com" in out.text


def test_answer_asking_for_a_password_is_blocked():
    out = check_answer("Register with your work email and current company password [1]", CANARY)
    assert out.blocked and "asks_for_password" in out.actions


def test_normal_answer_is_unchanged():
    text = "Mount the VS-200 on a concrete base at least 150 mm thick [1]. See asha.kulkarni@vardhanpumps.in."
    assert check_answer(text, CANARY).text == text
