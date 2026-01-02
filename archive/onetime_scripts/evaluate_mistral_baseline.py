#!/usr/bin/env python3
"""
Mistral Baseline Evaluation Script

Evaluates Mistral Large on ORIGINAL questions (before distortion)
to establish baseline accuracy for comparison with distorted results.

Key Features:
- Saves progress after EVERY question (crash-proof)
- Rate limiting for free tier
- Resume from any interruption
- Same output format as other baseline evaluations

Usage:
    # Test with 5 questions first
    python evaluate_mistral_baseline.py --difficulty 1.0 --test 5
    
    # Full evaluation for difficulty 1.0
    python evaluate_mistral_baseline.py --difficulty 1.0
    
    # Full evaluation for difficulty 1.5
    python evaluate_mistral_baseline.py --difficulty 1.5

Environment:
    MISTRAL_API_KEY: Your Mistral API key (required)
"""

import argparse
import json
import os
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_paths = [
        project_root / ".env",
        project_root / "venv" / "bin" / ".env",  # Your specific .env location
        Path.home() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"📁 Loaded .env from: {env_path}")
            break
except ImportError:
    pass

# Try to import Mistral SDK
try:
    from mistralai import Mistral
except ImportError:
    print("❌ Error: mistralai package not installed")
    print("   Install with: pip install mistralai")
    sys.exit(1)

from omnimath_distortion_workflow.modules.evaluation_prompt import create_evaluation_prompt
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
EVAL_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "baseline_results"

# Model configuration
MODEL_ID = "mistral-large-latest"

# Rate limiting
REQUESTS_PER_MINUTE = 30
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # ~2 seconds
MAX_RETRIES = 5
BACKOFF_FACTOR = 2


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client() -> Mistral:
    """Initialize Mistral client."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("❌ Error: MISTRAL_API_KEY not set")
        print("   Make sure it's in your .env file")
        sys.exit(1)
    
    return Mistral(api_key=api_key)


def get_eval_dir(difficulty: float) -> Path:
    """Get evaluation directory for baseline results."""
    model_name = MODEL_ID.replace("-", "_")
    diff_str = str(difficulty).replace(".", "_")
    eval_dir = EVAL_DIR / f"{model_name}_difficulty_{diff_str}"
    eval_dir.mkdir(parents=True, exist_ok=True)
    return eval_dir


def load_baseline_questions(difficulty: float) -> List[Dict]:
    """Load baseline questions for a difficulty level."""
    if difficulty == int(difficulty):
        diff_str = f"difficulty_{int(difficulty)}"
    else:
        diff_str = f"difficulty_{difficulty}"
    
    diff_dir = DATA_DIR / diff_str
    baseline_file = diff_dir / f"{diff_str}_baseline_questions.json"
    
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline questions file not found: {baseline_file}")
    
    with open(baseline_file, 'r') as f:
        questions = json.load(f)
    
    return questions


def load_completed_ids(eval_dir: Path) -> set:
    """Load set of completed question IDs."""
    results_file = eval_dir / "results.json"
    completed = set()
    
    if results_file.exists():
        with open(results_file, 'r') as f:
            results = json.load(f)
            for result in results:
                if result.get("question_id"):
                    completed.add(result["question_id"])
    
    return completed


def load_results(eval_dir: Path) -> List[Dict]:
    """Load existing results."""
    results_file = eval_dir / "results.json"
    if results_file.exists():
        with open(results_file, 'r') as f:
            return json.load(f)
    return []


def save_results(eval_dir: Path, results: List[Dict]):
    """Save results to file."""
    results_file = eval_dir / "results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)


def save_summary(eval_dir: Path, difficulty: float, results: List[Dict]):
    """Save evaluation summary."""
    correct = sum(1 for r in results if r.get("is_correct"))
    total = len(results)
    errors = sum(1 for r in results if r.get("api_error"))
    
    summary = {
        "model": MODEL_ID,
        "difficulty": difficulty,
        "evaluation_type": "baseline",
        "statistics": {
            "total_questions": total,
            "correct": correct,
            "incorrect": total - correct - errors,
            "errors": errors,
            "accuracy_percentage": correct / total * 100 if total > 0 else 0
        },
        "generated_at": datetime.now().isoformat()
    }
    
    summary_file = eval_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary


# ============================================================================
# EVALUATION FUNCTIONS
# ============================================================================

def evaluate_single(
    client: Mistral,
    question_data: Dict,
    retries: int = MAX_RETRIES
) -> Dict:
    """Evaluate a single baseline question with retry logic."""
    prompt = create_evaluation_prompt(question_data["original_question"])
    
    result = {
        "question_id": question_data["question_id"],
        "domain": question_data.get("domain", ""),
        "difficulty": question_data.get("difficulty"),
        "difficulty_category": question_data.get("difficulty_category", ""),
        "ground_truth": question_data["correct_answer"],
        "question": question_data["original_question"],
        "model_answer": "",
        "is_correct": False,
        "match_type": "no_match",
        "input_tokens": None,
        "output_tokens": None,
        "api_success": False,
        "api_error": None,
        "model": MODEL_ID,
        "timestamp": datetime.now().isoformat()
    }
    
    delay = DELAY_BETWEEN_REQUESTS
    
    for attempt in range(retries):
        try:
            # Make API call
            response = client.chat.complete(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0,
            )
            
            # Extract answer
            model_answer = response.choices[0].message.content.strip()
            
            # Clean up answer
            for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
                model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
            model_answer = model_answer.strip().rstrip('.')
            
            result["model_answer"] = model_answer
            result["api_success"] = True
            
            # Token usage
            if response.usage:
                result["input_tokens"] = response.usage.prompt_tokens
                result["output_tokens"] = response.usage.completion_tokens
            
            # Compare answers
            is_correct, match_type = compare_answers(model_answer, question_data["correct_answer"])
            result["is_correct"] = is_correct
            result["match_type"] = match_type
            
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            
            if 'rate' in error_str or 'limit' in error_str or '429' in error_str:
                if attempt < retries - 1:
                    sleep_time = delay * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 5)
                    print(f"   ⏳ Rate limited. Waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    result["api_error"] = f"Rate limit exceeded after {retries} retries"
            
            elif '402' in error_str or 'payment' in error_str:
                result["api_error"] = f"Quota/payment error: {str(e)[:100]}"
                return result
            
            else:
                if attempt < retries - 1:
                    sleep_time = delay * (BACKOFF_FACTOR ** attempt)
                    print(f"   ⚠️  Error: {str(e)[:50]}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    result["api_error"] = str(e)[:200]
    
    return result


def run_evaluation(
    client: Mistral,
    difficulty: float,
    test_count: Optional[int] = None,
):
    """Run baseline evaluation on original questions."""
    eval_dir = get_eval_dir(difficulty)
    
    print(f"\n📊 Evaluating {MODEL_ID} baseline on difficulty {difficulty}")
    print(f"   Output dir: {eval_dir}")
    
    # Load baseline questions
    questions = load_baseline_questions(difficulty)
    print(f"   Total baseline questions: {len(questions)}")
    
    # Load existing results for resume
    existing_results = load_results(eval_dir)
    completed_ids = set(r["question_id"] for r in existing_results)
    
    # Filter to remaining questions
    remaining = [q for q in questions if q["question_id"] not in completed_ids]
    
    if len(completed_ids) > 0:
        print(f"   ⏭️  Resuming: {len(completed_ids)} already done, {len(remaining)} remaining")
    
    # Limit for testing
    if test_count:
        remaining = remaining[:test_count]
        print(f"   🧪 Test mode: {test_count} questions")
    
    if not remaining:
        print("   ✅ All questions already evaluated!")
        # Still save summary
        all_results = load_results(eval_dir)
        summary = save_summary(eval_dir, difficulty, all_results)
        print(f"\n   📋 Final accuracy: {summary['statistics']['accuracy_percentage']:.1f}%")
        return
    
    # Estimate time
    est_time_mins = len(remaining) * DELAY_BETWEEN_REQUESTS / 60
    print(f"\n   ⏱️  Estimated time: {est_time_mins:.1f} minutes")
    print(f"   🔄 Rate: {REQUESTS_PER_MINUTE} requests/minute")
    
    # Confirm for full runs
    if not test_count and len(remaining) > 20:
        print("\n   Press Enter to continue or Ctrl+C to cancel...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n   Cancelled.")
            return
    
    # Evaluate
    correct = 0
    errors = 0
    results = existing_results.copy()
    start_time = time.time()
    
    print(f"\n   {'#':>4} | {'Q_ID':>5} | {'Answer':>15} | {'Truth':>15} | Status")
    print("   " + "-" * 70)
    
    for i, q in enumerate(remaining, 1):
        result = evaluate_single(client, q)
        results.append(result)
        
        # Save immediately (crash-proof)
        save_results(eval_dir, results)
        
        if result["is_correct"]:
            correct += 1
            status = "✅"
        elif result["api_error"]:
            errors += 1
            status = "⚠️ Error"
        else:
            status = "❌"
        
        # Progress display
        elapsed = time.time() - start_time
        rate = i / elapsed * 60 if elapsed > 0 else 0
        eta = (len(remaining) - i) / (rate / 60) / 60 if rate > 0 else 0
        
        ans_display = str(result['model_answer'])[:15]
        truth_display = str(result['ground_truth'])[:15]
        
        print(f"   {i:>4} | {result['question_id']:>5} | {ans_display:>15} | {truth_display:>15} | {status}")
        
        # Rate limiting
        if i < len(remaining):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Final summary
    all_results = load_results(eval_dir)
    total_correct = sum(1 for r in all_results if r.get("is_correct"))
    total = len(all_results)
    accuracy = total_correct / total * 100 if total > 0 else 0
    
    print(f"\n   {'='*70}")
    print(f"   📊 Baseline Results: {total_correct}/{total} correct ({accuracy:.1f}%)")
    if errors > 0:
        print(f"   ⚠️  API Errors: {errors}")
    
    # Save summary
    summary = save_summary(eval_dir, difficulty, all_results)
    
    print(f"\n   📁 Results saved to: {eval_dir}")
    print(f"   📋 Summary saved to: {eval_dir}/summary.json")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Mistral on baseline (original) questions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 5 questions first
  %(prog)s --difficulty 1.0 --test 5
  
  # Full evaluation for difficulty 1.0
  %(prog)s --difficulty 1.0
  
  # Full evaluation for difficulty 1.5
  %(prog)s --difficulty 1.5

This establishes baseline accuracy before comparing with distorted results.
        """
    )
    
    parser.add_argument("--difficulty", type=float, required=True,
                       choices=[1.0, 1.5],
                       help="Difficulty level")
    parser.add_argument("--test", type=int, metavar="N",
                       help="Test with N questions only")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Mistral Baseline Evaluation - {MODEL_ID}")
    print("=" * 60)
    
    client = get_client()
    
    try:
        run_evaluation(
            client=client,
            difficulty=args.difficulty,
            test_count=args.test,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Progress saved! Run again to resume.")


if __name__ == "__main__":
    main()
