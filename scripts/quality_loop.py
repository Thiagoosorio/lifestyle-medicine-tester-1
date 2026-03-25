"""Run a repeatable quality loop and write a markdown report.

This script is designed for local use and scheduled CI runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "quality_loop"
REPORT_PATH = REPORT_DIR / "latest.md"


@dataclass
class CheckResult:
    name: str
    command: list[str]
    returncode: int
    duration_s: float
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def run_check(name: str, command: list[str]) -> CheckResult:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    duration = time.perf_counter() - started
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return CheckResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        duration_s=duration,
        output=output.strip(),
    )


def write_report(results: list[CheckResult]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    overall_ok = all(r.passed for r in results)
    status = "PASS" if overall_ok else "FAIL"

    lines = [
        "# Quality Loop Report",
        "",
        f"- Timestamp (UTC): `{ts}`",
        f"- Overall status: **{status}**",
        "",
        "## Checks",
        "",
    ]

    for result in results:
        icon = "PASS" if result.passed else "FAIL"
        cmd = " ".join(result.command)
        lines.append(f"### {icon} - {result.name}")
        lines.append(f"- Command: `{cmd}`")
        lines.append(f"- Exit code: `{result.returncode}`")
        lines.append(f"- Duration: `{result.duration_s:.2f}s`")
        lines.append("")
        if result.output:
            lines.append("```text")
            lines.append(result.output)
            lines.append("```")
            lines.append("")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    checks = [
        ("Unit tests", [sys.executable, "-m", "pytest", "-q", "--tb=short"]),
        ("Syntax compile", [sys.executable, "-m", "compileall", "pages", "services", "models"]),
    ]
    results = [run_check(name, command) for name, command in checks]
    write_report(results)

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} ({result.duration_s:.2f}s)")
        if result.output:
            print(result.output)
            print()

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
