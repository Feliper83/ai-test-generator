# ai-test-generator

A CLI that finds functions in a Python module that no existing test calls, and generates pytest tests for them —
using Claude when an API key is available, and a deterministic template fallback when it isn't.

## Why this exists

Built around a recurring piece of legacy-modernization work: a module accumulates functions over years, test
coverage lags behind, and nobody has time to backfill tests one by one before a refactor. This tool automates the
first pass — find the gaps, generate a starting test for each — under an explicit guardrail: generated tests are a
**scaffold for human review**, not a substitute for it. Every mock-mode test is a smoke test with a `TODO` marking
where a human needs to supply the real expected behavior; every live-mode test is Claude's best attempt at real
assertions from reading the function body, still meant to be read before it's trusted.

This mirrors how AI-assisted test generation should be used in a real engineering org: accelerate the repetitive
part, keep a review gate on the part that encodes actual business intent.

## How it decides what's "untested"

`ai_test_generator/analyzer.py` parses the target module's AST to list its functions, then parses the existing test
file's AST to collect every function name that appears as a `Call`. Anything not called by name in the test file is
considered untested. This is a static heuristic (fast, no execution required) — the **real** coverage delta is
measured separately and precisely via `coverage` when you pass `--report-coverage`.

## Install

```bash
pip install -e .          # mock mode only
pip install -e ".[ai]"    # adds the `anthropic` client for live mode
```

## Usage

```bash
cd examples
ai-test-generator generate \
  --module sample_module.py \
  --tests test_sample_module.py \
  --report-coverage
```

`sample_module.py` ships with 6 functions; `test_sample_module.py` only exercises 2 of them. Running the command
above finds the other 4 (`calculate_prorated_price`, `merge_configs`, `retry_count_exceeded`,
`PricingCalculator.apply_discount`), generates a test for each, writes them to
`test_sample_module_generated.py`, and — with `--report-coverage` — prints the actual before/after coverage
percentage measured by running `coverage` against the original tests vs. the original + generated tests combined.

### Mock mode (default, no API key)

Infers plausible argument values from parameter names (`user_id` → `1`, `is_enabled` → `True`, `name` → `"test"`,
...) and emits a smoke test: call the function, assert it doesn't raise, leave a `TODO` for the real assertion.
Zero cost, zero network, always available — a safety net so the tool is usable even without LLM access.

### Live mode (`ANTHROPIC_API_KEY` set)

Sends the function's source to Claude and asks for a real pytest test covering the normal case plus at least one
edge case. Force mock mode even with a key present using `--mock` (useful in CI, or to compare both outputs).

## Project layout

```
ai_test_generator/
  analyzer.py          AST-based untested-function detection
  generator.py          mock template + Claude-backed test generation
  coverage_report.py    runs `coverage` before/after, returns real percentages
  cli.py                argparse entrypoint
examples/
  sample_module.py            demo target with partial coverage
  test_sample_module.py       the 2 existing tests
tests/
  test_analyzer.py      unit tests for the AST analysis
  test_generator.py     unit tests for mock generation + mode selection
```

## Run the tool's own tests

```bash
pip install -e .
pytest
```

## License

MIT
