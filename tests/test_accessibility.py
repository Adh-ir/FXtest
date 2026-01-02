"""
Accessibility Compliance Tests

This module tests the application's compliance with WCAG 2.1 standards,
focusing on Color Contrast and basic HTML Semantics.
"""

import os

import pytest

from forex.a11y_checker import (
    calculate_contrast_ratio,
    parse_css_variables,
    validate_html_semantics,
)

# Path to styles.css
STYLES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src",
    "forex",
    "ui",
    "styles.css",
)


@pytest.fixture
def css_variables():
    """Reads styles.css and parses CSS variables."""
    if not os.path.exists(STYLES_PATH):
        pytest.skip(f"styles.css not found at {STYLES_PATH}")

    with open(STYLES_PATH) as f:
        content = f.read()

    return parse_css_variables(content)


def test_css_variable_extraction(css_variables):
    """Test that we can successfully extract key variables."""
    assert "--app-bg" in css_variables
    assert "--text-color" in css_variables
    assert "--color-primary" in css_variables


@pytest.mark.parametrize(
    "bg_var, text_var, min_ratio",
    [
        ("--app-bg", "--text-color", 4.5),  # Main text on background
        ("--app-bg", "--heading-color", 4.5),  # Headings on background
        (
            "--color-secondary",
            "#FFFFFF",
            4.5,
        ),  # White text on secondary buttons (assuming white)
        ("--color-dark", "#FFFFFF", 4.5),  # White text on dark buttons
        # ('--color-primary', '--heading-color', 4.5), # Primary button text
    ],
)
def test_color_contrast_compliance(css_variables, bg_var, text_var, min_ratio):
    """
    Test contrast ratios for common UI elements.
    Using WCAG AA standard (4.5 for normal text).
    """
    # Resolve variables to hex
    bg_hex = css_variables.get(bg_var, bg_var)
    text_hex = css_variables.get(text_var, text_var)

    # Skip if we couldn't resolve (e.g., if it was rgba and parser skipped it)
    if not bg_hex.startswith("#") or not text_hex.startswith("#"):
        pytest.skip(f"Could not resolve colors: {bg_var}={bg_hex}, {text_var}={text_hex}")

    ratio = calculate_contrast_ratio(bg_hex, text_hex)

    # We allow a small tolerance or just strictly assert
    # Using specific error message to help debug fix
    assert ratio >= min_ratio, (
        f"Contrast fail: {bg_var}({bg_hex}) vs {text_var}({text_hex}) = {ratio:.2f}:1 (Required {min_ratio}:1)"
    )


def test_html_semantics_checker_forex():
    """Test the semantic validator directly."""
    bad_html = '<div><img src="foo.jpg"></div>'  # Missing alt
    violations = validate_html_semantics(bad_html)
    assert len(violations) > 0
    assert "Image missing alt attribute" in violations[0]

    good_html = '<div><img src="foo.jpg" alt="Description"></div>'
    violations = validate_html_semantics(good_html)
    assert len(violations) == 0


def test_button_contrast_primary(css_variables):
    """Specific check for Primary Button (likely black/dark text on green)."""
    # Primary color is --color-primary (#5ddf79)
    # Text is usually --heading-color (#132403) based on styles.css analysis
    bg_hex = css_variables.get("--color-primary", "#5ddf79")
    text_hex = css_variables.get("--heading-color", "#132403")

    ratio = calculate_contrast_ratio(bg_hex, text_hex)
    assert ratio >= 4.5, f"Primary Button Contrast fail: {ratio:.2f}:1"
