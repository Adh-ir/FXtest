#!/usr/bin/env python3
"""
Comprehensive Quality Check Script for Forex Rate Extractor

Runs:
1. Ruff (Linting & Formatting)
2. Mypy (Type Checking)
3. Bandit (Security Scanning)
4. Pytest (Testing & Coverage)

Usage:
    python run_quality_checks.py
"""

import json
import subprocess
import sys
from pathlib import Path

# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(title: str) -> None:
    print(f"\n{BLUE}{'=' * 60}")
    print(f"{title:^60}")
    print(f"{'=' * 60}{RESET}\n")


def run_command(
    command: list[str], description: str, continue_on_error: bool = False
) -> int:
    print(f"{YELLOW}Running {description}...{RESET}")
    try:
        result = subprocess.run(
            command,
            capture_output=False,  # Stream output directly
            text=True,
        )
        if result.returncode == 0:
            print(f"{GREEN}✓ {description} passed.{RESET}")
        else:
            print(f"{RED}✗ {description} failed.{RESET}")
        return result.returncode
    except FileNotFoundError:
        print(
            f"{RED}Error: Command not found: {command[0]}. Please install dev dependencies.{RESET}"
        )
        return 1


def run_tests_and_parse(project_root: Path) -> tuple[int, int, int]:
    """
    Runs pytest and parses the JSON report to get exact pass/fail counts.
    Returns: (exit_code, tests_passed, total_tests)
    """
    report_file = project_root / ".pytest_report.json"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--json-report",
        f"--json-report-file={report_file}",
    ]

    print(f"{YELLOW}Running Tests (pytest)...{RESET}")
    result = subprocess.run(cmd, capture_output=False)

    passed = 0
    total = 0

    if report_file.exists():
        try:
            with open(report_file) as f:
                data = json.load(f)
                summary = data.get("summary", {})
                passed = summary.get("passed", 0)
                # Total includes passed, failed, errors. Skipped/xfailed might be debatable,
                # but usually total tests attempted is valid.
                total = passed + summary.get("failed", 0) + summary.get("error", 0)

            # clean up
            report_file.unlink()
        except Exception as e:
            print(f"{RED}Failed to parse test report: {e}{RESET}")

    return result.returncode, passed, total


def main() -> None:
    project_root = Path(__file__).parent
    failures = []

    print_header("Forex Rate Extractor - Quality Assurance Gate")

    # 1. Linting & Formatting (Ruff)
    if (
        run_command(
            [sys.executable, "-m", "ruff", "check", "."], "Linting Check (Ruff)"
        )
        != 0
    ):
        failures.append("Linting")

    if (
        run_command(
            [sys.executable, "-m", "ruff", "format", "--check", "."],
            "Formatting Check (Ruff)",
        )
        != 0
    ):
        failures.append("Formatting")

    # 2. Type Checking (Mypy)
    if run_command([sys.executable, "-m", "mypy", "."], "Type Checking (Mypy)") != 0:
        failures.append("Type Checking")

    # 3. Security (Bandit)
    # -r for recursive, -c to point to config file if we had one, but defaults are ok.
    # LLM Note: Creating a bandit.yaml isn't strictly requested but good practice. using defaults for now.
    if (
        run_command(
            [sys.executable, "-m", "bandit", "-r", ".", "-q"], "Security Scan (Bandit)"
        )
        != 0
    ):
        failures.append("Security Scan")

    # 4. Tests (Pytest)
    test_exit_code, tests_passed, tests_total = run_tests_and_parse(project_root)
    if test_exit_code != 0:
        failures.append("Unit Tests")

    print_header("Quality Report Summary")

    # 5. Final Report string
    # "strictly formatted as: [FINAL REPORT] Quality Score: X/Y tests passed."
    print(f"[FINAL REPORT] Quality Score: {tests_passed}/{tests_total} tests passed.")

    if failures:
        print(f"\n{RED}The following checks failed:{RESET}")
        for fail in failures:
            print(f"- {fail}")
        sys.exit(1)

    if tests_total > 0 and tests_passed != tests_total:
        # Should be caught by test_exit_code, but strictly ensuring X/Y matching.
        print(f"{RED}Failure: Not all tests passed.{RESET}")
        sys.exit(1)

    if tests_total == 0:
        print(f"{YELLOW}Warning: No tests were run.{RESET}")

    print(f"\n{GREEN}All systems go! Ready for release candidate.{RESET}")
    sys.exit(0)


if __name__ == "__main__":
    main()
