import ast
from pathlib import Path

import pytest

from ai_test_generator.analyzer import find_functions
from ai_test_generator.generator import generate_mock_test, generate_test


@pytest.fixture
def functions(tmp_path: Path):
    module_path = tmp_path / "billing.py"
    module_path.write_text(
        "def calculate_total(user_id, amount, is_enabled):\n"
        "    return amount if is_enabled else 0\n",
        encoding="utf-8",
    )
    return find_functions(module_path)


def test_generate_mock_test_is_valid_python_and_uses_name_hints(functions) -> None:
    fn = functions[0]

    code = generate_mock_test(fn, module_name="billing")

    # Must be syntactically valid so it can actually be written to a test file.
    ast.parse(code)
    assert "billing.calculate_total(1, 1.0, True)" in code
    assert "def test_calculate_total_smoke" in code


def test_generate_test_defaults_to_mock_without_api_key(functions, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fn = functions[0]

    code, mode = generate_test(fn, module_name="billing")

    assert mode == "mock"
    ast.parse(code)


def test_generate_test_force_mock_ignores_api_key(functions, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fn = functions[0]

    code, mode = generate_test(fn, module_name="billing", force_mock=True)

    assert mode == "mock"
    ast.parse(code)
