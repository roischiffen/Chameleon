"""
Unit tests for the Answer Comparator Module

Run with: python -m pytest tests/test_answer_comparator.py -v
Or: python -m pytest tests/test_answer_comparator.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.modules.answer_comparator import (
    normalize_answer,
    parse_as_number,
    compare_answers
)


class TestNormalizeAnswer:
    """Tests for normalize_answer function."""
    
    def test_strip_whitespace(self):
        assert normalize_answer("  150  ") == "150"
        assert normalize_answer("\t150\n") == "150"
    
    def test_lowercase(self):
        assert normalize_answer("ABC") == "abc"
        assert normalize_answer("Pi") == "pi"
    
    def test_remove_latex_dollar(self):
        assert normalize_answer("$150$") == "150"
        assert normalize_answer("$x = 5$") == "x = 5"
    
    def test_remove_latex_parens(self):
        assert normalize_answer("\\(150\\)") == "150"
    
    def test_remove_latex_brackets(self):
        assert normalize_answer("\\[150\\]") == "150"
    
    def test_remove_thousands_separator(self):
        assert normalize_answer("1,000") == "1000"
        assert normalize_answer("1,000,000") == "1000000"
    
    def test_normalize_whitespace(self):
        assert normalize_answer("a   b   c") == "a b c"
    
    def test_none_input(self):
        assert normalize_answer(None) == ""
    
    def test_empty_input(self):
        assert normalize_answer("") == ""
        assert normalize_answer("   ") == ""


class TestParseAsNumber:
    """Tests for parse_as_number function."""
    
    def test_integer(self):
        assert parse_as_number("150") == 150.0
        assert parse_as_number("-42") == -42.0
    
    def test_decimal(self):
        assert parse_as_number("0.5") == 0.5
        assert parse_as_number(".5") == 0.5
        assert parse_as_number("0.50") == 0.5
    
    def test_fraction(self):
        assert parse_as_number("1/2") == 0.5
        assert parse_as_number("3/4") == 0.75
        assert parse_as_number("-1/2") == -0.5
    
    def test_percentage(self):
        assert parse_as_number("50%") == 0.5
        assert parse_as_number("50 percent") == 0.5
        assert parse_as_number("100%") == 1.0
    
    def test_scientific_notation(self):
        assert parse_as_number("1e5") == 100000.0
        assert parse_as_number("1E5") == 100000.0
        assert parse_as_number("2e3") == 2000.0
        assert parse_as_number("1E-2") == 0.01
    
    def test_non_numeric(self):
        assert parse_as_number("abc") is None
        assert parse_as_number("") is None
        assert parse_as_number("hello world") is None


class TestCompareAnswers:
    """Tests for compare_answers function."""
    
    def test_exact_match(self):
        assert compare_answers("150", "150") == (True, "exact")
        assert compare_answers("abc", "abc") == (True, "exact")
    
    def test_exact_after_normalization(self):
        assert compare_answers(" 150 ", "150") == (True, "exact")
        assert compare_answers("$150$", "150") == (True, "exact")
        assert compare_answers("1000", "1,000") == (True, "exact")
    
    def test_numeric_equivalence(self):
        assert compare_answers("0.5", "1/2") == (True, "numeric")
        assert compare_answers("0.50", "0.5") == (True, "numeric")
        assert compare_answers("50%", "0.5") == (True, "numeric")
        assert compare_answers("1e5", "100000") == (True, "numeric")
    
    def test_no_match(self):
        assert compare_answers("150", "151") == (False, "no_match")
        assert compare_answers("abc", "150") == (False, "no_match")
        assert compare_answers("", "150") == (False, "no_match")


def run_tests():
    """Run all tests and report results."""
    test_classes = [TestNormalizeAnswer, TestCompareAnswers, TestParseAsNumber]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n=== {test_class.__name__} ===")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✅ {method_name}")
                    total_passed += 1
                except AssertionError as e:
                    print(f"  ❌ {method_name}: {e}")
                    total_failed += 1
                except Exception as e:
                    print(f"  ❌ {method_name}: {type(e).__name__}: {e}")
                    total_failed += 1
    
    print(f"\n{'='*40}")
    print(f"Results: {total_passed} passed, {total_failed} failed")
    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

