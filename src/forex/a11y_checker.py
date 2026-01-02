"""
Accessibility (a11y) Checker Module

This module provides utility functions to programmatically check for common
accessibility issues, specifically focusing on WCAG 2.1 standards for
color contrast and basic semantic HTML structure.
"""

import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex color code to an RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_relative_luminance(rgb: tuple[int, int, int]) -> float:
    """
    Calculates the relative luminance of a color.
    Formula from WCAG 2.0: https://www.w3.org/TR/WCAG20/#relativeluminancedef
    """
    rs, gs, bs = [c / 255.0 for c in rgb]

    components = []
    for c in [rs, gs, bs]:
        if c <= 0.03928:
            components.append(c / 12.92)
        else:
            components.append(((c + 0.055) / 1.055) ** 2.4)

    r, g, b = components
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(color1_hex: str, color2_hex: str) -> float:
    """
    Calculates the contrast ratio between two hex colors.
    Returns value between 1.0 and 21.0.
    """
    try:
        rgb1 = hex_to_rgb(color1_hex)
        rgb2 = hex_to_rgb(color2_hex)

        l1 = get_relative_luminance(rgb1)
        l2 = get_relative_luminance(rgb2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)
    except Exception as e:
        logger.error(f"Error calculating contrast for {color1_hex} and {color2_hex}: {e}")
        return 0.0


def check_wcag_compliance(contrast_ratio: float, level: str = "AA", font_size: str = "normal") -> bool:
    """
    Checks if a contrast ratio meets WCAG requirements.

    Args:
        contrast_ratio: The calculated contrast ratio.
        level: "AA" or "AAA".
        font_size: "normal" or "large" (large is defined as 14pt bold or 18pt regular).
    """
    if level == "AA":
        required = 3.0 if font_size == "large" else 4.5
    elif level == "AAA":
        required = 4.5 if font_size == "large" else 7.0
    else:
        raise ValueError("Level must be 'AA' or 'AAA'")

    return contrast_ratio >= required


def parse_css_variables(css_content: str) -> dict[str, str]:
    """
    Extracts CSS variables from the :root block of a CSS file content.
    """
    variables = {}
    # Find the :root block
    root_match = re.search(r":root\s*{([^}]*)}", css_content, re.DOTALL)
    if root_match:
        root_content = root_match.group(1)
        # Extract variables
        # Matches --variable-name: #hexcode; or --variable-name: rgba(...);
        # For simplicity, currently focusing on Hex and simple RGB/RGBA

        # Regex for hex colors
        hex_matches = re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{3,6})", root_content)
        for name, value in hex_matches:
            variables[name.strip()] = value.strip()

        # TODO: Add parsing for rgb/rgba if needed later

    return variables


def validate_html_semantics(html_content: str) -> list[str]:
    """
    Performs basic semantic checks on HTML strings.
    """
    violations = []

    # Check 1: Image alt attributes
    img_tags = re.findall(r"<img[^>]+>", html_content)
    for img in img_tags:
        if "alt=" not in img:
            violations.append(f"Image missing alt attribute: {img[:50]}...")

    # Check 2: Empty links
    empty_links = re.findall(r"<a[^>]*>\s*</a>", html_content)
    if empty_links:
        violations.append(f"Found {len(empty_links)} empty links.")

    # Check 3: Heading hierarchy skipped (e.g., h1 then h3)
    # This is hard to check on a snippet, skipping for now

    return violations
