"""Skip artifact-integrity tests when their git-ignored local artifacts are absent.

Several tests verify that frozen experiment artifacts were not mutated. Those
artifacts live under paths that ``.gitignore`` keeps out of version control
(run archives, generated outputs, licensed external corpora), so a clean
checkout cannot contain them. Missing artifacts there mean "not available
here", not "regressed"; any other missing file still fails the test.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ONLY = (
    ROOT / "experiments" / "archive",
    ROOT / "experiments" / "outputs",
    ROOT / "data" / "benchmarks" / "external",
)


def _is_local_only(filename: object) -> bool:
    if not filename:
        return False
    path = Path(str(filename)).resolve()
    return any(path.is_relative_to(base) for base in LOCAL_ONLY)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    try:
        return (yield)
    except FileNotFoundError as error:
        missing = error.filename or (error.args[0] if error.args else None)
        if _is_local_only(missing):
            pytest.skip(f"local-only artifact not present in this checkout: {Path(str(missing)).relative_to(ROOT)}")
        raise
