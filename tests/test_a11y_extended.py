import pytest
from forex.a11y_checker import calculate_contrast_ratio, check_wcag_compliance, hex_to_rgb, validate_html_semantics


class TestA11yExtended:
    def test_hex_to_rgb_short(self):
        assert hex_to_rgb("#FFF") == (255, 255, 255)
        assert hex_to_rgb("#000") == (0, 0, 0)

    def test_check_wcag_compliance_aaa(self):
        # AAA normal needs 7.0
        assert check_wcag_compliance(7.1, level="AAA", font_size="normal") is True
        assert check_wcag_compliance(6.9, level="AAA", font_size="normal") is False
        # AAA large needs 4.5
        assert check_wcag_compliance(4.6, level="AAA", font_size="large") is True
        assert check_wcag_compliance(4.4, level="AAA", font_size="large") is False

    def test_check_wcag_compliance_invalid_level(self):
        with pytest.raises(ValueError):
            check_wcag_compliance(4.5, level="INVALID")

    def test_validate_html_semantics_empty_links(self):
        html = '<a href="#"></a>'
        violations = validate_html_semantics(html)
        assert any("empty links" in v for v in violations)

    def test_calculate_contrast_ratio_error(self):
        # Invalid hex should trigger exception and return 0.0
        assert calculate_contrast_ratio("invalid", "#FFFFFF") == 0.0
