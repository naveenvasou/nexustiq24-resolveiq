"""
Unit tests for Fact Validation Engine (Distinctive Strength).
"""
from resolveiq.validator import fact_validator
from resolveiq.accounts import account_repo


def test_valid_draft_passes():
    acc = account_repo.get_account("ACC-1001")
    draft = (
        "Hello Sarah, I see your Fiber 500 service with NexusHub WiFi-6 router is offline "
        "following incident INC-88219. Your current balance is $0.00. Please power cycle your Nokia ONT."
    )
    res = fact_validator.validate(draft, acc)
    assert res.is_valid is True
    assert res.verdict == "VALIDATED"
    assert len(res.audit_trail) >= 3


def test_falsified_balance_rejected():
    acc = account_repo.get_account("ACC-1001")
    draft = "Hello Sarah, your Fiber 500 account has an unpaid overdue balance of $850.00."
    res = fact_validator.validate(draft, acc)
    assert res.is_valid is False
    assert res.verdict == "REJECTED"
    assert any("$850.00" in r for r in res.rejection_reasons)


def test_wrong_plan_rejected():
    acc = account_repo.get_account("ACC-1001")
    draft = "Hello Sarah, checking your Fiber 100 service."
    res = fact_validator.validate(draft, acc)
    assert res.is_valid is False
    assert res.verdict == "REJECTED"
    assert any("Fiber 100" in r for r in res.rejection_reasons)


def test_wrong_router_rejected():
    acc = account_repo.get_account("ACC-1001")
    draft = "Hello Sarah, please reboot your NexusHub Basic router for Fiber 500."
    res = fact_validator.validate(draft, acc)
    assert res.is_valid is False
    assert res.verdict == "REJECTED"
    assert any("NexusHub Basic" in r for r in res.rejection_reasons)
