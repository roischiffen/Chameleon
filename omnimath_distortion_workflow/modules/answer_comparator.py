"""
Answer Comparator Module for OmniMath Evaluation

Compares model answers with ground truth using:
- Exact string matching after normalization
- Numeric equivalence with tolerance
- Fraction and percentage parsing
- LaTeX expression evaluation (fractions, sqrt, exponents)
- Coordinate/tuple comparison
- Text answer detection

Examples:
    >>> compare_answers("150", "150")
    (True, 'exact')
    >>> compare_answers("0.5", "1/2")
    (True, 'numeric')
    >>> compare_answers("0.5", r"\\frac{1}{2}")
    (True, 'numeric')
    >>> compare_answers("8", "2^3")
    (True, 'expression')
    >>> compare_answers("(2,2), (-2,-2)", "(−2,−2), (2,2)")
    (True, 'coordinate')
    >>> compare_answers("anything", "There are no pairs that satisfy...")
    (None, 'text_answer')
"""

import re
import math
from fractions import Fraction
from typing import Optional, Tuple, List, Set, Union

# Try to import sympy for expression evaluation
try:
    from sympy import sympify, simplify, N, sqrt as sympy_sqrt, Rational, Integer, Float, pi, E
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
    from sympy.core.numbers import NumberSymbol
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


# ============================================================================
# TEXT ANSWER DETECTION
# ============================================================================

def is_text_answer(answer: str) -> bool:
    """
    Check if an answer is primarily text (not a mathematical expression).
    
    Returns True if the answer:
    - Contains multiple English words
    - Starts with common text phrases
    - Does not look like a number or math expression
    
    Args:
        answer: Answer string to check
        
    Returns:
        True if answer appears to be text, not math
        
    Examples:
        >>> is_text_answer("There are no pairs...")
        True
        >>> is_text_answer("150")
        False
        >>> is_text_answer("1/2")
        False
        >>> is_text_answer("The answer is undefined")
        True
    """
    if not answer:
        return False
    
    # Clean the answer
    cleaned = answer.strip()
    
    # Common text answer phrases
    text_starters = [
        r'^there\s+(are|is)\s+no',
        r'^no\s+(solution|answer|pairs?|values?)',
        r'^impossible',
        r'^undefined',
        r'^does\s+not\s+exist',
        r'^infinitely\s+many',
        r'^none',
        r'^cannot\s+be\s+determined',
        r'^the\s+answer\s+is\s+(undefined|impossible|none)',
        r'^no\s+such',
        r'^it\s+is\s+(impossible|not\s+possible)',
    ]
    
    for pattern in text_starters:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return True
    
    # Count English words (3+ letter words that aren't math terms)
    math_terms = {'sin', 'cos', 'tan', 'log', 'sqrt', 'frac', 'exp', 'mod', 'gcd', 'lcm', 'max', 'min'}
    words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower())
    english_words = [w for w in words if w not in math_terms]
    
    # If more than 3 English words, likely text
    if len(english_words) > 3:
        return True
    
    # Check if it looks numeric/mathematical
    # Remove LaTeX, spaces, common math symbols
    math_cleaned = re.sub(r'[\s\\{}\[\]()$]', '', cleaned)
    math_cleaned = re.sub(r'(frac|sqrt|cdot|times|div|pm)', '', math_cleaned)
    
    # If what remains is mostly non-alphanumeric math symbols and digits, it's math
    if math_cleaned:
        math_chars = sum(1 for c in math_cleaned if c.isdigit() or c in '+-*/^.,=<>')
        if math_chars / len(math_cleaned) < 0.3:
            return True
    
    return False


# ============================================================================
# COORDINATE/TUPLE PARSING
# ============================================================================

def parse_coordinates(answer: str) -> Optional[Set[Tuple[float, ...]]]:
    """
    Parse coordinate pairs or tuples from an answer string.
    
    Handles formats like:
    - "(2, 2), (-2, -2)"
    - "(2,2),(-2,-2)"
    - "(-2, -2), (2, 2)"  (different order)
    - "(1, 2, 3)"  (3D coordinates)
    
    Args:
        answer: Answer string containing coordinates
        
    Returns:
        Set of tuples (for order-independent comparison), or None if not parseable
        
    Examples:
        >>> parse_coordinates("(2, 2), (-2, -2)")
        {(2.0, 2.0), (-2.0, -2.0)}
    """
    if not answer:
        return None
    
    # Normalize unicode minus signs
    answer = answer.replace('−', '-').replace('–', '-')
    
    # Find all coordinate tuples: (a, b) or (a, b, c) etc.
    pattern = r'\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*(?:,\s*(-?\d+(?:\.\d+)?))?\s*\)'
    matches = re.findall(pattern, answer)
    
    if not matches:
        return None
    
    coordinates = set()
    for match in matches:
        try:
            # Filter out empty strings from optional third coordinate
            nums = [float(x) for x in match if x]
            coordinates.add(tuple(nums))
        except ValueError:
            continue
    
    return coordinates if coordinates else None


def compare_coordinates(pred: str, truth: str) -> bool:
    """
    Compare two answers as coordinate sets.
    
    Order-independent comparison of coordinate tuples.
    
    Args:
        pred: Predicted answer
        truth: Ground truth answer
        
    Returns:
        True if coordinate sets match
    """
    pred_coords = parse_coordinates(pred)
    truth_coords = parse_coordinates(truth)
    
    if pred_coords is None or truth_coords is None:
        return False
    
    return pred_coords == truth_coords


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_answer(answer: str) -> str:
    """
    Normalize an answer string for comparison.
    
    Operations:
    - Strip leading/trailing whitespace
    - Convert to lowercase
    - Remove LaTeX delimiters ($...$, \\(...\\), \\[...\\])
    - Remove thousands separators (1,000 → 1000)
    - Normalize whitespace (multiple spaces → single space)
    - Normalize unicode minus signs
    
    Args:
        answer: Raw answer string
        
    Returns:
        Normalized answer string, empty string if input is None or empty
    """
    if answer is None:
        return ""
    
    if not isinstance(answer, str):
        answer = str(answer)
    
    # Strip whitespace
    result = answer.strip()
    
    if not result:
        return ""
    
    # Normalize unicode characters
    result = result.replace('−', '-').replace('–', '-')
    result = result.replace('×', '*').replace('·', '*')
    
    # Convert to lowercase
    result = result.lower()
    
    # Remove LaTeX delimiters: $...$, \(...\), \[...\]
    result = re.sub(r'\$([^$]*)\$', r'\1', result)
    result = re.sub(r'\\\(([^)]*)\\\)', r'\1', result)
    result = re.sub(r'\\\[([^\]]*)\\\]', r'\1', result)
    
    # Remove thousands separators (1,000 → 1000)
    result = re.sub(r'(\d),(\d)', r'\1\2', result)
    while re.search(r'(\d),(\d)', result):
        result = re.sub(r'(\d),(\d)', r'\1\2', result)
    
    # Normalize whitespace
    result = ' '.join(result.split())
    
    return result


# ============================================================================
# NUMBER PARSING
# ============================================================================

def parse_as_number(answer: str) -> Optional[float]:
    """
    Try to parse an answer string as a number.
    
    Handles:
    - Integers (150, -42)
    - Decimals (0.5, .5, 0.50)
    - Fractions (1/2, 3/4, -1/2)
    - Percentages (50%, 50 percent)
    - Scientific notation (1e5, 1E5, 1×10^5)
    
    Args:
        answer: Normalized answer string
        
    Returns:
        Float value if parseable, None otherwise
    """
    if not answer:
        return None
    
    answer = answer.strip()
    
    # Try integer first
    try:
        return float(int(answer))
    except ValueError:
        pass
    
    # Try float/decimal
    try:
        return float(answer)
    except ValueError:
        pass
    
    # Try fraction (e.g., "1/2", "3/4")
    fraction_match = re.match(r'^(-?\d+)\s*/\s*(-?\d+)$', answer)
    if fraction_match:
        try:
            numerator = int(fraction_match.group(1))
            denominator = int(fraction_match.group(2))
            if denominator != 0:
                return float(Fraction(numerator, denominator))
        except (ValueError, ZeroDivisionError):
            pass
    
    # Try percentage (e.g., "50%", "50 percent")
    percent_match = re.match(r'^(-?\d+(?:\.\d+)?)\s*(%|percent)$', answer)
    if percent_match:
        try:
            value = float(percent_match.group(1))
            return value / 100.0
        except ValueError:
            pass
    
    # Try scientific notation (e.g., "1e5", "1E5")
    sci_match = re.match(r'^(-?\d+(?:\.\d+)?)\s*[eE]\s*(-?\d+)$', answer)
    if sci_match:
        try:
            base = float(sci_match.group(1))
            exp = int(sci_match.group(2))
            return base * (10 ** exp)
        except ValueError:
            pass
    
    # Try alternative scientific notation (e.g., "1×10^5", "1*10^5")
    alt_sci_match = re.match(r'^(-?\d+(?:\.\d+)?)\s*[×x\*]\s*10\s*\^\s*(-?\d+)$', answer)
    if alt_sci_match:
        try:
            base = float(alt_sci_match.group(1))
            exp = int(alt_sci_match.group(2))
            return base * (10 ** exp)
        except ValueError:
            pass
    
    return None


# ============================================================================
# LATEX EXPRESSION EVALUATION
# ============================================================================

def parse_latex_fraction(latex: str) -> Optional[float]:
    """
    Parse a LaTeX fraction to a float.
    
    Handles:
    - Simple: \\frac{1}{2} → 0.5
    - With expressions: \\frac{\\sqrt{2}}{3} → 0.4714...
    - Nested: \\frac{1}{\\frac{1}{2}} → 2.0
    
    Args:
        latex: LaTeX string containing a fraction
        
    Returns:
        Float value, or None if not parseable
    """
    if not latex or '\\frac' not in latex and 'frac' not in latex.lower():
        return None
    
    # Use the full expression evaluator
    return evaluate_expression(latex)


def normalize_for_expression(answer: str) -> str:
    """
    Normalize answer string for sympy expression parsing.
    
    Converts common mathematical notations to sympy-compatible format:
    - LaTeX fractions: \\frac{a}{b} → (a)/(b)
    - Caret exponents: a^b → a**b
    - LaTeX sqrt: \\sqrt{x} → sqrt(x)
    - LaTeX commands: \\cdot → *, \\times → *
    
    Args:
        answer: Answer string to normalize
        
    Returns:
        Sympy-compatible expression string
    """
    if not answer:
        return ""
    
    result = answer.strip()
    
    # Remove common LaTeX delimiters
    result = re.sub(r'\$([^$]*)\$', r'\1', result)
    result = re.sub(r'\\\(([^)]*)\\\)', r'\1', result)
    result = re.sub(r'\\\[([^\]]*)\\\]', r'\1', result)
    
    # Remove \displaystyle and similar
    result = re.sub(r'\\displaystyle\s*', '', result)
    result = re.sub(r'\\textstyle\s*', '', result)
    result = re.sub(r'\\text\{[^}]*\}', '', result)
    
    # First, convert sqrt INSIDE fractions: \sqrt{x} → sqrt(x)
    # This must happen before frac conversion so sqrt is preserved
    for _ in range(10):
        prev = result
        result = re.sub(r'\\sqrt\[(\d+)\]\s*\{([^{}]*)\}', r'((\2))**(1/\1)', result)
        result = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'sqrt(\1)', result)
        if result == prev:
            break
    
    # Convert LaTeX fractions: \frac{a}{b} → (a)/(b)
    # Handle nested braces by multiple passes
    def replace_frac(match):
        return f"(({match.group(1)})/({match.group(2)}))"
    
    for _ in range(10):  # Max depth of nesting
        prev = result
        result = re.sub(r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', replace_frac, result)
        if result == prev:
            break
    
    # Convert ^ to ** for exponentiation
    result = re.sub(r'\^{([^{}]+)}', r'**(\1)', result)
    result = re.sub(r'\^(\d+)', r'**\1', result)
    result = re.sub(r'\^([a-zA-Z])', r'**\1', result)
    
    # Replace LaTeX operators
    result = result.replace('\\cdot', '*')
    result = result.replace('\\times', '*')
    result = result.replace('×', '*')
    result = result.replace('·', '*')
    result = result.replace('\\div', '/')
    
    # Handle pi and e
    result = re.sub(r'\\pi\b', 'pi', result)
    result = result.replace('π', 'pi')
    
    # Remove remaining backslashes before common functions
    result = re.sub(r'\\(sin|cos|tan|log|ln|exp|pi)', r'\1', result)
    
    # Remove any remaining backslashes
    result = result.replace('\\', '')
    
    # Clean up whitespace
    result = ' '.join(result.split())
    
    return result


def evaluate_expression(expr_str: str) -> Optional[float]:
    """
    Try to evaluate a mathematical expression string to a numeric value.
    
    Uses sympy for safe evaluation of expressions like:
    - 2^3 → 8
    - sqrt(16) → 4
    - \\frac{1}{2} → 0.5
    - \\frac{\\sqrt{2}}{3} → 0.4714...
    
    Args:
        expr_str: Expression string to evaluate
        
    Returns:
        Float value if evaluable, None otherwise
    """
    if not SYMPY_AVAILABLE:
        return None
    
    if not expr_str or not expr_str.strip():
        return None
    
    # Normalize the expression for sympy
    normalized = normalize_for_expression(expr_str)
    
    if not normalized:
        return None
    
    try:
        # Try direct parsing with sympy
        transformations = standard_transformations + (implicit_multiplication_application,)
        
        # Create local dict for safe evaluation
        local_dict = {'sqrt': sympy_sqrt, 'pi': pi, 'e': E}
        
        try:
            parsed = sympify(normalized, locals=local_dict, evaluate=True)
        except:
            try:
                parsed = parse_expr(normalized, local_dict=local_dict, transformations=transformations)
            except:
                return None
        
        # Get numeric value
        numeric_val = N(parsed)
        
        # Check if result is actually numeric
        if numeric_val.is_number:
            result = float(numeric_val)
            # Guard against infinity and NaN
            if math.isfinite(result):
                return result
    except Exception:
        pass
    
    return None


# ============================================================================
# MAIN COMPARISON FUNCTION
# ============================================================================

def compare_answers(predicted: str, ground_truth: str, tolerance: float = 1e-4) -> Tuple[Union[bool, None], str]:
    """
    Compare predicted answer with ground truth.
    
    Comparison strategy (in order):
    1. Text answer detection → (None, "text_answer")
    2. Exact match after normalization → (True, "exact")
    3. Numeric comparison with tolerance → (True, "numeric")
    4. Coordinate/tuple comparison → (True, "coordinate")
    5. Expression evaluation comparison → (True, "expression")
    6. No match → (False, "no_match")
    
    Args:
        predicted: Model's predicted answer
        ground_truth: Correct answer
        tolerance: Numeric tolerance (default 1e-6, ~6 decimal places)
        
    Returns:
        Tuple of (is_correct, match_type)
        - is_correct can be True, False, or None (for text answers needing manual review)
        
    Examples:
        >>> compare_answers("150", "150")
        (True, 'exact')
        >>> compare_answers("0.5", "1/2")
        (True, 'numeric')
        >>> compare_answers("0.5", r"\\frac{1}{2}")
        (True, 'numeric')
        >>> compare_answers("8", "2^3")
        (True, 'expression')
        >>> compare_answers("(2,2), (-2,-2)", "(−2,−2), (2,2)")
        (True, 'coordinate')
        >>> compare_answers("anything", "There are no pairs...")
        (None, 'text_answer')
    """
    # 0. Handle None/empty inputs
    if ground_truth is None or (isinstance(ground_truth, str) and not ground_truth.strip()):
        return (False, "no_match")
    
    # 1. Check if ground truth is a text answer (needs manual review)
    if is_text_answer(ground_truth):
        return (None, "text_answer")
    
    # Normalize both answers
    norm_predicted = normalize_answer(predicted)
    norm_truth = normalize_answer(ground_truth)
    
    # 2. Try exact match after normalization
    if norm_predicted and norm_predicted == norm_truth:
        return (True, "exact")
    
    # 3. Try numeric comparison
    pred_num = parse_as_number(norm_predicted)
    truth_num = parse_as_number(norm_truth)
    
    if pred_num is not None and truth_num is not None:
        if abs(pred_num - truth_num) <= tolerance:
            return (True, "numeric")
        if truth_num != 0 and abs((pred_num - truth_num) / truth_num) <= tolerance:
            return (True, "numeric")
    
    # 4. Try coordinate comparison
    if '(' in (predicted or '') and '(' in (ground_truth or ''):
        if compare_coordinates(predicted, ground_truth):
            return (True, "coordinate")
    
    # 5. Try expression evaluation
    if SYMPY_AVAILABLE:
        # Check if either looks like a mathematical expression
        expression_patterns = [
            r'\^', r'\*\*', r'\\frac', r'\\sqrt', r'sqrt\(', 
            r'\d+\s*/\s*\d+', r'\\pi', r'π'
        ]
        
        looks_like_expr = any(
            re.search(pattern, predicted or '', re.IGNORECASE) or 
            re.search(pattern, ground_truth or '', re.IGNORECASE)
            for pattern in expression_patterns
        )
        
        if looks_like_expr or (pred_num is None or truth_num is None):
            pred_eval = evaluate_expression(predicted)
            truth_eval = evaluate_expression(ground_truth)
            
            # Use already-parsed numeric values as fallback
            if pred_eval is None and pred_num is not None:
                pred_eval = pred_num
            if truth_eval is None and truth_num is not None:
                truth_eval = truth_num
            
            if pred_eval is not None and truth_eval is not None:
                if abs(pred_eval - truth_eval) <= tolerance:
                    return (True, "expression")
                if truth_eval != 0 and abs((pred_eval - truth_eval) / truth_eval) <= tolerance:
                    return (True, "expression")
    
    # 6. No match
    return (False, "no_match")


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    print("Testing Enhanced Answer Comparator Module\n")
    print(f"Sympy available: {SYMPY_AVAILABLE}\n")
    print("=" * 70)
    
    test_cases = [
        # (predicted, ground_truth, expected_result, expected_type)
        
        # === EXACT MATCHES ===
        ("150", "150", True, "exact"),
        (" 150 ", "150", True, "exact"),
        ("$150$", "150", True, "exact"),
        ("1000", "1,000", True, "exact"),
        
        # === NUMERIC MATCHES ===
        ("0.5", "1/2", True, "numeric"),
        ("0.50", "0.5", True, "numeric"),
        ("50%", "0.5", True, "numeric"),
        ("1e5", "100000", True, "numeric"),
        ("-3/4", "-0.75", True, "numeric"),
        ("0.03094482421875", "507/16384", True, "numeric"),
        
        # === EXPRESSION MATCHES ===
        ("8", "2^3", True, "expression"),
        ("8", "2**3", True, "expression"),
        ("4", r"\sqrt{16}", True, "expression"),
        ("4", "sqrt(16)", True, "expression"),
        ("0.5", r"\frac{1}{2}", True, "expression"),
        ("27", "3^3", True, "expression"),
        ("100", "10^2", True, "expression"),
        ("0.01", "10^{-2}", True, "expression"),
        
        # === LATEX FRACTIONS WITH EXPRESSIONS ===
        ("0.4714", r"\frac{\sqrt{2}}{3}", True, "expression"),  # sqrt(2)/3 ≈ 0.4714
        ("2.0", r"\frac{1}{\frac{1}{2}}", True, "expression"),  # 1/(1/2) = 2
        
        # === COORDINATE MATCHES ===
        ("(2, 2), (-2, -2)", "(2,2),(-2,-2)", True, "coordinate"),
        ("(2, 2), (-2, -2)", "(-2, -2), (2, 2)", True, "coordinate"),  # Order independent
        ("(−2, −2), (2, 2)", "(2, 2), (-2, -2)", True, "coordinate"),  # Unicode minus
        
        # === TEXT ANSWERS ===
        ("42", "There are no pairs that satisfy the condition", None, "text_answer"),
        ("100", "No solution exists", None, "text_answer"),
        ("xyz", "It is impossible to determine", None, "text_answer"),
        
        # === NO MATCHES ===
        ("150", "151", False, "no_match"),
        ("abc", "150", False, "no_match"),
        ("7", "2^3", False, "no_match"),  # 7 ≠ 8
        ("10", "5", False, "no_match"),
    ]
    
    passed = 0
    failed = 0
    
    for pred, truth, expected_correct, expected_type in test_cases:
        result, match_type = compare_answers(pred, truth)
        
        # For expression/numeric, accept either as valid
        type_ok = (match_type == expected_type) or \
                  (expected_type in ["expression", "numeric"] and match_type in ["expression", "numeric"])
        
        is_pass = (result == expected_correct and type_ok)
        status = "✅" if is_pass else "❌"
        
        if is_pass:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} compare_answers({repr(pred)[:20]}, {repr(truth)[:30]})")
        print(f"   Expected: ({expected_correct}, {repr(expected_type)})")
        print(f"   Got:      ({result}, {repr(match_type)})")
        if not is_pass:
            print(f"   ⚠️  MISMATCH!")
        print()
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
