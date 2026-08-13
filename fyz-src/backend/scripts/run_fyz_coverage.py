"""Run FYZ tests and measure service-layer executable-line coverage.

This runner intentionally uses only the Python standard library.  Executable
lines come from CPython line tables (``dis.findlinestarts``), while executed
lines are collected with ``sys.settrace``.  The method is deterministic and
works in the offline competition environment where pytest-cov may be absent.
"""

from __future__ import annotations

import argparse
import dis
import json
import platform
import sys
import threading
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
SERVICE_DIR = (BACKEND_DIR / "app" / "services").resolve()
DEFAULT_OUTPUT = BACKEND_DIR / "evaluation" / "fyz_coverage.json"
DEFAULT_JUNIT = BACKEND_DIR / "evaluation" / "fyz_pytest_results.xml"
COVERAGE_THRESHOLD = 0.60


def _code_lines(code: types.CodeType) -> set[int]:
    lines = {line for _, line in dis.findlinestarts(code) if line > 0}
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            lines.update(_code_lines(constant))
    return lines


def executable_lines(path: Path) -> set[int]:
    source = path.read_text(encoding="utf-8")
    return _code_lines(compile(source, str(path), "exec"))


class ServiceLineTracer:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.covered: dict[Path, set[int]] = {}
        self._path_cache: dict[str, Path | None] = {}

    def _service_path(self, filename: str) -> Path | None:
        cached = self._path_cache.get(filename)
        if filename in self._path_cache:
            return cached
        try:
            path = Path(filename).resolve()
            path.relative_to(self.root)
        except (OSError, ValueError):
            path = None
        self._path_cache[filename] = path
        return path

    def global_trace(self, frame: types.FrameType, event: str, arg: Any):
        if event == "call" and self._service_path(frame.f_code.co_filename):
            return self.local_trace
        return None

    def local_trace(self, frame: types.FrameType, event: str, arg: Any):
        if event == "line":
            path = self._service_path(frame.f_code.co_filename)
            if path is not None:
                self.covered.setdefault(path, set()).add(frame.f_lineno)
        return self.local_trace


def build_report(tracer: ServiceLineTracer, *, pytest_exit_code: int) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    total_executable = 0
    total_covered = 0
    for path in sorted(SERVICE_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        executable = executable_lines(path)
        covered = executable & tracer.covered.get(path.resolve(), set())
        total_executable += len(executable)
        total_covered += len(covered)
        ratio = len(covered) / len(executable) if executable else 1.0
        files.append(
            {
                "file": path.relative_to(BACKEND_DIR).as_posix(),
                "executable_lines": len(executable),
                "covered_lines": len(covered),
                "coverage": round(ratio, 6),
            }
        )
    ratio = total_covered / total_executable if total_executable else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "FYZ app/services executable lines",
        "method": "CPython line-table executable lines + sys.settrace execution",
        "python": platform.python_version(),
        "threshold": COVERAGE_THRESHOLD,
        "executable_lines": total_executable,
        "covered_lines": total_covered,
        "coverage": round(ratio, 6),
        "coverage_gate_passed": ratio >= COVERAGE_THRESHOLD,
        "pytest_exit_code": pytest_exit_code,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--junit", type=Path, default=DEFAULT_JUNIT)
    parser.add_argument("pytest_args", nargs="*", default=["test"])
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.junit.parent.mkdir(parents=True, exist_ok=True)

    pytest_args = list(args.pytest_args or ["test"])
    pytest_args.extend(["-q", f"--junitxml={args.junit}"])
    tracer = ServiceLineTracer(SERVICE_DIR)
    sys.settrace(tracer.global_trace)
    threading.settrace(tracer.global_trace)
    try:
        pytest_exit_code = int(pytest.main(pytest_args))
    finally:
        sys.settrace(None)
        threading.settrace(None)

    report = build_report(tracer, pytest_exit_code=pytest_exit_code)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))
    return 0 if pytest_exit_code == 0 and report["coverage_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
