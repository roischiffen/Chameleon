#!/usr/bin/env python3
"""
Direct GPT-5 Evaluation Script for OmniMath

Makes synchronous API calls to GPT-5 instead of using batch API.
Faster turnaround, continuous workflow, slightly higher cost (~$1 more).

Usage:
    # Test with 5 samples first (RECOMMENDED)
    python omnimath_distortion_workflow/flows/evaluate_direct.py --test 5
    
    # Test with 10 samples from specific batch
    python omnimath_distortion_workflow/flows/evaluate_direct.py --test 10 --batch batch1
    
    # Run full evaluation (after testing)
    python omnimath_distortion_workflow/flows/evaluate_direct.py --full
    
    # Resume interrupted evaluation
    python omnimath_distortion_workflow/flows/evaluate_direct.py --resume

Environment:
    OPENAI_API_KEY: Your OpenAI API key (required)
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try multiple .env locations
    env_paths = [
        project_root / ".env",
        project_root / "venv" / "bin" / ".env",
        Path.home() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"📁 Loaded .env from: {env_path}")
            break
except ImportError:
    pass  # dotenv not installed, will use environment variables directly

from omnimath_distortion_workflow.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
    parse_custom_id
)
from omnimath_distortion_workflow.modules.batch_converter import load_distortion_batch
from omnimath_distortion_workflow.modules.results_parser import extract_token_usage
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# Try to import openai
try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)


# Paths
DATA_BATCHES_DIR = project_root / "omnimath_distortion_workflow" / "data" / "batches"
EVAL_RESULTS_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "results"
PROGRESS_FILE = EVAL_RESULTS_DIR / "evaluation_progress.json"


# Configuration
DEFAULT_MODEL = "gpt-4o"  # Fallback if gpt-5 not available
GPT5_MODEL = "gpt-4o"     # Testing with GPT-4o (no reasoning token overhead)
REASONING_EFFORT = "minimal"  # Only used for GPT-5, ignored by GPT-4o
# NOTE: max_completion_tokens includes BOTH reasoning tokens AND output tokens
# With minimal reasoning, most tokens go to the answer
MAX_COMPLETION_TOKENS = 150  # Small - we only need the final answer
RATE_LIMIT_DELAY = 0.3    # Faster with minimal reasoning


def get_client() -> openai.OpenAI:
    """Get OpenAI client with API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def check_model_availability(client: openai.OpenAI) -> str:
    """Check which model is available and return the best option."""
    print("\n🔍 Checking model availability...")
    
    # Try configured model first
    try:
        # Use appropriate parameter based on model
        if "gpt-5" in GPT5_MODEL.lower():
            response = client.chat.completions.create(
                model=GPT5_MODEL,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_completion_tokens=5
            )
        else:
            response = client.chat.completions.create(
                model=GPT5_MODEL,
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5
            )
        print(f"   ✅ {GPT5_MODEL} is available!")
        return GPT5_MODEL
    except Exception as e:
        print(f"   ⚠️  {GPT5_MODEL} not available: {e}")
    
    # Fall back to gpt-4o
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5
        )
        print(f"   ✅ Falling back to {DEFAULT_MODEL}")
        return DEFAULT_MODEL
    except Exception as e:
        print(f"   ❌ {DEFAULT_MODEL} also not available: {e}")
        sys.exit(1)


def load_all_questions(
    difficulty: Optional[str] = None,
    baseline_only: bool = False,
    distorted_only: bool = False,
    batches: Optional[List[int]] = None,
    max_difficulty: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Load questions from batches with optional filters.
    
    Args:
        difficulty: Filter by difficulty_category ('easy', 'medium', or None for all)
        baseline_only: If True, only load μ=0.0 (original) questions
        distorted_only: If True, only load μ>0 (distorted) questions
        batches: List of batch numbers to include (e.g., [1, 2, 5, 6, 7])
        max_difficulty: Maximum numeric difficulty value (e.g., 1.5 for only easiest)
    
    Returns:
        List of question dicts
    """
    all_questions = []
    seen_ids = set()
    
    for batch_dir in sorted(DATA_BATCHES_DIR.iterdir()):
        if not batch_dir.is_dir() or not batch_dir.name.startswith("batch"):
            continue
        
        # Filter by batch number if specified
        if batches:
            try:
                batch_num = int(batch_dir.name.replace("batch", ""))
                if batch_num not in batches:
                    continue
            except ValueError:
                continue
        
        distortions = load_distortion_batch(batch_dir)
        
        for entry in distortions:
            qid = entry["question_id"]
            miu = entry["miu"]
            diff_cat = entry.get("difficulty_category", "")
            diff_num = entry.get("difficulty", 999)  # Default high if missing
            
            # Filter by difficulty category
            if difficulty and diff_cat != difficulty:
                continue
            
            # Filter by max numeric difficulty
            if max_difficulty is not None and diff_num > max_difficulty:
                continue
            
            # Add baseline (μ=0.0) only once per question
            if not distorted_only:
                baseline_key = f"{qid}_0.0"
                if baseline_key not in seen_ids:
                    all_questions.append({
                        "question_id": qid,
                        "miu": 0.0,
                        "question": entry["original_question"],
                        "correct_answer": entry["correct_answer"],
                        "miu_description": "Baseline (Original)",
                        "domain": entry.get("domain", ""),
                        "difficulty": entry.get("difficulty"),
                        "difficulty_category": diff_cat,
                        "batch": batch_dir.name
                    })
                    seen_ids.add(baseline_key)
            
            # Add distorted version
            if not baseline_only:
                distorted_key = f"{qid}_{miu}"
                if distorted_key not in seen_ids:
                    all_questions.append({
                        "question_id": qid,
                        "miu": miu,
                        "question": entry["distorted_question"],
                        "correct_answer": entry["correct_answer"],
                        "miu_description": entry.get("miu_description", ""),
                        "domain": entry.get("domain", ""),
                        "difficulty": entry.get("difficulty"),
                        "difficulty_category": diff_cat,
                        "batch": batch_dir.name
                    })
                    seen_ids.add(distorted_key)
    
    return all_questions


def evaluate_single(client: openai.OpenAI, model: str, question_data: Dict) -> Dict[str, Any]:
    """
    Evaluate a single question with GPT-5/GPT-4o.
    
    Returns result dict with model answer, correctness, and token usage.
    """
    custom_id = generate_custom_id(question_data["question_id"], question_data["miu"])
    prompt = create_evaluation_prompt(question_data["question"])
    
    result = {
        "custom_id": custom_id,
        "question_id": question_data["question_id"],
        "miu": question_data["miu"],
        "miu_description": question_data["miu_description"],
        "domain": question_data["domain"],
        "difficulty": question_data["difficulty"],
        "difficulty_category": question_data["difficulty_category"],
        "ground_truth": question_data["correct_answer"],
        "question": question_data["question"],
        "model_answer": "",
        "is_correct": False,
        "match_type": "no_match",
        "input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None,
        "api_success": False,
        "api_error": None,
        "model_used": model,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Build request based on model
        request_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        # GPT-5 family uses reasoning_effort and max_completion_tokens
        # Note: GPT-5/reasoning models don't support temperature parameter
        if "gpt-5" in model.lower():
            request_params["reasoning_effort"] = REASONING_EFFORT
            request_params["max_completion_tokens"] = MAX_COMPLETION_TOKENS
        else:
            # GPT-4o and other models use max_tokens and temperature
            request_params["max_tokens"] = MAX_COMPLETION_TOKENS
            request_params["temperature"] = 0  # Deterministic output
        
        # Make API call
        response = client.chat.completions.create(**request_params)
        
        # Extract answer
        model_answer = response.choices[0].message.content.strip()
        
        # Clean up answer (remove common prefixes)
        import re
        for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
            model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
        model_answer = model_answer.strip().rstrip('.')
        
        result["model_answer"] = model_answer
        result["api_success"] = True
        
        # Extract token usage
        if response.usage:
            result["input_tokens"] = getattr(response.usage, 'prompt_tokens', None) or getattr(response.usage, 'input_tokens', None)
            result["output_tokens"] = getattr(response.usage, 'completion_tokens', None) or getattr(response.usage, 'output_tokens', None)
            
            # Try to get reasoning tokens
            if hasattr(response.usage, 'completion_tokens_details'):
                details = response.usage.completion_tokens_details
                if details:
                    result["reasoning_tokens"] = getattr(details, 'reasoning_tokens', None)
        
        # Compare answer
        is_correct, match_type = compare_answers(model_answer, question_data["correct_answer"])
        result["is_correct"] = is_correct
        result["match_type"] = match_type
        
    except Exception as e:
        result["api_error"] = str(e)
    
    return result


def run_test(
    client: openai.OpenAI, 
    model: str, 
    num_samples: int,
    difficulty: Optional[str] = None,
    baseline_only: bool = False,
    distorted_only: bool = False,
    batches: Optional[List[int]] = None,
    question_ids: Optional[List[int]] = None,
    max_difficulty: Optional[float] = None
) -> List[Dict]:
    """
    Run a test evaluation with a small sample of questions.
    
    Args:
        client: OpenAI client
        model: Model to use
        num_samples: Number of samples to test
        difficulty: Filter by difficulty ('easy', 'medium', or None)
        baseline_only: Only test μ=0.0 questions
        distorted_only: Only test μ>0 questions
        batches: List of batch numbers to include
        max_difficulty: Max numeric difficulty value (e.g., 1.5)
        question_ids: Optional list of specific question IDs to test
    
    Returns:
        List of results
    """
    mode_desc = []
    if difficulty:
        mode_desc.append(f"difficulty={difficulty}")
    if baseline_only:
        mode_desc.append("baseline-only")
    if distorted_only:
        mode_desc.append("distorted-only")
    if batches:
        mode_desc.append(f"batches={batches}")
    
    mode_str = f" ({', '.join(mode_desc)})" if mode_desc else ""
    print(f"\n🧪 Running test evaluation with {num_samples} samples{mode_str}...")
    
    # Load questions with filters
    all_questions = load_all_questions(
        difficulty=difficulty,
        baseline_only=baseline_only,
        distorted_only=distorted_only,
        batches=batches,
        max_difficulty=max_difficulty
    )
    print(f"   Total questions available: {len(all_questions)}")
    
    # Filter by specific question IDs if provided
    if question_ids:
        sample = [q for q in all_questions if q["question_id"] in question_ids]
        print(f"   Filtered to {len(sample)} questions by ID")
    else:
        # Sample questions
        random.seed(42)  # Reproducible sampling
        sample = random.sample(all_questions, min(num_samples, len(all_questions)))
    
    # Sort by question_id and miu for readability
    sample.sort(key=lambda x: (x["question_id"], x["miu"]))
    
    print(f"   Sampled {len(sample)} questions")
    print(f"   μ distribution: {dict(sorted({q['miu']: sum(1 for x in sample if x['miu'] == q['miu']) for q in sample}.items()))}")
    
    results = []
    correct = 0
    
    print(f"\n   {'#':>3} | {'Q_ID':>6} | {'μ':>3} | {'Answer':>12} | {'Correct':>12} | {'Match':>8} | Status")
    print("   " + "-" * 75)
    
    for i, q in enumerate(sample, 1):
        result = evaluate_single(client, model, q)
        results.append(result)
        
        if result["is_correct"]:
            correct += 1
        
        status = "✅" if result["is_correct"] else ("❌ API Error" if result["api_error"] else "❌ Wrong")
        print(f"   {i:>3} | {result['question_id']:>6} | {result['miu']:>3} | {result['model_answer'][:12]:>12} | {result['ground_truth'][:12]:>12} | {result['match_type']:>8} | {status}")
        
        # Rate limiting
        if i < len(sample):
            time.sleep(RATE_LIMIT_DELAY)
    
    # Summary
    print(f"\n   {'='*75}")
    print(f"   Test Results: {correct}/{len(sample)} correct ({correct/len(sample)*100:.1f}% accuracy)")
    
    api_errors = sum(1 for r in results if r["api_error"])
    if api_errors:
        print(f"   ⚠️  API Errors: {api_errors}")
        for r in results:
            if r["api_error"]:
                print(f"      - Q{r['question_id']} μ={r['miu']}: {r['api_error'][:50]}...")
    
    # Token usage
    input_tokens = sum(r["input_tokens"] or 0 for r in results)
    output_tokens = sum(r["output_tokens"] or 0 for r in results)
    print(f"\n   Token usage: {input_tokens:,} input, {output_tokens:,} output")
    
    return results


def run_full_evaluation(client: openai.OpenAI, model: str, resume: bool = False) -> None:
    """
    Run full evaluation on all 2,000 questions.
    
    Args:
        client: OpenAI client
        model: Model to use
        resume: Whether to resume from previous progress
    """
    print("\n🚀 Running FULL evaluation...")
    
    # Load all questions
    all_questions = load_all_questions()
    print(f"   Total questions: {len(all_questions)}")
    
    # Check for existing progress
    completed_ids = set()
    results = []
    
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = EVAL_RESULTS_DIR / "direct_eval_results.jsonl"
    
    if resume and results_file.exists():
        print(f"   📂 Loading existing progress from {results_file.name}...")
        with open(results_file, 'r') as f:
            for line in f:
                result = json.loads(line)
                results.append(result)
                completed_ids.add(result["custom_id"])
        print(f"   ✅ Loaded {len(completed_ids)} completed evaluations")
    
    # Filter out completed questions
    remaining = [q for q in all_questions 
                 if generate_custom_id(q["question_id"], q["miu"]) not in completed_ids]
    
    print(f"   Remaining: {len(remaining)} questions")
    
    if not remaining:
        print("   ✅ All evaluations already complete!")
        return
    
    # Estimate time and cost
    est_time_mins = len(remaining) * (RATE_LIMIT_DELAY + 0.5) / 60
    est_cost = len(remaining) * 0.001  # ~$0.001 per request estimate
    
    print(f"\n   ⏱️  Estimated time: {est_time_mins:.0f} minutes")
    print(f"   💰 Estimated cost: ~${est_cost:.2f}")
    
    # Confirm
    print("\n   Press Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n   Cancelled.")
        return
    
    # Open file for appending results
    with open(results_file, 'a') as f:
        correct = 0
        start_time = time.time()
        
        for i, q in enumerate(remaining, 1):
            result = evaluate_single(client, model, q)
            results.append(result)
            
            # Save immediately (resumable)
            f.write(json.dumps(result) + '\n')
            f.flush()
            
            if result["is_correct"]:
                correct += 1
            
            # Progress
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(remaining) - i) / rate / 60 if rate > 0 else 0
            
            status = "✅" if result["is_correct"] else "❌"
            print(f"\r   [{i:>4}/{len(remaining)}] Q{result['question_id']} μ={result['miu']} {status} | "
                  f"Accuracy: {correct/i*100:.1f}% | ETA: {eta:.0f}m", end="")
            
            # Rate limiting
            if i < len(remaining):
                time.sleep(RATE_LIMIT_DELAY)
    
    print(f"\n\n   ✅ Evaluation complete!")
    print(f"   Results saved to: {results_file}")
    print(f"   Total: {len(results)} | Correct: {sum(1 for r in results if r['is_correct'])}")


def save_test_results(results: List[Dict], filename: str = "test_results.json") -> None:
    """Save test results to file."""
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVAL_RESULTS_DIR / filename
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n   💾 Test results saved to: {output_path}")


def run_baseline_comparison(client: openai.OpenAI, model: str, question_ids: List[int]) -> None:
    """
    Run baseline (μ=0.0) evaluation for specific questions and compare with distorted results.
    
    Args:
        client: OpenAI client
        model: Model to use
        question_ids: List of question IDs to evaluate at baseline
    """
    print(f"\n📊 Running BASELINE comparison for {len(question_ids)} questions...")
    
    # Load all questions
    all_questions = load_all_questions()
    
    # Get baseline (μ=0.0) versions of the specified questions
    baseline_questions = [q for q in all_questions 
                         if q["question_id"] in question_ids and q["miu"] == 0.0]
    
    print(f"   Found {len(baseline_questions)} baseline questions")
    
    if not baseline_questions:
        print("   ❌ No baseline questions found!")
        return
    
    # Sort by question_id
    baseline_questions.sort(key=lambda x: x["question_id"])
    
    results = []
    correct = 0
    
    print(f"\n   {'#':>3} | {'Q_ID':>6} | {'Diff':>6} | {'Answer':>12} | {'Correct':>12} | {'Match':>10} | Status")
    print("   " + "-" * 80)
    
    for i, q in enumerate(baseline_questions, 1):
        result = evaluate_single(client, model, q)
        results.append(result)
        
        if result["is_correct"]:
            correct += 1
        
        diff_cat = result.get("difficulty_category", "?")[:6]
        status = "✅" if result["is_correct"] else ("⚠️ Text" if result["match_type"] == "text_answer" else "❌")
        
        print(f"   {i:>3} | {result['question_id']:>6} | {diff_cat:>6} | {str(result['model_answer'])[:12]:>12} | {str(result['ground_truth'])[:12]:>12} | {result['match_type']:>10} | {status}")
        
        time.sleep(RATE_LIMIT_DELAY)
    
    # Calculate accuracy (excluding text answers)
    non_text = [r for r in results if r["match_type"] != "text_answer"]
    correct_non_text = sum(1 for r in non_text if r["is_correct"])
    
    print(f"\n   {'='*80}")
    print(f"   Baseline Results: {correct}/{len(baseline_questions)} correct")
    if len(non_text) < len(baseline_questions):
        print(f"   (Excluding {len(baseline_questions) - len(non_text)} text answers: {correct_non_text}/{len(non_text)} = {correct_non_text/len(non_text)*100:.1f}%)")
    
    # Save baseline results
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    baseline_file = EVAL_RESULTS_DIR / "baseline_test_results.json"
    with open(baseline_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n   💾 Baseline results saved to: {baseline_file}")
    
    # Load distorted results for comparison
    distorted_file = EVAL_RESULTS_DIR / "test_results.json"
    if distorted_file.exists():
        print("\n   📊 Comparison with distorted results:")
        with open(distorted_file, 'r') as f:
            distorted_results = json.load(f)
        
        # Create comparison table
        print(f"\n   {'Q_ID':>6} | {'Diff':>6} | {'Baseline':>10} | {'Distorted (μ)':>15} | Analysis")
        print("   " + "-" * 70)
        
        for baseline_r in results:
            qid = baseline_r["question_id"]
            baseline_correct = "✅" if baseline_r["is_correct"] else ("⚠️" if baseline_r["match_type"] == "text_answer" else "❌")
            
            # Find distorted results for this question
            distorted_for_q = [r for r in distorted_results if r["question_id"] == qid]
            
            if distorted_for_q:
                # Show each distorted result
                for dist_r in distorted_for_q:
                    dist_correct = "✅" if dist_r["is_correct"] else ("⚠️" if dist_r.get("match_type") == "text_answer" else "❌")
                    miu = dist_r["miu"]
                    
                    # Analysis
                    if baseline_r["is_correct"] and not dist_r["is_correct"]:
                        analysis = "📉 Distortion broke it"
                    elif not baseline_r["is_correct"] and dist_r["is_correct"]:
                        analysis = "🎲 Lucky on distorted"
                    elif baseline_r["is_correct"] and dist_r["is_correct"]:
                        analysis = "✨ Robust"
                    else:
                        analysis = "💀 Hard question"
                    
                    diff_cat = baseline_r.get("difficulty_category", "?")[:6]
                    print(f"   {qid:>6} | {diff_cat:>6} | {baseline_correct:>10} | {dist_correct} (μ={miu})      | {analysis}")
            else:
                diff_cat = baseline_r.get("difficulty_category", "?")[:6]
                print(f"   {qid:>6} | {diff_cat:>6} | {baseline_correct:>10} | {'(no data)':>15} |")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Direct GPT evaluation for OmniMath",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test 5                           # Test 5 random samples
  %(prog)s --test 5 --difficulty easy         # Test 5 easy questions
  %(prog)s --test 10 --baseline-only          # Test 10 baseline (μ=0.0) questions
  %(prog)s --test 5 --difficulty easy --baseline-only  # 5 easy baselines
  %(prog)s --baseline                         # Baseline test for previous questions
  %(prog)s --full --difficulty easy           # Full eval on easy questions
  %(prog)s --full --batches 5,6,7             # Full eval on new batches only
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test", type=int, metavar="N",
                       help="Run test with N samples")
    group.add_argument("--baseline", action="store_true",
                       help="Run baseline (μ=0.0) test for comparison with previous results")
    group.add_argument("--full", action="store_true",
                       help="Run full evaluation")
    group.add_argument("--resume", action="store_true",
                       help="Resume interrupted evaluation")
    
    # New filtering options
    parser.add_argument("--difficulty", type=str, choices=["easy", "medium", "all"],
                        default="all", help="Filter by difficulty (default: all)")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Only test μ=0.0 original questions")
    parser.add_argument("--distorted-only", action="store_true",
                        help="Only test μ=0.1-0.9 distorted questions")
    parser.add_argument("--batches", type=str,
                        help="Comma-separated batch numbers (e.g., 1,2,5,6,7)")
    parser.add_argument("--max-difficulty", type=float, default=None,
                        help="Max numeric difficulty (e.g., 1.5 for easiest questions only)")
    
    # Model selection
    parser.add_argument("--model", type=str, choices=["gpt-4o", "gpt-5-mini", "gpt-5"],
                        default=None, help="Model to use (default: configured in script)")
    
    # Legacy option (deprecated)
    parser.add_argument("--batch", type=str,
                        help="(Deprecated) Use --batches instead")
    
    args = parser.parse_args()
    
    # Parse filter options
    difficulty = None if args.difficulty == "all" else args.difficulty
    baseline_only = getattr(args, 'baseline_only', False)
    distorted_only = getattr(args, 'distorted_only', False)
    max_difficulty = getattr(args, 'max_difficulty', None)
    batches = None
    if args.batches:
        batches = [int(b.strip()) for b in args.batches.split(",")]
    
    print("=" * 60)
    print("OmniMath Direct Evaluation")
    print("=" * 60)
    
    # Get client and check model
    client = get_client()
    if args.model:
        model = args.model
        print(f"\n🔍 Using specified model: {model}")
    else:
        model = check_model_availability(client)
    
    print(f"\n📋 Configuration:")
    print(f"   Model: {model}")
    print(f"   Reasoning effort: {REASONING_EFFORT}")
    print(f"   Rate limit delay: {RATE_LIMIT_DELAY}s")
    if difficulty:
        print(f"   Difficulty filter: {difficulty}")
    if baseline_only:
        print(f"   Mode: baseline-only (μ=0.0)")
    if distorted_only:
        print(f"   Mode: distorted-only (μ>0)")
    if batches:
        print(f"   Batches: {batches}")
    if max_difficulty is not None:
        print(f"   Max difficulty: {max_difficulty}")
    
    if args.test:
        results = run_test(client, model, args.test, 
                          difficulty=difficulty, 
                          baseline_only=baseline_only,
                          distorted_only=distorted_only,
                          batches=batches,
                          max_difficulty=max_difficulty)
        
        # Save results with difficulty label
        suffix = f"_{difficulty}" if difficulty else ""
        suffix += "_baseline" if baseline_only else ""
        suffix += "_distorted" if distorted_only else ""
        save_test_results(results, f"test_results{suffix}.json")
        
        print("\n" + "=" * 60)
        print("✅ Test complete! Review results above.")
        print("   If everything looks good, run with --full")
        print("   Or run --baseline to compare with original questions")
        print("=" * 60)
    
    elif args.baseline:
        # Get question IDs from previous test results
        test_file = EVAL_RESULTS_DIR / "test_results.json"
        if not test_file.exists():
            print(f"❌ No test results found at {test_file}")
            print("   Run --test first to create test results")
            return 1
        
        with open(test_file, 'r') as f:
            test_results = json.load(f)
        
        # Extract unique question IDs
        question_ids = list(set(r["question_id"] for r in test_results))
        print(f"Found {len(question_ids)} unique questions from previous test")
        
        run_baseline_comparison(client, model, question_ids)
        
        print("\n" + "=" * 60)
        print("✅ Baseline comparison complete!")
        print("=" * 60)
        
    elif args.full or args.resume:
        run_full_evaluation(client, model, resume=args.resume)
        
        print("\n" + "=" * 60)
        print("✅ Full evaluation complete!")
        print("   Run scoring: python flows/score_results.py")
        print("=" * 60)


if __name__ == "__main__":
    main()

