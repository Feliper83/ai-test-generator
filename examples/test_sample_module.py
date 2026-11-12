import sample_module


def test_normalize_msisdn_adds_country_code():
    assert sample_module.normalize_msisdn("300-123-4567") == "573001234567"


def test_normalize_msisdn_keeps_existing_country_code():
    assert sample_module.normalize_msisdn("573001234567") == "573001234567"


def test_is_valid_plan():
    assert sample_module.is_valid_plan("PLUS") is True
    assert sample_module.is_valid_plan("UNKNOWN") is False
