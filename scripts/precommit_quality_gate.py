from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_PATHS = ["src"]


def run_step(*args: str) -> int:
    command = [sys.executable, "-m", *args]
    print(f"[pre-commit] running: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    return int(result.returncode)


def run_quality_checks() -> tuple[int, int, int, int]:
    src_only = CHECK_PATHS.copy()
    ruff_code = run_step("ruff", "check", *src_only)
    ruff_format_check_code = run_step("ruff", "format", "--check", *src_only)
    mypy_code = run_step("mypy", "--strict", *src_only)
    return ruff_code, ruff_format_check_code, mypy_code


def run_ruff_fix() -> int:
    return run_step("ruff", "check", "--fix", *CHECK_PATHS)


def run_ruff_format() -> int:
    return run_step("ruff", "format", *CHECK_PATHS)


def main() -> int:
    ruff_code, ruff_format_check_code, mypy_code = run_quality_checks()

    # Always format/fix when any check fails.
    if ruff_code != 0 or ruff_format_check_code != 0 or mypy_code != 0:
        print(
            "[pre-commit] check failed; applying ruff --fix + ruff format and re-running checks",
            flush=True,
        )
        ruff_fix_code = run_ruff_fix()
        if ruff_fix_code != 0:
            return ruff_fix_code

        ruff_format_code = run_ruff_format()
        if ruff_format_code != 0:
            return ruff_format_code

        ruff_code, ruff_format_check_code, mypy_code = run_quality_checks()

    return 0 if all(code == 0 for code in (ruff_code, ruff_format_check_code, mypy_code)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
