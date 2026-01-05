#!/usr/bin/env python3
"""
🦎 Chameleon Framework - Phase 1: Dataset Creation
===================================================

Creates verified baseline dataset from Big-Math RL-Verified.

This script:
1. Loads dataset from SynthLabsAI/Big-Math-RL-Verified
2. Filters by source (default: "omni-math")
3. Filters by difficulty tier (T0-T4)
4. Validates questions meet quality criteria
5. Exports to data/source_verified/tier_{tier}/baseline_questions.json

Usage:
    # Create dataset for tier T3 with 100 questions
    python -m src.flows.phase1_create_dataset --tier T3 --count 100
    
    # Create dataset for tier T4 with 50 questions
    python -m src.flows.phase1_create_dataset --tier T4 --count 50
    
    # Use random sampling instead of first N
    python -m src.flows.phase1_create_dataset --tier T3 --count 100 --random

Author: Chameleon Framework
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.modules.bigmath_loader import BigMathLoader


# =============================================================================
# VALIDATION GATE CHECKS
# =============================================================================

def validate_question(question: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a single question against Phase 1 quality criteria.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    # Check 1: Non-empty problem text
    problem = question.get("problem", "").strip()
    if not problem:
        issues.append("Empty problem text")
    
    # Check 2: Closed-form answer exists
    answer = question.get("answer", "").strip()
    if not answer:
        issues.append("Missing answer")
    
    # Check 3: No references to diagrams, figures, options, or "following"
    forbidden_patterns = [
        r'\bdiagram\b',
        r'\bfigure\b',
        r'\boptions?\b',
        r'\bfollowing\b',
        r'\boption\s+[A-E]\b',
        r'\([A-E]\)',
    ]
    
    problem_lower = problem.lower()
    for pattern in forbidden_patterns:
        if re.search(pattern, problem_lower, re.IGNORECASE):
            issues.append(f"Contains forbidden reference: {pattern}")
    
    # Check 4: Reasonable length (not too short, not extremely long)
    if len(problem) < 20:
        issues.append("Problem text too short (< 20 chars)")
    if len(problem) > 5000:
        issues.append("Problem text too long (> 5000 chars)")
    
    # Check 5: Has question mark or clear question indicator
    has_question = (
        '?' in problem or
        'find' in problem_lower or
        'determine' in problem_lower or
        'calculate' in problem_lower or
        'solve' in problem_lower or
        'compute' in problem_lower
    )
    if not has_question:
        issues.append("No clear question/goal identified")
    
    is_valid = len(issues) == 0
    return is_valid, issues


def validate_dataset(questions: List[Dict[str, Any]], expected_count: Optional[int] = None) -> Dict[str, Any]:
    """
    Validate entire dataset and return validation report.
    
    Args:
        questions: List of questions to validate
        expected_count: Expected number of questions (for count check)
        
    Returns:
        Validation report dictionary
    """
    total = len(questions)
    valid_count = 0
    invalid_count = 0
    all_issues = []
    
    for q in questions:
        is_valid, issues = validate_question(q)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            all_issues.append({
                "question_id": q.get("question_id", "unknown"),
                "issues": issues
            })
    
    # Check count match
    count_match = True
    if expected_count is not None:
        count_match = (total == expected_count)
    
    report = {
        "total_questions": total,
        "valid_questions": valid_count,
        "invalid_questions": invalid_count,
        "validation_rate": valid_count / total if total > 0 else 0.0,
        "count_match": count_match,
        "expected_count": expected_count,
        "actual_count": total,
        "issues": all_issues,
        "passed": (valid_count == total) and (count_match if expected_count else True)
    }
    
    return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main entry point for Phase 1."""
    
    parser = argparse.ArgumentParser(
        description="🦎 Chameleon Phase 1: Create Verified Dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create T3 dataset with 100 questions
  %(prog)s --tier T3 --count 100
  
  # Create T4 dataset with 50 questions (random sample)
  %(prog)s --tier T4 --count 50 --random
  
  # Create T2 dataset with all available questions
  %(prog)s --tier T2
  
  # Use different source filter
  %(prog)s --tier T3 --count 100 --source "math-competition"
        """
    )
    
    parser.add_argument(
        '--tier',
        type=str,
        default='T3',
        choices=['T0', 'T1', 'T2', 'T3', 'T4'],
        help='Difficulty tier (T0=hardest, T4=easiest). Default: T3'
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help='Number of questions to select (default: all available)'
    )
    
    parser.add_argument(
        '--random',
        action='store_true',
        help='Use random sampling instead of first N questions'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        default='omnimath',
        help='Source dataset filter (default: omnimath)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/source_verified',
        help='Output directory (default: data/source_verified)'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation checks (not recommended)'
    )
    
    parser.add_argument(
        '--include-reformulated',
        action='store_true',
        default=True,
        help='Include reformulated MC questions (default: True)'
    )
    
    parser.add_argument(
        '--no-reformulated',
        dest='include_reformulated',
        action='store_false',
        help='Exclude reformulated MC questions'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("\n" + "=" * 70)
    print("  🦎 CHAMELEON - Phase 1: Dataset Creation")
    print("=" * 70)
    print(f"\n📋 Configuration:")
    print(f"   • Tier: {args.tier}")
    print(f"   • Source filter: {args.source}")
    print(f"   • Count: {args.count or 'all available'}")
    print(f"   • Sampling: {'random' if args.random else 'first N'}")
    print(f"   • Include reformulated: {args.include_reformulated}")
    print(f"   • Output: {args.output_dir}/tier_{args.tier}/")
    
    # Initialize loader
    print(f"\n📚 Loading Big-Math RL-Verified dataset...")
    loader = BigMathLoader(
        tier=args.tier,
        source_filter=args.source,
        include_reformulated=args.include_reformulated
    )
    
    # Load dataset
    if not loader.load_dataset():
        print("\n❌ Failed to load dataset.")
        print("\n💡 This dataset requires HuggingFace authentication:")
        print("   1. Accept terms: https://huggingface.co/datasets/SynthLabsAI/Big-Math-RL-Verified")
        print("   2. Get token: https://huggingface.co/settings/tokens")
        print("   3. Authenticate: huggingface-cli login")
        print("      OR set HF_TOKEN environment variable")
        sys.exit(1)
    
    # Get verified questions
    print(f"\n🔍 Filtering questions...")
    questions = loader.get_verified_questions(
        count=args.count,
        random_sample=args.random,
        seed=args.seed
    )
    
    if not questions:
        print("❌ No questions found after filtering.")
        print(f"   Try a different tier or source filter.")
        sys.exit(1)
    
    print(f"✅ Loaded {len(questions)} questions")
    
    # Display statistics
    stats = loader.get_statistics()
    print(f"\n📊 Dataset Statistics:")
    print(f"   • Total questions: {stats['total_questions']}")
    print(f"   • Tier: {stats['tier']} ({stats['tier_description']})")
    level_range = stats['level_range']
    if level_range['min'] is not None:
        print(f"   • Level range: {level_range['min']:.1f} - {level_range['max']:.1f}")
    else:
        print(f"   • Level range: Not available (dataset doesn't have level field)")
    print(f"   • Reformulated (MC→Open): {stats.get('reformulated_count', 0)}")
    if stats.get('domains'):
        top_domains = list(stats['domains'].items())[:5]
        print(f"   • Top domains: {', '.join([f'{d}({c})' for d, c in top_domains])}")
    
    # Validation gate
    if not args.skip_validation:
        print(f"\n🔍 Running validation gate checks...")
        validation_report = validate_dataset(questions, expected_count=None)  # Don't check count yet
        
        print(f"\n📋 Validation Results:")
        print(f"   • Total questions: {validation_report['total_questions']}")
        print(f"   • Valid: {validation_report['valid_questions']}")
        print(f"   • Invalid: {validation_report['invalid_questions']}")
        print(f"   • Validation rate: {validation_report['validation_rate']:.1%}")
        
        # Filter out invalid questions
        invalid_ids = {issue['question_id'] for issue in validation_report['issues']}
        valid_questions = [q for q in questions if q.get('question_id') not in invalid_ids]
        
        if validation_report['invalid_questions'] > 0:
            print(f"\n⚠️  Filtering out {validation_report['invalid_questions']} invalid questions:")
            for issue in validation_report['issues'][:10]:  # Show first 10
                print(f"   • {issue['question_id']}: {', '.join(issue['issues'])}")
            if len(validation_report['issues']) > 10:
                print(f"   ... and {len(validation_report['issues']) - 10} more")
            print(f"\n✅ Kept {len(valid_questions)} valid questions")
        
        # If we need more questions and have invalid ones, try to get more
        if args.count and len(valid_questions) < args.count:
            print(f"\n⚠️  Only {len(valid_questions)} valid questions available (requested {args.count})")
            print(f"   Proceeding with {len(valid_questions)} valid questions")
        
        # Update questions list to only valid ones
        questions = valid_questions[:args.count] if args.count else valid_questions
        
        if len(questions) == 0:
            print(f"\n❌ No valid questions remaining after filtering")
            sys.exit(1)
        
        print(f"\n✅ Validation complete - {len(questions)} valid questions ready")
    else:
        print(f"\n⚠️  Skipping validation checks (--skip-validation)")
    
    # Export to Chameleon format
    print(f"\n💾 Exporting to Chameleon format...")
    tier_dir = Path(args.output_dir) / f"tier_{args.tier}"
    tier_dir.mkdir(parents=True, exist_ok=True)
    
    # Save baseline questions
    baseline_path = tier_dir / "baseline_questions.json"
    with open(baseline_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    # Create metadata with validation info
    metadata_path = tier_dir / "metadata.json"
    validation_info = {}
    if not args.skip_validation:
        validation_info = {
            "validated": True,
            "validation_rate": validation_report['validation_rate'],
            "valid_questions": validation_report['valid_questions'],
            "invalid_questions": validation_report['invalid_questions'],
        }
    else:
        validation_info = {"validated": False}
    
    metadata = {
        "tier": args.tier,
        "tier_description": loader.TIER_DESCRIPTIONS[args.tier],
        "total_questions": len(questions),
        "question_ids": [q["question_id"] for q in questions],
        "miu_levels": [0.2, 0.5, 0.7, 0.9],
        "source_dataset": "big-math-rl-verified",
        "source_filter": args.source,
        "level_range": stats["level_range"],
        "domains": stats["domains"],
        "all_verified": True,
        "validation": validation_info,
        "sampling": {
            "random_sample": args.random,
            "seed": args.seed if args.random else None,
            "count": args.count,
        },
        "created_by": "phase1_create_dataset.py",
    }
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ Phase 1 Complete!")
    print(f"\n📁 Output files:")
    print(f"   • Baseline questions: {baseline_path}")
    print(f"   • Metadata: {metadata_path}")
    print(f"\n🎯 Next step: Run Phase 2 to generate distortions")
    print(f"   python -m src.flows.phase2_generate_distortions --tier {args.tier}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

