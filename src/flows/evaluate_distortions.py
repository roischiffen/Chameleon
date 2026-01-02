#!/usr/bin/env python3
"""
Direct Distortion Evaluation Script (Synchronous API Calls)

Alternative to Batch API when you need faster results (no 50% discount).
Features robust checkpointing - saves after EVERY question to prevent data loss.

Key Features:
- Saves progress after EVERY question (crash-proof)
- Resume from any interruption instantly
- Rate limiting with exponential backoff
- Supports both GPT-4o and GPT-5-mini models
- Real-time progress display

Usage:
    # Evaluate GPT-4o on difficulty 1.0
    python evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0
    
    # Resume interrupted evaluation
    python evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0 --resume
    
    # Test with small sample first
    python evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0 --test 10
    
    # Evaluate specific miu levels only
    python evaluate_distortions_direct.py --model gpt-4o --difficulty 1.0 --miu 0.2,0.5

Environment:
    OPENAI_API_KEY: Your OpenAI API key (required)
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

try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    sys.exit(1)

from src.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
    parse_custom_id
)
from src.modules.answer_comparator import compare_answers

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = project_root / "data" / "source"
EVAL_DIR = project_root / "data" / "results" / "distortion"

MODEL_CONFIGS = {
    "gpt-4o": {
        "model_id": "gpt-4o",
        "use_reasoning": False,
        "max_tokens": 150,
        "temperature": 0,
    },
    "gpt-5": {
        "model_id": "gpt-5",
        "use_reasoning": True,
        "max_tokens": 150,
        "reasoning_effort": "low",
    },
    "gpt-5-mini": {
        "model_id": "gpt-5-mini",
        "use_reasoning": True,
        "max_tokens": 150,
        "reasoning_effort": "low",
    },
    "o4-mini": {
        "model_id": "o4-mini",
        "use_reasoning": True,
        "max_tokens": 150,
        "reasoning_effort": "low",
    }
}

# Rate limiting
INITIAL_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 5
BACKOFF_FACTOR = 2


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client() -> openai.OpenAI:
    """Get OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def get_eval_dir(model: str, difficulty: float) -> Path:
    """Get evaluation directory for model and difficulty."""
    model_name = model.replace("-", "_")
    diff_str = str(difficulty).replace(".", "_")
    eval_dir = EVAL_DIR / f"{model_name}_difficulty_{diff_str}_direct"
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
                    # Flatten the nested structure
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
        f.flush()  # Force write to disk
        os.fsync(f.fileno())  # Ensure OS writes to disk


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
    client: openai.OpenAI,
    model_config: Dict,
    question_data: Dict,
    retries: int = MAX_RETRIES
) -> Dict:
    """
    Evaluate a single question with retry logic.
    """
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
        "reasoning_tokens": None,
        "api_success": False,
        "api_error": None,
        "model": model_config["model_id"],
        "timestamp": datetime.now().isoformat()
    }
    
    delay = INITIAL_DELAY
    
    for attempt in range(retries):
        try:
            # Build request
            request_params = {
                "model": model_config["model_id"],
                "messages": [{"role": "user", "content": prompt}],
            }
            
            if model_config.get("use_reasoning"):
                request_params["max_completion_tokens"] = model_config["max_tokens"]
                request_params["reasoning_effort"] = model_config.get("reasoning_effort", "low")
            else:
                request_params["max_tokens"] = model_config["max_tokens"]
                request_params["temperature"] = model_config.get("temperature", 0)
            
            # Make API call
            response = client.chat.completions.create(**request_params)
            
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
                result["input_tokens"] = getattr(response.usage, 'prompt_tokens', None)
                result["output_tokens"] = getattr(response.usage, 'completion_tokens', None)
                
                if hasattr(response.usage, 'completion_tokens_details'):
                    details = response.usage.completion_tokens_details
                    if details:
                        result["reasoning_tokens"] = getattr(details, 'reasoning_tokens', None)
            
            # Compare answers
            is_correct, match_type = compare_answers(model_answer, question_data["correct_answer"])
            result["is_correct"] = is_correct
            result["match_type"] = match_type
            
            return result
            
        except openai.RateLimitError as e:
            if attempt < retries - 1:
                sleep_time = delay * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1)
                print(f"   ⏳ Rate limited. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                result["api_error"] = f"Rate limit exceeded after {retries} retries"
                
        except openai.APIError as e:
            if attempt < retries - 1:
                sleep_time = delay * (BACKOFF_FACTOR ** attempt)
                print(f"   ⚠️  API error. Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                result["api_error"] = str(e)
                
        except Exception as e:
            result["api_error"] = str(e)
            break
    
    return result


def run_evaluation(
    client: openai.OpenAI,
    model: str,
    difficulty: float,
    test_count: Optional[int] = None,
    miu_filter: Optional[List[float]] = None,
    resume: bool = True
):
    """
    Run evaluation on distorted questions.
    """
    eval_dir = get_eval_dir(model, difficulty)
    model_config = MODEL_CONFIGS[model]
    
    print(f"\n📊 Evaluating {model} on difficulty {difficulty}")
    print(f"   Output dir: {eval_dir}")
    
    # Load distortions
    distortions = load_distortions(difficulty)
    print(f"   Total distortions: {len(distortions)}")
    
    # Filter by miu if specified
    if miu_filter:
        distortions = [d for d in distortions if d["miu"] in miu_filter]
        print(f"   Filtered to miu levels {miu_filter}: {len(distortions)} questions")
    
    # Load completed IDs for resume
    if resume:
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
    
    # Estimate time and cost
    est_time_mins = len(distortions) * (INITIAL_DELAY + 0.5) / 60
    est_cost = len(distortions) * 0.0025  # Approximate cost per question
    print(f"\n   ⏱️  Estimated time: {est_time_mins:.1f} minutes")
    print(f"   💰 Estimated cost: ~${est_cost:.2f}")
    print(f"   💡 Use Batch API (--batch) for 50% discount!")
    
    # Confirm for full runs
    if not test_count and len(distortions) > 50:
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
        result = evaluate_single(client, model_config, dist)
        
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
        rate = i / elapsed if elapsed > 0 else 0
        eta = (len(distortions) - i) / rate / 60 if rate > 0 else 0
        
        ans_display = str(result['model_answer'])[:12]
        truth_display = str(result['ground_truth'])[:12]
        
        print(f"   {i:>4} | {result['question_id']:>5} | {result['miu']:>3} | {ans_display:>12} | {truth_display:>12} | {status}")
        
        # Rate limiting
        if i < len(distortions):
            time.sleep(INITIAL_DELAY)
    
    # Summary
    total = len(distortions)
    accuracy = correct / total * 100 if total > 0 else 0
    
    print(f"\n   {'='*65}")
    print(f"   📊 Results: {correct}/{total} correct ({accuracy:.1f}%)")
    if errors > 0:
        print(f"   ⚠️  API Errors: {errors}")
    
    # Save summary
    all_results = load_all_results(eval_dir)
    save_summary(eval_dir, model, difficulty, all_results)
    
    print(f"\n   📁 Results saved to: {eval_dir}")


def save_summary(eval_dir: Path, model: str, difficulty: float, results: List[Dict]):
    """Save evaluation summary."""
    summary = {
        "model": model,
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
        description="Direct evaluation of distorted questions (synchronous API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full evaluation
  %(prog)s --model gpt-4o --difficulty 1.0
  
  # Test with 10 questions first
  %(prog)s --model gpt-4o --difficulty 1.0 --test 10
  
  # Evaluate specific miu levels
  %(prog)s --model gpt-4o --difficulty 1.0 --miu 0.2,0.9
  
  # Start fresh (ignore previous progress)
  %(prog)s --model gpt-4o --difficulty 1.0 --no-resume

Note: For 50% cost savings, use evaluate_distortions_batch.py instead!
        """
    )
    
    parser.add_argument("--model", type=str, required=True,
                       choices=list(MODEL_CONFIGS.keys()),
                       help="Model to evaluate")
    parser.add_argument("--difficulty", type=float, required=True,
                       choices=[1.0, 1.5],
                       help="Difficulty level")
    parser.add_argument("--test", type=int, metavar="N",
                       help="Test with N questions only")
    parser.add_argument("--miu", type=str,
                       help="Comma-separated miu levels to evaluate (e.g., 0.2,0.5)")
    parser.add_argument("--no-resume", action="store_true",
                       help="Start fresh, ignore previous progress")
    
    args = parser.parse_args()
    
    # Parse miu filter
    miu_filter = None
    if args.miu:
        miu_filter = [float(m.strip()) for m in args.miu.split(",")]
    
    print("=" * 60)
    print("OmniMath Distortion Evaluation (Direct API)")
    print("=" * 60)
    
    client = get_client()
    
    try:
        run_evaluation(
            client=client,
            model=args.model,
            difficulty=args.difficulty,
            test_count=args.test,
            miu_filter=miu_filter,
            resume=not args.no_resume
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Progress saved! Run again to resume.")


if __name__ == "__main__":
    main()
