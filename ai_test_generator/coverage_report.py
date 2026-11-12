"""Run `coverage` against a module + test file pair and return the total
line-coverage percentage. Used to print a real before/after delta -- not an
estimate -- when the CLI's --report-coverage flag is set.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def measure_coverage(module_path: Path, test_path: Path) -> float:
    """Returns total statement coverage percentage for module_path, exercised
    by running pytest against test_path."""
    if not test_path.exists():
        return 0.0

    workdir = module_path.parent
    data_file = workdir / f".coverage.ai_test_generator.{test_path.stem}"

    run_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        f"--data-file={data_file}",
        f"--source={module_path.stem}",
        "-m",
        "pytest",
        str(test_path),
        "-q",
    ]
    subprocess.run(run_cmd, cwd=workdir, capture_output=True, text=True)

    report_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "report",
        f"--data-file={data_file}",
        "--format=total",
    ]
    result = subprocess.run(report_cmd, cwd=workdir, capture_output=True, text=True)
    data_file.unlink(missing_ok=True)

    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0
