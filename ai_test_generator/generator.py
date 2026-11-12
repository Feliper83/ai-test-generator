"""Generate pytest test code for a single function.

Two modes:
- mock: a deterministic, dependency-free template. Infers plausible argument
  values from parameter names (e.g. `user_id` -> 1, `name` -> "test") and
  emits a smoke test that calls the function and asserts it doesn't raise.
  Always available, used when ANTHROPIC_API_KEY isn't set or --mock is passed.
- live: calls the Anthropic API with the function's source and asks for a
  real pytest test covering normal and edge cases. Requires the `anthropic`
  extra and ANTHROPIC_API_KEY.

Either way, generated tests are a starting point, not a replacement for
review -- see the README's "operational guardrails" note.
"""

from __future__ import annotations

import os
import re

from .analyzer import FunctionInfo

DEFAULT_MODEL = "claude-sonnet-5"

_NAME_HINTS: list[tuple[re.Pattern[str], object]] = [
    (re.compile(r"(^|_)id$"), 1),
    (re.compile(r"^is_|^has_|flag|enabled"), True),
    (re.compile(r"attempt|retr|max_|count|num|qty|quantity|size|length|day|month|week|year"), 2),
    (re.compile(r"name|title|label|text|str"), "test"),
    (re.compile(r"path|file"), "test.txt"),
    (re.compile(r"items|list|values|records"), []),
    (re.compile(r"data|payload|config|options|settings|^base$|override"), {}),
    (re.compile(r"rate|ratio|percent|score|amount|price"), 1.0),
]

# Used only when no name pattern matches -- chosen to be the least likely to
# blow up on common arithmetic/comparison operators inside the function body.
# It will still be wrong for unrecognized dict/str/list parameters; that's an
# inherent limit of guessing from names alone, which is exactly why generated
# tests are meant to be reviewed, not trusted blindly (see README).
_FALLBACK_VALUE = 1


def _guess_value(arg_name: str) -> object:
    for pattern, value in _NAME_HINTS:
        if pattern.search(arg_name.lower()):
            return value
    return _FALLBACK_VALUE


def generate_mock_test(fn: FunctionInfo, module_name: str) -> str:
    call_args = ", ".join(repr(_guess_value(a)) for a in fn.args)
    target = f"{module_name}.{fn.qualified_name}" if not fn.is_method else None

    if fn.is_method:
        call_expr = (
            f"instance = {module_name}.{fn.class_name}()\n"
            f"    result = instance.{fn.name}({call_args})"
        )
    else:
        call_expr = f"result = {module_name}.{fn.name}({call_args})"

    return (
        f"def test_{fn.qualified_name.lower().replace('.', '_')}_smoke():\n"
        f'    """Auto-generated smoke test (mock mode) for {fn.qualified_name}.\n'
        f"    TODO: replace the placeholder arguments and assertion below with\n"
        f"    values and expectations specific to this function's contract.\n"
        f'    """\n'
        f"    {call_expr}\n"
        f"    assert result is not None  # TODO: assert the real expected value\n"
    )


def generate_live_test(fn: FunctionInfo, module_name: str, model: str = DEFAULT_MODEL) -> str:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only without the extra installed
        raise RuntimeError(
            "Live mode requires the 'anthropic' package. Install with: pip install ai-test-generator[ai]"
        ) from exc

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = (
        "Write pytest test function(s) for the Python function below. "
        f"It lives in a module importable as `{module_name}`. "
        "Cover the normal case and at least one edge case. "
        "Return ONLY the test code (no markdown fences, no explanation, no imports "
        f"beyond what's needed) assuming `import {module_name}` is already available.\n\n"
        f"```python\n{fn.source}\n```"
    )

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in message.content if block.type == "text")
    return _strip_code_fences(text).strip() + "\n"


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def generate_test(
    fn: FunctionInfo, module_name: str, *, force_mock: bool = False, model: str = DEFAULT_MODEL
) -> tuple[str, str]:
    """Returns (source, mode) where mode is 'live' or 'mock'."""
    if not force_mock and os.environ.get("ANTHROPIC_API_KEY"):
        return generate_live_test(fn, module_name, model=model), "live"
    return generate_mock_test(fn, module_name), "mock"
