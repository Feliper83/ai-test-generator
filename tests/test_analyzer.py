from pathlib import Path

from ai_test_generator.analyzer import (
    find_functions,
    find_tested_function_names,
    find_untested_functions,
)

MODULE_SOURCE = '''
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def _private_helper(x):
    return x


class Thing:
    def method_a(self):
        return 1

    def method_b(self):
        return 2
'''

TEST_SOURCE = '''
import mymodule


def test_add():
    assert mymodule.add(1, 2) == 3
'''


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_find_functions_skips_private_and_finds_methods(tmp_path: Path) -> None:
    module_path = _write(tmp_path / "mymodule.py", MODULE_SOURCE)

    functions = find_functions(module_path)
    names = {fn.name for fn in functions}

    assert names == {"add", "subtract", "method_a", "method_b"}
    assert all(not name.startswith("_") for name in names)

    method = next(fn for fn in functions if fn.name == "method_a")
    assert method.is_method is True
    assert method.class_name == "Thing"
    assert method.qualified_name == "Thing.method_a"


def test_find_tested_function_names_reads_calls(tmp_path: Path) -> None:
    test_path = _write(tmp_path / "test_mymodule.py", TEST_SOURCE)

    tested = find_tested_function_names(test_path)

    assert tested == {"add"}


def test_find_tested_function_names_missing_file_returns_empty(tmp_path: Path) -> None:
    assert find_tested_function_names(tmp_path / "does_not_exist.py") == set()


def test_find_untested_functions(tmp_path: Path) -> None:
    module_path = _write(tmp_path / "mymodule.py", MODULE_SOURCE)
    test_path = _write(tmp_path / "test_mymodule.py", TEST_SOURCE)

    untested = {fn.name for fn in find_untested_functions(module_path, test_path)}

    assert untested == {"subtract", "method_a", "method_b"}
