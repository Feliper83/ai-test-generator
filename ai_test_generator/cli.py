"""Command-line entrypoint.

    ai-test-generator generate --module path/to/module.py --tests path/to/test_module.py

Finds functions in --module that no test in --tests calls, generates a test
for each (Claude if ANTHROPIC_API_KEY is set, a deterministic template
otherwise), writes them to --out, and optionally reports the real
before/after coverage delta measured by `coverage`.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .analyzer import find_untested_functions
from .coverage_report import measure_coverage
from .generator import DEFAULT_MODEL, generate_test


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-test-generator")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate tests for untested functions")
    gen.add_argument("--module", required=True, type=Path, help="Path to the source module")
    gen.add_argument("--tests", required=True, type=Path, help="Path to the existing test file")
    gen.add_argument("--out", type=Path, default=None, help="Where to write generated tests (default: <tests_dir>/test_<module>_generated.py)")
    gen.add_argument("--mock", action="store_true", help="Force template-based generation, skip Claude even if ANTHROPIC_API_KEY is set")
    gen.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use in live mode (default: {DEFAULT_MODEL})")
    gen.add_argument("--report-coverage", action="store_true", help="Run `coverage` before/after and print the real delta")

    return parser


def _default_out_path(module_path: Path, tests_path: Path) -> Path:
    return tests_path.parent / f"test_{module_path.stem}_generated.py"


def cmd_generate(args: argparse.Namespace) -> int:
    module_path: Path = args.module.resolve()
    tests_path: Path = args.tests.resolve()
    out_path: Path = (args.out or _default_out_path(module_path, tests_path)).resolve()
    module_name = module_path.stem

    untested = find_untested_functions(module_path, tests_path)
    if not untested:
        print(f"All functions in {module_path.name} are already referenced in {tests_path.name}.")
        return 0

    print(f"Found {len(untested)} untested function(s) in {module_path.name}: "
          f"{', '.join(fn.qualified_name for fn in untested)}")

    blocks: list[str] = []
    for fn in untested:
        code, mode = generate_test(fn, module_name, force_mock=args.mock, model=args.model)
        print(f"  - {fn.qualified_name}: generated via {mode} mode")
        blocks.append(code)

    header = f"import pytest\nimport {module_name}\n\n\n"
    body = "\n\n".join(blocks)
    out_path.write_text(header + body + "\n", encoding="utf-8")
    print(f"\nWrote generated tests to {out_path}")

    if args.report_coverage:
        before = measure_coverage(module_path, tests_path)
        merged_source = tests_path.read_text(encoding="utf-8") + "\n\n" + header + body + "\n"
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", dir=tests_path.parent, prefix="test_merged_", delete=False
        ) as tmp:
            tmp.write(merged_source)
            merged_path = Path(tmp.name)
        try:
            after = measure_coverage(module_path, merged_path)
        finally:
            merged_path.unlink(missing_ok=True)

        print(f"\nCoverage for {module_path.name}: {before:.0f}% -> {after:.0f}% "
              f"({after - before:+.0f} pts)")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return cmd_generate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
