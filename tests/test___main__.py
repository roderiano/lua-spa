from __future__ import annotations

import runpy
import sys


def test_module_entrypoint_runs_help() -> None:
    # Given: sys.argv simulates a bare CLI invocation (no subcommand)
    original_argv = sys.argv[:]
    try:
        sys.argv = ["moon-spa"]

        # When: the moon_spa.__main__ module is executed
        runpy.run_module("moon_spa.__main__", run_name="__main__")

    finally:
        # Then: no exception is raised and argv is restored
        sys.argv = original_argv
