#!/usr/bin/env python3
"""
Gemini Distortion Evaluation Script

Evaluates Google Gemini models on distorted questions.
Features robust checkpointing and rate limiting for free tier.

Key Features:
- Saves progress after EVERY question (crash-proof)
- Rate limiting optimized for Gemini free tier (5 RPM)
- Resume from any interruption instantly
- Real-time progress display

Usage:
    # Evaluate difficulty 1.0 (Day 1)
    python evaluate_gemini.py --difficulty 1.0
    
    # Evaluate difficulty 1.5 (Day 2)
    python evaluate_gemini.py --difficulty 1.5
    
    # Resume interrupted evaluation
    python evaluate_gemini.py --difficulty 1.0
    
    # Test with small sample first
    python evaluate_gemini.py --difficulty 1.0 --test 5

Environment:
    GOOGLE_API_KEY: Your Google AI API key (required)
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

# Try to import Google Generative AI
try:
    import google.generativeai as genai
except ImportError:
    print("❌ Error: google-generativeai package not installed")
    print("   Install with: pip install google-generativeai")
    sys.exit(1)

from omnimath_distortion_workflow.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
)
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
EVAL_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "distortion_results"

# Model configuration
MODEL_ID = "gemini-2.5-flash"  # Free tier model with higher quota

# Rate limiting for Gemini free tier
# Conservative: 5 RPM = 12 seconds between requests
# With buffer for safety
REQUESTS_PER_MINUTE = 5
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE + 1  # ~13 seconds
MAX_RETRIES = 5
BACKOFF_FACTOR = 2


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client():
    """Initialize Gemini client."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not set")
        print("   Make sure it's in your .env file")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_ID)


def get_eval_dir(difficulty: float) -> Path:
    """Get evaluation directory for model and difficulty."""
    model_name = MODEL_ID.replace("-", "_").replace(".", "_")
    diff_str = str(difficulty).replace(".", "_")
    eval_dir = EVAL_DIR / f"{model_name}_difficulty_{diff_str}"
    eval_dir.mkdir(parents=True, exist_ok=True)
    return eval_dir


def load_distortions(difficulty: float) -> List[Dict]:
    """Load distorted questions for a difficulty level."""
    # Handle folder naming: difficulty_1 (not difficulty_1.0) but difficulty_1.5
    if difficulty == int(difficulty):
        diff_str = f"difficulty_{int(difficulty)}"
    else:
        diff_str = f"difficulty_{difficulty}"
    
    diff_dir = DATA_DIR / diff_str
    distortions_file = diff_dir / f"{diff_str}_distortions.json"
    
    if not distortions_file.exists():
        raise FileNotFoundError(f"Distortions file not found: {distortions_file}")
    
    with open(distortions_file, 'r') as f:
        all_entries = json.load(f)
    
    distortions = []
    
    for entry in all_entries:
        # Format 1: Flat format - miu is directly in the entry
        if 'miu' in entry and entry.get('miu') is not None:
            distortions.append(entry)
        
        # Format 2: Nested format - distortions array contains miu entries
        elif 'distortions' in entry and isinstance(entry['distortions'], list):
            for dist in entry['distortions']:
                if 'miu' in dist and 'distorted_question' in dist:
                    flat_entry = {
                        'question_id': entry.get('question_id'),
                        'original_question': entry.get('original_question'),
                        'correct_answer': entry.get('correct_answer'),
                        'difficulty': entry.get('difficulty'),
                        'difficulty_category': entry.get('difficulty_category', 'easy'),
                        'domain': entry.get('domain', ''),
                        'distorted_question': dist.get('distorted_question'),
                        'miu': dist.get('miu'),
                        'miu_description': dist.get('miu_description', ''),
                    }
                    distortions.append(flat_entry)
    
    return distortions


def load_completed_ids(eval_dir: Path) -> set:
    """Load set of completed question IDs."""
    results_file = eval_dir / "results.jsonl"
    completed = set()
    
    if results_file.exists():
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        result = json.loads(line)
                        if result.get("custom_id"):
                            completed.add(result["custom_id"])
                    except:
                        pass
    
    return completed


def append_result(eval_dir: Path, result: Dict):
    """Append a single result immediately (crash-proof)."""
    results_file = eval_dir / "results.jsonl"
    with open(results_file, 'a') as f:
        f.write(json.dumps(result) + '\n')
        f.flush()
        os.fsync(f.fileno())


def load_all_results(eval_dir: Path) -> List[Dict]:
    """Load all results."""
    results_file = eval_dir / "results.jsonl"
    results = []
    if results_file.exists():
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


# ============================================================================
# EVALUATION FUNCTIONS
# ============================================================================

def evaluate_single(
    model,
    question_data: Dict,
    retries: int = MAX_RETRIES
) -> Dict:
    """Evaluate a single question with retry logic."""
    custom_id = generate_custom_id(question_data["question_id"], question_data["miu"])
    prompt = create_evaluation_prompt(question_data["distorted_question"])
    
    result = {
        "custom_id": custom_id,
        "question_id": question_data["question_id"],
        "miu": question_data["miu"],
        "miu_description": question_data.get("miu_description", ""),
        "domain": question_data.get("domain", ""),
        "difficulty": question_data.get("difficulty"),
        "difficulty_category": question_data.get("difficulty_category", ""),
        "ground_truth": question_data["correct_answer"],
        "question": question_data["distorted_question"],
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
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0,
                )
            )
            
            # Extract answer
            model_answer = response.text.strip()
            
            # Clean up answer
            for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
                model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
            model_answer = model_answer.strip().rstrip('.')
            
            result["model_answer"] = model_answer
            result["api_success"] = True
            
            # Token usage (if available)
            if hasattr(response, 'usage_metadata'):
                result["input_tokens"] = getattr(response.usage_metadata, 'prompt_token_count', None)
                result["output_tokens"] = getattr(response.usage_metadata, 'candidates_token_count', None)
            
            # Compare answers
            is_correct, match_type = compare_answers(model_answer, question_data["correct_answer"])
            result["is_correct"] = is_correct
            result["match_type"] = match_type
            
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit errors
            if 'rate' in error_str or 'quota' in error_str or '429' in error_str:
                if attempt < retries - 1:
                    sleep_time = delay * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 5)
                    print(f"   ⏳ Rate limited. Waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    result["api_error"] = f"Rate limit exceeded after {retries} retries"
            
            # Check for resource exhausted
            elif 'resource' in error_str or 'exhausted' in error_str:
                if attempt < retries - 1:
                    sleep_time = 60 + random.uniform(0, 30)  # Wait longer
                    print(f"   ⏳ Resource exhausted. Waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    result["api_error"] = f"Resource exhausted after {retries} retries"
            
            # Other errors
            else:
                if attempt < retries - 1:
                    sleep_time = delay * (BACKOFF_FACTOR ** attempt)
                    print(f"   ⚠️  Error: {str(e)[:50]}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    result["api_error"] = str(e)[:200]
    
    return result


def run_evaluation(
    model,
    difficulty: float,
    test_count: Optional[int] = None,
    miu_filter: Optional[List[float]] = None,
):
    """Run evaluation on distorted questions."""
    eval_dir = get_eval_dir(difficulty)
    
    print(f"\n📊 Evaluating {MODEL_ID} on difficulty {difficulty}")
    print(f"   Output dir: {eval_dir}")
    
    # Load distortions
    distortions = load_distortions(difficulty)
    print(f"   Total distortions: {len(distortions)}")
    
    # Filter by miu if specified
    if miu_filter:
        distortions = [d for d in distortions if d["miu"] in miu_filter]
        print(f"   Filtered to miu levels {miu_filter}: {len(distortions)} questions")
    
    # Load completed IDs for resume
    completed_ids = load_completed_ids(eval_dir)
    distortions = [d for d in distortions 
                  if generate_custom_id(d["question_id"], d["miu"]) not in completed_ids]
    if len(completed_ids) > 0:
        print(f"   ⏭️  Resuming: {len(completed_ids)} already done, {len(distortions)} remaining")
    
    # Limit for testing
    if test_count:
        distortions = distortions[:test_count]
        print(f"   🧪 Test mode: {test_count} questions")
    
    if not distortions:
        print("   ✅ All questions already evaluated!")
        return
    
    # Estimate time
    est_time_mins = len(distortions) * DELAY_BETWEEN_REQUESTS / 60
    print(f"\n   ⏱️  Estimated time: {est_time_mins:.1f} minutes (~{est_time_mins/60:.1f} hours)")
    print(f"   🔄 Rate: {REQUESTS_PER_MINUTE} requests/minute")
    print(f"   💡 Free tier - no cost!")
    
    # Confirm for full runs
    if not test_count and len(distortions) > 20:
        print("\n   Press Enter to continue or Ctrl+C to cancel...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n   Cancelled.")
            return
    
    # Evaluate
    correct = 0
    errors = 0
    start_time = time.time()
    
    print(f"\n   {'#':>4} | {'Q_ID':>5} | {'μ':>3} | {'Answer':>12} | {'Truth':>12} | Status")
    print("   " + "-" * 65)
    
    for i, dist in enumerate(distortions, 1):
        result = evaluate_single(model, dist)
        
        # Save immediately (crash-proof)
        append_result(eval_dir, result)
        
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
        rate = i / elapsed * 60 if elapsed > 0 else 0  # per minute
        eta = (len(distortions) - i) / (rate / 60) / 60 if rate > 0 else 0  # hours
        
        ans_display = str(result['model_answer'])[:12]
        truth_display = str(result['ground_truth'])[:12]
        
        print(f"   {i:>4} | {result['question_id']:>5} | {result['miu']:>3} | {ans_display:>12} | {truth_display:>12} | {status} (ETA: {eta:.1f}h)")
        
        # Rate limiting - wait between requests
        if i < len(distortions):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Summary
    total = len(distortions)
    accuracy = correct / total * 100 if total > 0 else 0
    
    print(f"\n   {'='*65}")
    print(f"   📊 Results: {correct}/{total} correct ({accuracy:.1f}%)")
    if errors > 0:
        print(f"   ⚠️  API Errors: {errors}")
    
    # Save summary
    all_results = load_all_results(eval_dir)
    save_summary(eval_dir, difficulty, all_results)
    
    print(f"\n   📁 Results saved to: {eval_dir}")


def save_summary(eval_dir: Path, difficulty: float, results: List[Dict]):
    """Save evaluation summary."""
    summary = {
        "model": MODEL_ID,
        "difficulty": difficulty,
        "total_questions": len(results),
        "correct": sum(1 for r in results if r.get("is_correct")),
        "accuracy": sum(1 for r in results if r.get("is_correct")) / len(results) * 100 if results else 0,
        "errors": sum(1 for r in results if r.get("api_error")),
        "by_miu": {},
        "updated_at": datetime.now().isoformat()
    }
    
    # Group by miu
    miu_results = {}
    for r in results:
        miu = r.get("miu")
        if miu not in miu_results:
            miu_results[miu] = {"correct": 0, "total": 0}
        miu_results[miu]["total"] += 1
        if r.get("is_correct"):
            miu_results[miu]["correct"] += 1
    
    for miu, stats in sorted(miu_results.items()):
        summary["by_miu"][str(miu)] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        }
    
    summary_file = eval_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n   📋 Summary by μ level:")
    for miu, stats in summary["by_miu"].items():
        print(f"      μ={miu}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1f}%)")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Gemini on distorted questions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate difficulty 1.0 (Day 1)
  %(prog)s --difficulty 1.0
  
  # Evaluate difficulty 1.5 (Day 2)
  %(prog)s --difficulty 1.5
  
  # Test with 5 questions first
  %(prog)s --difficulty 1.0 --test 5
  
  # Evaluate specific miu levels
  %(prog)s --difficulty 1.0 --miu 0.2,0.9

Note: Rate limited to ~5 requests/minute for free tier.
      400 questions will take ~1.5 hours.
        """
    )
    
    parser.add_argument("--difficulty", type=float, required=True,
                       choices=[1.0, 1.5],
                       help="Difficulty level")
    parser.add_argument("--test", type=int, metavar="N",
                       help="Test with N questions only")
    parser.add_argument("--miu", type=str,
                       help="Comma-separated miu levels to evaluate (e.g., 0.2,0.5)")
    
    args = parser.parse_args()
    
    # Parse miu filter
    miu_filter = None
    if args.miu:
        miu_filter = [float(m.strip()) for m in args.miu.split(",")]
    
    print("=" * 60)
    print(f"Gemini Distortion Evaluation - {MODEL_ID}")
    print("=" * 60)
    
    model = get_client()
    
    try:
        run_evaluation(
            model=model,
            difficulty=args.difficulty,
            test_count=args.test,
            miu_filter=miu_filter,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Progress saved! Run again to resume.")


if __name__ == "__main__":
    main()
