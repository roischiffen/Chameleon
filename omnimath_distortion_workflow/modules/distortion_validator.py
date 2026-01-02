"""
🦎 Chameleon Framework - Distortion Validator
=============================================

Validates that mathematical distortions preserve problem meaning and answers.

Validation approaches:
1. Automated checks (structure, numbers, length)
2. LLM-based semantic validation (GPT-4o-mini for cost efficiency)
3. Human review helpers

Author: Chameleon Framework
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# AUTOMATED VALIDATION CHECKS
# =============================================================================

class AutomatedValidator:
    """
    Performs automated validation checks on distorted questions.
    These are fast, cheap checks that catch obvious problems.
    """
    
    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """
        Extract all numbers from text (integers, decimals, fractions).
        
        Args:
            text: Text to extract numbers from
            
        Returns:
            List of number strings found
        """
        # Match various number formats
        patterns = [
            r'\b\d+\b',                    # Integers: 5, 100, 42
            r'\b\d+\.\d+\b',               # Decimals: 3.14, 2.5
            r'\b\d+/\d+\b',                # Fractions: 1/2, 3/4
            r'\b\d+\^\d+\b',               # Powers: 2^3, 10^6
            r'\b\d+\^{[^}]+}\b',           # LaTeX powers: 2^{10}
            r'\\frac{(\d+)}{(\d+)}',       # LaTeX fractions
        ]
        
        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if isinstance(matches[0], tuple) if matches else False:
                # Handle tuple matches from groups
                for match in matches:
                    numbers.extend(match)
            else:
                numbers.extend(matches)
        
        return sorted(set(numbers))
    
    @staticmethod
    def extract_math_symbols(text: str) -> List[str]:
        """
        Extract mathematical symbols and operators.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of math symbols found
        """
        # Common math symbols
        symbols = []
        
        # Check for specific symbols
        symbol_patterns = [
            (r'[≤≥<>≠=]', 'comparison'),
            (r'[∈∉⊂⊃⊆⊇]', 'set_membership'),
            (r'[∀∃]', 'quantifier'),
            (r'[∑∏∫]', 'operation'),
            (r'[√∛]', 'root'),
            (r'[π]', 'constant'),
            (r'\\sum|\\prod|\\int', 'latex_operation'),
            (r'\\frac|\\sqrt', 'latex_function'),
            (r'\\le|\\ge|\\neq', 'latex_comparison'),
        ]
        
        for pattern, category in symbol_patterns:
            if re.search(pattern, text):
                symbols.append(category)
        
        return sorted(set(symbols))
    
    @staticmethod
    def check_length_ratio(original: str, distorted: str) -> Tuple[bool, float]:
        """
        Check if distorted length is reasonable relative to original.
        
        Args:
            original: Original question
            distorted: Distorted question
            
        Returns:
            Tuple of (is_valid, ratio)
        """
        if not original or not distorted:
            return False, 0.0
        
        ratio = len(distorted) / len(original)
        
        # Allow 50% shorter to 200% longer
        is_valid = 0.5 <= ratio <= 2.0
        
        return is_valid, ratio
    
    @staticmethod
    def check_not_identical(original: str, distorted: str, miu: float) -> bool:
        """
        Check that distortion actually changed the text (unless μ=0.0).
        
        Args:
            original: Original question
            distorted: Distorted question
            miu: Distortion level
            
        Returns:
            True if valid (different for μ>0, same for μ=0)
        """
        if miu == 0.0:
            return original == distorted
        else:
            return original != distorted
    
    @staticmethod
    def check_numbers_preserved(original: str, distorted: str) -> Tuple[bool, Dict]:
        """
        Check that all numbers are preserved in distortion.
        
        Args:
            original: Original question
            distorted: Distorted question
            
        Returns:
            Tuple of (is_valid, details)
        """
        original_nums = AutomatedValidator.extract_numbers(original)
        distorted_nums = AutomatedValidator.extract_numbers(distorted)
        
        # Check for missing or added numbers
        original_set = set(original_nums)
        distorted_set = set(distorted_nums)
        
        missing = original_set - distorted_set
        added = distorted_set - original_set
        
        # It's OK to have the same numbers in different forms
        # But core numbers should be preserved
        is_valid = len(missing) == 0 or len(missing) <= 1  # Allow 1 missing (edge cases)
        
        return is_valid, {
            'original_numbers': list(original_set),
            'distorted_numbers': list(distorted_set),
            'missing': list(missing),
            'added': list(added)
        }
    
    def validate_single(self, 
                       original: str, 
                       distorted: str, 
                       miu: float) -> Dict[str, Any]:
        """
        Run all automated validation checks on a single distortion.
        
        Args:
            original: Original question
            distorted: Distorted question  
            miu: Distortion level
            
        Returns:
            Validation result dictionary
        """
        results = {
            'miu': miu,
            'checks': {},
            'all_passed': True,
            'warnings': []
        }
        
        # Check 1: Not empty
        not_empty = bool(distorted and len(distorted.strip()) > 10)
        results['checks']['not_empty'] = not_empty
        if not not_empty:
            results['all_passed'] = False
        
        # Check 2: Not identical (unless μ=0)
        identity_check = self.check_not_identical(original, distorted, miu)
        results['checks']['identity_valid'] = identity_check
        if not identity_check:
            results['all_passed'] = False
        
        # Check 3: Length ratio
        length_valid, ratio = self.check_length_ratio(original, distorted)
        results['checks']['length_valid'] = length_valid
        results['checks']['length_ratio'] = ratio
        if not length_valid:
            results['warnings'].append(f"Unusual length ratio: {ratio:.2f}")
        
        # Check 4: Numbers preserved
        numbers_valid, numbers_details = self.check_numbers_preserved(original, distorted)
        results['checks']['numbers_preserved'] = numbers_valid
        results['checks']['numbers_details'] = numbers_details
        if not numbers_valid:
            results['warnings'].append(f"Numbers may not be preserved: missing {numbers_details['missing']}")
        
        # Check 5: Math symbols preserved
        original_symbols = self.extract_math_symbols(original)
        distorted_symbols = self.extract_math_symbols(distorted)
        symbols_valid = len(set(original_symbols) - set(distorted_symbols)) <= 1
        results['checks']['symbols_preserved'] = symbols_valid
        if not symbols_valid:
            results['warnings'].append("Some math symbols may be missing")
        
        return results
    
    def validate_batch(self, 
                      results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of distortion results.
        
        Args:
            results: List of result dictionaries with original/distorted questions
            
        Returns:
            Batch validation summary
        """
        validations = []
        
        for r in results:
            if r['miu'] == 0.0:
                continue  # Skip baseline
            
            validation = self.validate_single(
                r['original_question'],
                r['distorted_question'],
                r['miu']
            )
            validation['question_id'] = r['question_id']
            validations.append(validation)
        
        # Calculate summary statistics
        total = len(validations)
        passed = sum(1 for v in validations if v['all_passed'])
        
        summary = {
            'total_validated': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': passed / total if total > 0 else 0,
            'validations': validations
        }
        
        # Group by μ level
        by_miu = {}
        for v in validations:
            miu = v['miu']
            if miu not in by_miu:
                by_miu[miu] = {'total': 0, 'passed': 0}
            by_miu[miu]['total'] += 1
            if v['all_passed']:
                by_miu[miu]['passed'] += 1
        
        summary['by_miu'] = by_miu
        
        return summary


# =============================================================================
# LLM-BASED VALIDATION
# =============================================================================

class LLMValidator:
    """
    Uses GPT-4o-mini for semantic validation of distortions.
    More expensive but catches subtle meaning changes.
    """
    
    VALIDATION_PROMPT = """You are a mathematical validation expert. Your task is to verify that a distorted version of a math problem preserves the EXACT mathematical meaning and answer.

ORIGINAL PROBLEM:
{original}

DISTORTED PROBLEM:
{distorted}

CORRECT ANSWER: {answer}

Please check the following:
1. Does the distorted problem ask the EXACT same mathematical question?
2. Would the correct answer still be "{answer}" for the distorted version?
3. Are ALL numerical values preserved exactly?
4. Are ALL constraints and conditions preserved?
5. Is the problem still clear and unambiguous?

Respond with ONLY one of these:
- VALID - if all checks pass
- INVALID: [brief reason] - if any check fails

Your response:"""

    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize LLM validator.
        
        Args:
            model: Model to use for validation (gpt-4o-mini recommended for cost)
        """
        self.model = model
        self.client = None
        
    def _init_client(self):
        """Initialize OpenAI client lazily."""
        if self.client is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
    
    def validate_single(self,
                       original: str,
                       distorted: str,
                       answer: str,
                       miu: float) -> Dict[str, Any]:
        """
        Validate a single distortion using LLM.
        
        Args:
            original: Original question
            distorted: Distorted question
            answer: Correct answer
            miu: Distortion level
            
        Returns:
            Validation result dictionary
        """
        if miu == 0.0:
            return {'valid': True, 'reason': 'Baseline (no distortion)'}
        
        self._init_client()
        
        prompt = self.VALIDATION_PROMPT.format(
            original=original,
            distorted=distorted,
            answer=answer
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )
            
            result_text = response.choices[0].message.content.strip()
            
            is_valid = result_text.upper().startswith("VALID")
            
            return {
                'valid': is_valid,
                'response': result_text,
                'miu': miu
            }
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return {
                'valid': None,
                'error': str(e),
                'miu': miu
            }
    
    def validate_sample(self,
                       results: List[Dict[str, Any]],
                       sample_rate: float = 0.15) -> Dict[str, Any]:
        """
        Validate a random sample of distortions.
        
        Args:
            results: List of result dictionaries
            sample_rate: Fraction of results to validate (default 15%)
            
        Returns:
            Sample validation summary
        """
        import random
        
        # Filter out baseline (μ=0.0)
        to_validate = [r for r in results if r['miu'] > 0]
        
        # Sample
        sample_size = max(1, int(len(to_validate) * sample_rate))
        sample = random.sample(to_validate, min(sample_size, len(to_validate)))
        
        logger.info(f"🔍 Validating {len(sample)} samples ({sample_rate*100:.0f}% of {len(to_validate)})")
        
        validations = []
        
        for r in sample:
            validation = self.validate_single(
                r['original_question'],
                r['distorted_question'],
                str(r['correct_answer']),
                r['miu']
            )
            validation['question_id'] = r['question_id']
            validations.append(validation)
        
        # Summary
        valid_count = sum(1 for v in validations if v.get('valid') is True)
        invalid_count = sum(1 for v in validations if v.get('valid') is False)
        error_count = sum(1 for v in validations if v.get('valid') is None)
        
        return {
            'sample_size': len(sample),
            'valid': valid_count,
            'invalid': invalid_count,
            'errors': error_count,
            'validation_rate': valid_count / len(sample) if sample else 0,
            'details': validations
        }


# =============================================================================
# HUMAN REVIEW HELPERS
# =============================================================================

class HumanReviewHelper:
    """
    Helpers for human review of distortions.
    """
    
    @staticmethod
    def generate_review_report(results: List[Dict[str, Any]],
                               output_path: str,
                               focus_miu_levels: List[float] = None) -> str:
        """
        Generate a human-readable review report.
        
        Args:
            results: List of result dictionaries
            output_path: Path to save report
            focus_miu_levels: μ levels to focus on (default: [0.8, 0.9])
            
        Returns:
            Path to generated report
        """
        if focus_miu_levels is None:
            focus_miu_levels = [0.8, 0.9]  # Focus on high-risk levels
        
        output_file = Path(output_path)
        
        lines = [
            "# 🦎 CHAMELEON - Human Review Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nFocus μ levels: {focus_miu_levels}",
            "\n---\n"
        ]
        
        # Group by question
        by_question = {}
        for r in results:
            qid = r['question_id']
            if qid not in by_question:
                by_question[qid] = []
            by_question[qid].append(r)
        
        # Generate review items for focus μ levels
        review_count = 0
        
        for qid, entries in by_question.items():
            original = entries[0]['original_question']
            answer = entries[0]['correct_answer']
            difficulty = entries[0]['difficulty']
            
            focus_entries = [e for e in entries if e['miu'] in focus_miu_levels]
            
            if not focus_entries:
                continue
            
            review_count += 1
            
            lines.append(f"\n## Question {qid} (Difficulty: {difficulty})\n")
            lines.append(f"### Original:\n```\n{original}\n```\n")
            lines.append(f"### Answer: `{answer}`\n")
            
            for entry in focus_entries:
                miu = entry['miu']
                distorted = entry['distorted_question']
                desc = entry.get('miu_description', f'μ={miu}')
                
                lines.append(f"\n### Distorted (μ={miu} - {desc}):\n")
                lines.append(f"```\n{distorted}\n```\n")
                lines.append("\n**Review checklist:**\n")
                lines.append("- [ ] Same mathematical question?\n")
                lines.append("- [ ] Same answer?\n")
                lines.append("- [ ] Numbers preserved?\n")
                lines.append("- [ ] Clear and unambiguous?\n")
                lines.append("\n---\n")
        
        lines.append(f"\n\n**Total items to review: {review_count}**\n")
        
        # Write report
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"📝 Generated review report: {output_file}")
        
        return str(output_file)
    
    @staticmethod
    def flag_suspicious(results: List[Dict[str, Any]],
                       automated_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Flag results that need human attention based on automated checks.
        
        Args:
            results: Original results
            automated_results: Results from AutomatedValidator
            
        Returns:
            List of flagged results with reasons
        """
        flagged = []
        
        validations = {v['question_id']: v 
                      for v in automated_results.get('validations', [])}
        
        for r in results:
            if r['miu'] == 0.0:
                continue
            
            qid = r['question_id']
            validation = validations.get(qid, {})
            
            reasons = []
            
            # Check for issues
            if not validation.get('checks', {}).get('numbers_preserved', True):
                reasons.append("Numbers may have changed")
            
            if validation.get('checks', {}).get('length_ratio', 1.0) > 1.8:
                reasons.append("Much longer than original")
            
            if validation.get('checks', {}).get('length_ratio', 1.0) < 0.6:
                reasons.append("Much shorter than original")
            
            if r['miu'] >= 0.8:
                reasons.append("High μ level - verify meaning preserved")
            
            if reasons:
                flagged.append({
                    **r,
                    'flag_reasons': reasons
                })
        
        return flagged


# =============================================================================
# MAIN VALIDATION RUNNER
# =============================================================================

def run_full_validation(results: List[Dict[str, Any]],
                       output_dir: str = "validation_results",
                       llm_sample_rate: float = 0.15) -> Dict[str, Any]:
    """
    Run complete validation pipeline.
    
    Args:
        results: List of distortion results
        output_dir: Directory for output files
        llm_sample_rate: Rate for LLM validation sampling
        
    Returns:
        Complete validation summary
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 70)
    print("  🔍 DISTORTION VALIDATION")
    print("=" * 70)
    
    # Step 1: Automated validation
    print("\n📋 Running automated validation...")
    auto_validator = AutomatedValidator()
    auto_results = auto_validator.validate_batch(results)
    
    print(f"   ✓ Validated {auto_results['total_validated']} distortions")
    print(f"   ✓ Pass rate: {auto_results['pass_rate']*100:.1f}%")
    
    # Step 2: LLM validation (sample)
    print(f"\n🤖 Running LLM validation ({llm_sample_rate*100:.0f}% sample)...")
    llm_validator = LLMValidator()
    llm_results = llm_validator.validate_sample(results, llm_sample_rate)
    
    print(f"   ✓ Sampled {llm_results['sample_size']} distortions")
    print(f"   ✓ Validation rate: {llm_results['validation_rate']*100:.1f}%")
    
    # Step 3: Generate human review report
    print("\n📝 Generating human review report...")
    review_path = HumanReviewHelper.generate_review_report(
        results,
        output_path / "human_review_report.md"
    )
    
    # Step 4: Flag suspicious results
    flagged = HumanReviewHelper.flag_suspicious(results, auto_results)
    print(f"   ⚠️ Flagged {len(flagged)} items for review")
    
    # Save all results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save automated results
    auto_path = output_path / f"automated_validation_{timestamp}.json"
    with open(auto_path, 'w') as f:
        json.dump(auto_results, f, indent=2)
    
    # Save LLM results
    llm_path = output_path / f"llm_validation_{timestamp}.json"
    with open(llm_path, 'w') as f:
        json.dump(llm_results, f, indent=2)
    
    # Save flagged items
    if flagged:
        flagged_path = output_path / f"flagged_items_{timestamp}.json"
        with open(flagged_path, 'w') as f:
            json.dump(flagged, f, indent=2)
    
    print("\n" + "=" * 70)
    print("  ✅ VALIDATION COMPLETE")
    print("=" * 70)
    print(f"\n💾 Results saved to: {output_path}/")
    
    return {
        'automated': auto_results,
        'llm': llm_results,
        'flagged_count': len(flagged),
        'review_report': review_path
    }


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("🦎 Chameleon - Distortion Validator Module")
    print("=" * 50)
    print("\nThis module provides validation tools for distortions.")
    print("\nUsage:")
    print("  from modules.distortion_validator import run_full_validation")
    print("  results = run_full_validation(distortion_results)")

