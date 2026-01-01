#!/usr/bin/env python3
"""
Custom Test Runner for Forex Rate Extractor

Executes pytest with coverage and provides a custom summary output.
Final line format: [Summary] X/Y tests passed.
"""

import subprocess
import sys
import re
import json
from pathlib import Path


def run_tests():
    """
    Runs pytest with JSON output and coverage, then parses results.
    """
    project_root = Path(__file__).parent
    
    # Build pytest command
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        str(project_root / "tests"),
        "-v",
        "--tb=short",
        "--cov=logic",
        "--cov-report=term-missing",
        "--json-report",
        "--json-report-file=.pytest_report.json"
    ]
    
    print("=" * 60)
    print("🧪 Forex Rate Extractor - Test Suite")
    print("=" * 60)
    print()
    
    # Run pytest
    result = subprocess.run(
        pytest_cmd,
        cwd=project_root,
        capture_output=False  # Let output stream to terminal
    )
    
    print()
    print("=" * 60)
    
    # Parse results from JSON report
    report_path = project_root / ".pytest_report.json"
    
    if report_path.exists():
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)
            
            summary = report.get('summary', {})
            passed = summary.get('passed', 0)
            failed = summary.get('failed', 0)
            error = summary.get('error', 0)
            skipped = summary.get('skipped', 0)
            
            total = passed + failed + error
            
            # Clean up report file
            report_path.unlink()
            
        except (json.JSONDecodeError, KeyError):
            # Fallback: parse from return code
            passed = 0 if result.returncode != 0 else 1
            total = 1
            failed = 1 if result.returncode != 0 else 0
    else:
        # Fallback if JSON report not generated
        # Try to install pytest-json-report and re-run, or use return code
        passed = 0 if result.returncode != 0 else 1
        total = 1
        failed = 1 if result.returncode != 0 else 0
    
    # Print custom summary
    if failed > 0 or result.returncode != 0:
        print("❌ Some tests failed!")
    else:
        print("✅ All tests passed!")
    
    print()
    print(f"[Summary] {passed}/{total} tests passed.")
    
    # Return exit code
    return result.returncode


def main():
    """Main entry point."""
    # Check for pytest-json-report
    try:
        import pytest_jsonreport
    except ImportError:
        print("Note: Installing pytest-json-report for detailed reporting...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest-json-report", "-q"])
    
    exit_code = run_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
