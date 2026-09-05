"""
Unit tests for Dual-Mode Resolution and Handover Drafting Engine.
"""
from resolveiq.accounts import account_repo
from resolveiq.resolver import resolution_engine


def test_resolution_draft_mode():
    conv = account_repo.get_conversation("CONV-001")
    acc = account_repo.get_account(conv["account_id"])
    res = resolution_engine.resolve(conv, acc)
    assert res.mode == "RESOLUTION_DRAFT"
    assert len(res.citations) > 0
    assert res.validation.is_valid is True
    assert "Sarah" in res.draft_text


def test_handover_summary_mode_for_physical_line_fault():
    conv = account_repo.get_conversation("CONV-003")
    acc = account_repo.get_account(conv["account_id"])
    res = resolution_engine.resolve(conv, acc)
    assert res.mode == "HANDOVER_SUMMARY"
    assert res.handover_details is not None
    assert "Field Engineering Dispatch" in res.handover_details.get("target_team", "")
    assert res.validation.is_valid is True
    assert "KB-NET-001" in [c["article_id"] for c in res.citations]


def test_roaming_billing_resolution():
    conv = account_repo.get_conversation("CONV-002")
    acc = account_repo.get_account(conv["account_id"])
    res = resolution_engine.resolve(conv, acc)
    assert res.mode == "RESOLUTION_DRAFT"
    assert "$32.50" in res.draft_text or "$65.00" in res.draft_text
    assert res.validation.is_valid is True
