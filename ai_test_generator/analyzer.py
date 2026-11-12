"""AST-based analysis: find function definitions in a module and figure out
which of them are referenced (called) anywhere in an existing test file.

This is a static heuristic, not real coverage measurement -- it answers
"does any test even mention this function's name" before we spend an LLM
call (or the user's time) generating a test for it. Actual coverage deltas
are measured separately in coverage_report.py by running `coverage` for real.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    lineno: int
    end_lineno: int
    args: list[str]
    source: str
    is_method: bool = False
    class_name: str | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.class_name}.{self.name}" if self.class_name else self.name


def _extract_source(source_lines: list[str], node: ast.FunctionDef) -> str:
    start = node.lineno - 1
    end = node.end_lineno or node.lineno
    return "\n".join(source_lines[start:end])


def find_functions(module_path: Path) -> list[FunctionInfo]:
    """Return every top-level and class-method function defined in module_path."""
    text = module_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text, filename=str(module_path))

    functions: list[FunctionInfo] = []

    def visit(node: ast.AST, class_name: str | None = None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("_"):
                    continue
                args = [a.arg for a in child.args.args if a.arg != "self"]
                functions.append(
                    FunctionInfo(
                        name=child.name,
                        lineno=child.lineno,
                        end_lineno=child.end_lineno or child.lineno,
                        args=args,
                        source=_extract_source(lines, child),
                        is_method=class_name is not None,
                        class_name=class_name,
                    )
                )
            elif isinstance(child, ast.ClassDef):
                visit(child, class_name=child.name)

    visit(tree)
    return functions


def find_tested_function_names(test_path: Path) -> set[str]:
    """Return the set of function names that appear as a Call anywhere in test_path."""
    if not test_path.exists():
        return set()

    tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
    called_names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            called_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            called_names.add(func.attr)

    return called_names


def find_untested_functions(module_path: Path, test_path: Path) -> list[FunctionInfo]:
    tested = find_tested_function_names(test_path)
    return [fn for fn in find_functions(module_path) if fn.name not in tested]
