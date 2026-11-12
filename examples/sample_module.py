"""A small telecom-provisioning-flavored module used to demo the tool.

Two of its functions already have tests (see test_sample_module.py); the
rest are "legacy" code that ai-test-generator will generate tests for.
"""

from __future__ import annotations


def normalize_msisdn(number: str) -> str:
    """Strip separators and ensure a leading country code."""
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits.startswith("57"):
        digits = "57" + digits
    return digits


def is_valid_plan(plan_code: str) -> bool:
    return plan_code in {"BASIC", "PLUS", "PREMIUM"}


def calculate_prorated_price(monthly_price: float, days_used: int, days_in_month: int) -> float:
    if days_in_month <= 0:
        raise ValueError("days_in_month must be positive")
    return round(monthly_price * days_used / days_in_month, 2)


def merge_configs(base: dict, override: dict) -> dict:
    merged = dict(base)
    merged.update(override)
    return merged


def retry_count_exceeded(attempts: int, max_attempts: int) -> bool:
    return attempts >= max_attempts


class PricingCalculator:
    def __init__(self, base_rate: float = 1.0) -> None:
        self.base_rate = base_rate

    def apply_discount(self, amount: float, discount_percent: float) -> float:
        return round(amount * (1 - discount_percent / 100) * self.base_rate, 2)
