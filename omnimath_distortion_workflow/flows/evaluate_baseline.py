#!/usr/bin/env python3
"""
Baseline Evaluation Script for OmniMath

Tests ORIGINAL questions (before distortion) with two models:
1. GPT-4o (standard)
2. GPT-5-mini (with low reasoning effort)

This establishes baseline accuracy before testing distorted questions.

Usage:
    # Test with 5 samples first (RECOMMENDED)
    python omnimath_distortion_workflow/flows/evaluate_baseline.py --test 5
    
    # Test specific difficulty level
    python omnimath_distortion_workflow/flows/evaluate_baseline.py --difficulty 1.0 --full
    
    # Run full evaluation (after testing)
    python omnimath_distortion_workflow/flows/evaluate_baseline.py --full
    
    # Test single model
    python omnimath_distortion_workflow/flows/evaluate_baseline.py --test 10 --model gpt-4o

Environment:
    OPENAI_API_KEY: Your OpenAI API key (required)
"""

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
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
    pass

from omnimath_distortion_workflow.modules.evaluation_prompt import create_evaluation_prompt
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# Try to import openai
try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Model configurations
MODEL_CONFIGS = {
    "gpt-4o": {
        "model": "gpt-4o",
        "max_tokens": 150,
        "temperature": 0  # Deterministic output
    },
    "gpt-5-mini": {
        "model": "gpt-5-mini",
        "reasoning_effort": "low",  # Low reasoning for math problems
        "max_completion_tokens": 150
    }
}

# Paths
DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
OUTPUT_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "baseline_results"

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # seconds between API calls


# =============================================================================
# DATA LOADING
# =============================================================================

def load_unique_baseline_questions(
    difficulty: Optional[float] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Load unique baseline questions from all difficulty folders.
    
    Each question_id appears 9 times (once per μ level 0.1-0.9).
    For baseline, we extract ONE entry per question_id and use `original_question`.
    
    Args:
        difficulty: Filter by specific difficulty level (e.g., 1.0, 1.5)
        limit: Limit number of questions returned
    
    Returns:
        List of unique baseline question dicts
    """
    questions = {}  # Use dict to ensure uniqueness by question_id
    
    # Get all difficulty folders
    difficulty_folders = sorted(DATA_DIR.glob("difficulty_*"))
    
    for folder in difficulty_folders:
        if not folder.is_dir():
            continue
        
        # Get difficulty level from folder name
        folder_difficulty_str = folder.name.replace("difficulty_", "")
        try:
            folder_difficulty = float(folder_difficulty_str)
        except ValueError:
            continue
        
        # Filter by difficulty if specified
        if difficulty is not None and folder_difficulty != difficulty:
            continue
        
        # Load JSON file
        json_file = folder / f"difficulty_{folder_difficulty_str}_distortions.json"
        if not json_file.exists():
            continue
        
        with open(json_file, 'r') as f:
            entries = json.load(f)
        
        for entry in entries:
            qid = entry["question_id"]
            
            # Only add if we haven't seen this question_id
            if qid not in questions:
                questions[qid] = {
                    "question_id": qid,
                    "domain": entry.get("domain", ""),
                    "original_question": entry["original_question"],
                    "correct_answer": entry["correct_answer"],
                    "difficulty": entry.get("difficulty", folder_difficulty),
                    "difficulty_category": entry.get("difficulty_category", ""),
                    "source": entry.get("source", "omnimath"),
                    "subject": entry.get("subject", "")
                }
    
    # Convert to list and sort by difficulty then question_id
    result = list(questions.values())
    result.sort(key=lambda x: (x["difficulty"], x["question_id"]))
    
    if limit:
        result = result[:limit]
    
    return result


def get_difficulty_levels() -> List[float]:
    """Get all available difficulty levels from folder names."""
    levels = []
    for folder in DATA_DIR.glob("difficulty_*"):
        if folder.is_dir():
            try:
                level = float(folder.name.replace("difficulty_", ""))
                levels.append(level)
            except ValueError:
                continue
    return sorted(levels)


# =============================================================================
# API CLIENT
# =============================================================================

def get_client() -> openai.OpenAI:
    """Get OpenAI client with API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def check_model_availability(client: openai.OpenAI, model_name: str) -> bool:
    """Check if a specific model is available."""
    try:
        config = MODEL_CONFIGS[model_name]
        
        request_params = {
            "model": config["model"],
            "messages": [{"role": "user", "content": "Say 'ok'"}],
        }
        
        if "gpt-5" in config["model"].lower():
            if "reasoning_effort" in config:
                request_params["reasoning_effort"] = config["reasoning_effort"]
            request_params["max_completion_tokens"] = 5
        else:
            request_params["max_tokens"] = 5
            if "temperature" in config:
                request_params["temperature"] = config["temperature"]
        
        client.chat.completions.create(**request_params)
        return True
    except Exception as e:
        print(f"   ⚠️  {model_name} not available: {e}")
        return False


# =============================================================================
# EVALUATION
# =============================================================================

def evaluate_single(
    client: openai.OpenAI, 
    model_name: str, 
    question_data: Dict
) -> Dict[str, Any]:
    """
    Evaluate a single question with a specific model.
    
    Returns result dict with model answer, correctness, and token usage.
    """
    config = MODEL_CONFIGS[model_name]
    prompt = create_evaluation_prompt(question_data["original_question"])
    
    result = {
        "question_id": question_data["question_id"],
        "domain": question_data["domain"],
        "difficulty": question_data["difficulty"],
        "difficulty_category": question_data["difficulty_category"],
        "ground_truth": question_data["correct_answer"],
        "question": question_data["original_question"],
        "model": model_name,
        "model_answer": "",
        "is_correct": False,
        "match_type": "no_match",
        "input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None,
        "api_success": False,
        "api_error": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Build request based on model type
        request_params = {
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
        }
        
        # GPT-5 family uses reasoning_effort and max_completion_tokens
        if "gpt-5" in config["model"].lower():
            if "reasoning_effort" in config:
                request_params["reasoning_effort"] = config["reasoning_effort"]
            request_params["max_completion_tokens"] = config.get("max_completion_tokens", 150)
        else:
            # GPT-4o and other models use max_tokens and temperature
            request_params["max_tokens"] = config.get("max_tokens", 150)
            if "temperature" in config:
                request_params["temperature"] = config["temperature"]
        
        # Make API call
        response = client.chat.completions.create(**request_params)
        
        # Extract answer
        model_answer = response.choices[0].message.content.strip()
        
        # Clean up answer (remove common prefixes)
        import re
        for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*', r'^final\s+answer\s*:?\s*']:
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
        result["is_correct"] = is_correct if is_correct is not None else False
        result["match_type"] = match_type
        
    except Exception as e:
        result["api_error"] = str(e)
    
    return result


def run_evaluation(
    client: openai.OpenAI,
    questions: List[Dict],
    models: List[str],
    verbose: bool = True
) -> Dict[str, List[Dict]]:
    """
    Run evaluation on questions with specified models.
    
    Args:
        client: OpenAI client
        questions: List of question dicts
        models: List of model names to evaluate
        verbose: Print progress
    
    Returns:
        Dict mapping model name to list of results
    """
    results = {model: [] for model in models}
    
    total_evaluations = len(questions) * len(models)
    current = 0
    
    if verbose:
        print(f"\n📊 Evaluating {len(questions)} questions with {len(models)} model(s)...")
        print(f"   Total API calls: {total_evaluations}")
        print()
    
    for q in questions:
        for model in models:
            current += 1
            
            result = evaluate_single(client, model, q)
            results[model].append(result)
            
            if verbose:
                status = "✅" if result["is_correct"] else ("⚠️ Text" if result["match_type"] == "text_answer" else "❌")
                print(f"   [{current:>4}/{total_evaluations}] Q{result['question_id']} | {model[:10]:>10} | {status} | {result['model_answer'][:15]}")
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
    
    return results


# =============================================================================
# ANALYSIS & REPORTING
# =============================================================================

def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculate statistics from evaluation results."""
    total = len(results)
    
    # Filter out text answers for accuracy calculation
    scorable = [r for r in results if r["match_type"] != "text_answer"]
    correct = sum(1 for r in scorable if r["is_correct"])
    
    text_answers = sum(1 for r in results if r["match_type"] == "text_answer")
    api_errors = sum(1 for r in results if r["api_error"])
    
    return {
        "total": total,
        "scorable": len(scorable),
        "correct": correct,
        "accuracy": correct / len(scorable) * 100 if scorable else 0,
        "text_answers": text_answers,
        "api_errors": api_errors
    }


def generate_markdown_report(
    gpt4o_results: List[Dict],
    gpt5_mini_results: List[Dict],
    questions: List[Dict]
) -> str:
    """Generate comprehensive markdown analysis report."""
    
    # Overall statistics
    gpt4o_stats = calculate_statistics(gpt4o_results)
    gpt5_mini_stats = calculate_statistics(gpt5_mini_results)
    
    # Group by difficulty
    difficulty_stats = defaultdict(lambda: {"gpt4o": [], "gpt5_mini": []})
    for r in gpt4o_results:
        difficulty_stats[r["difficulty"]]["gpt4o"].append(r)
    for r in gpt5_mini_results:
        difficulty_stats[r["difficulty"]]["gpt5_mini"].append(r)
    
    # Group by domain
    domain_stats = defaultdict(lambda: {"gpt4o": [], "gpt5_mini": []})
    for r in gpt4o_results:
        domain_stats[r["domain"]]["gpt4o"].append(r)
    for r in gpt5_mini_results:
        domain_stats[r["domain"]]["gpt5_mini"].append(r)
    
    # Build report
    lines = []
    lines.append("# 🎯 Baseline Evaluation Results\n")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    # Executive Summary
    lines.append("## Executive Summary\n")
    lines.append(f"- **Total questions evaluated**: {len(questions)}")
    lines.append(f"- **GPT-4o accuracy**: {gpt4o_stats['accuracy']:.1f}% ({gpt4o_stats['correct']}/{gpt4o_stats['scorable']} scorable)")
    lines.append(f"- **GPT-5-mini accuracy**: {gpt5_mini_stats['accuracy']:.1f}% ({gpt5_mini_stats['correct']}/{gpt5_mini_stats['scorable']} scorable)")
    if gpt4o_stats['text_answers'] > 0:
        lines.append(f"- **Text answers (manual review needed)**: {gpt4o_stats['text_answers']}")
    lines.append("")
    
    # Results by Difficulty Level
    lines.append("## Results by Difficulty Level\n")
    lines.append("| Difficulty | Questions | GPT-4o Correct | GPT-4o Accuracy | GPT-5-mini Correct | GPT-5-mini Accuracy |")
    lines.append("|------------|-----------|----------------|-----------------|---------------------|----------------------|")
    
    for diff in sorted(difficulty_stats.keys()):
        data = difficulty_stats[diff]
        gpt4o_diff = calculate_statistics(data["gpt4o"])
        gpt5_diff = calculate_statistics(data["gpt5_mini"])
        
        lines.append(f"| {diff} | {gpt4o_diff['total']} | {gpt4o_diff['correct']} | {gpt4o_diff['accuracy']:.1f}% | {gpt5_diff['correct']} | {gpt5_diff['accuracy']:.1f}% |")
    
    # Add totals row
    lines.append(f"| **Total** | **{len(questions)}** | **{gpt4o_stats['correct']}** | **{gpt4o_stats['accuracy']:.1f}%** | **{gpt5_mini_stats['correct']}** | **{gpt5_mini_stats['accuracy']:.1f}%** |")
    lines.append("")
    
    # Results by Mathematical Domain
    lines.append("## Results by Mathematical Domain\n")
    lines.append("| Domain | Questions | GPT-4o Accuracy | GPT-5-mini Accuracy |")
    lines.append("|--------|-----------|-----------------|----------------------|")
    
    # Sort domains by question count
    sorted_domains = sorted(domain_stats.items(), key=lambda x: len(x[1]["gpt4o"]), reverse=True)
    
    for domain, data in sorted_domains[:15]:  # Top 15 domains
        gpt4o_dom = calculate_statistics(data["gpt4o"])
        gpt5_dom = calculate_statistics(data["gpt5_mini"])
        
        # Truncate long domain names
        domain_display = domain[:60] + "..." if len(domain) > 60 else domain
        lines.append(f"| {domain_display} | {gpt4o_dom['total']} | {gpt4o_dom['accuracy']:.1f}% | {gpt5_dom['accuracy']:.1f}% |")
    
    lines.append("")
    
    # Detailed Results by Difficulty
    lines.append("## Detailed Results\n")
    
    for diff in sorted(difficulty_stats.keys()):
        lines.append(f"### Difficulty {diff}")
        lines.append("")
        lines.append("| Q_ID | GPT-4o | GPT-5-mini | Domain |")
        lines.append("|------|--------|------------|--------|")
        
        # Get questions for this difficulty
        diff_q_ids = [r["question_id"] for r in difficulty_stats[diff]["gpt4o"]]
        
        for qid in diff_q_ids:
            gpt4o_r = next((r for r in gpt4o_results if r["question_id"] == qid), None)
            gpt5_r = next((r for r in gpt5_mini_results if r["question_id"] == qid), None)
            
            if gpt4o_r and gpt5_r:
                g4_status = "✅" if gpt4o_r["is_correct"] else ("⚠️" if gpt4o_r["match_type"] == "text_answer" else "❌")
                g5_status = "✅" if gpt5_r["is_correct"] else ("⚠️" if gpt5_r["match_type"] == "text_answer" else "❌")
                domain_short = gpt4o_r["domain"].split(" -> ")[-1][:20] if gpt4o_r["domain"] else ""
                lines.append(f"| {qid} | {g4_status} | {g5_status} | {domain_short} |")
        
        lines.append("")
    
    # Analysis Notes
    lines.append("## Analysis Notes\n")
    
    # Find best/worst difficulties
    if difficulty_stats:
        best_diff = max(difficulty_stats.keys(), key=lambda d: calculate_statistics(difficulty_stats[d]["gpt4o"])["accuracy"])
        worst_diff = min(difficulty_stats.keys(), key=lambda d: calculate_statistics(difficulty_stats[d]["gpt4o"])["accuracy"])
        lines.append(f"- **Highest accuracy difficulty**: {best_diff} ({calculate_statistics(difficulty_stats[best_diff]['gpt4o'])['accuracy']:.1f}%)")
        lines.append(f"- **Lowest accuracy difficulty**: {worst_diff} ({calculate_statistics(difficulty_stats[worst_diff]['gpt4o'])['accuracy']:.1f}%)")
    
    # Model comparison
    if gpt4o_stats['accuracy'] > gpt5_mini_stats['accuracy']:
        diff = gpt4o_stats['accuracy'] - gpt5_mini_stats['accuracy']
        lines.append(f"- **GPT-4o outperforms GPT-5-mini by {diff:.1f} percentage points**")
    elif gpt5_mini_stats['accuracy'] > gpt4o_stats['accuracy']:
        diff = gpt5_mini_stats['accuracy'] - gpt4o_stats['accuracy']
        lines.append(f"- **GPT-5-mini outperforms GPT-4o by {diff:.1f} percentage points**")
    else:
        lines.append("- **Both models perform equally**")
    
    lines.append("")
    
    # Raw Data Location
    lines.append("## Raw Data Location\n")
    lines.append("- Full results: `evaluation/baseline_results/baseline_results.json`")
    lines.append("- GPT-4o detailed: `evaluation/baseline_results/gpt4o_results.json`")
    lines.append("- GPT-5-mini detailed: `evaluation/baseline_results/gpt5_mini_results.json`")
    lines.append("")
    
    return "\n".join(lines)


def save_results(
    gpt4o_results: List[Dict],
    gpt5_mini_results: List[Dict],
    questions: List[Dict],
    output_dir: Path
) -> None:
    """Save all results and generate report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save GPT-4o results
    gpt4o_file = output_dir / "gpt4o_results.json"
    with open(gpt4o_file, 'w') as f:
        json.dump(gpt4o_results, f, indent=2)
    print(f"   💾 GPT-4o results: {gpt4o_file}")
    
    # Save GPT-5-mini results
    gpt5_file = output_dir / "gpt5_mini_results.json"
    with open(gpt5_file, 'w') as f:
        json.dump(gpt5_mini_results, f, indent=2)
    print(f"   💾 GPT-5-mini results: {gpt5_file}")
    
    # Save combined results
    combined = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "total_questions": len(questions),
            "models": ["gpt-4o", "gpt-5-mini"]
        },
        "gpt4o": gpt4o_results,
        "gpt5_mini": gpt5_mini_results
    }
    combined_file = output_dir / "baseline_results.json"
    with open(combined_file, 'w') as f:
        json.dump(combined, f, indent=2)
    print(f"   💾 Combined results: {combined_file}")
    
    # Generate and save markdown report
    report = generate_markdown_report(gpt4o_results, gpt5_mini_results, questions)
    report_file = output_dir / "BASELINE_ANALYSIS.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"   📄 Analysis report: {report_file}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Baseline evaluation for OmniMath questions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test 5                    # Test 5 random samples
  %(prog)s --test 10 --difficulty 1.0  # Test 10 samples from difficulty 1.0
  %(prog)s --test 5 --model gpt-4o     # Test only with GPT-4o
  %(prog)s --difficulty 1.0 --full     # Full eval on difficulty 1.0
  %(prog)s --full                      # Full evaluation all questions
        """
    )
    
    # Mode selection
    parser.add_argument("--test", type=int, metavar="N",
                        help="Test mode: evaluate N random samples")
    parser.add_argument("--full", action="store_true",
                        help="Run full evaluation")
    
    # Filters
    parser.add_argument("--difficulty", type=float,
                        help="Filter by specific difficulty level (e.g., 1.0, 1.5, 2.0)")
    parser.add_argument("--model", type=str, choices=["gpt-4o", "gpt-5-mini"],
                        help="Test with single model only")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.test and not args.full:
        parser.error("Must specify either --test N or --full")
    
    print("=" * 60)
    print("🎯 OmniMath Baseline Evaluation")
    print("=" * 60)
    
    # Get available difficulty levels
    difficulty_levels = get_difficulty_levels()
    print(f"\n📊 Available difficulty levels: {difficulty_levels}")
    
    # Validate difficulty if specified
    if args.difficulty is not None and args.difficulty not in difficulty_levels:
        print(f"❌ Invalid difficulty: {args.difficulty}")
        print(f"   Available: {difficulty_levels}")
        sys.exit(1)
    
    # Load questions
    print("\n📂 Loading baseline questions...")
    questions = load_unique_baseline_questions(difficulty=args.difficulty)
    print(f"   Found {len(questions)} unique baseline questions")
    
    if args.difficulty:
        print(f"   Filtered to difficulty {args.difficulty}")
    
    # For test mode, sample randomly
    if args.test:
        random.seed(42)  # Reproducible
        questions = random.sample(questions, min(args.test, len(questions)))
        print(f"   Sampled {len(questions)} questions for testing")
    
    # Determine models to test
    models = ["gpt-4o", "gpt-5-mini"]
    if args.model:
        models = [args.model]
    
    print(f"\n🤖 Models to evaluate: {models}")
    
    # Get OpenAI client
    client = get_client()
    
    # Check model availability
    print("\n🔍 Checking model availability...")
    available_models = []
    for model in models:
        if check_model_availability(client, model):
            print(f"   ✅ {model} is available")
            available_models.append(model)
        else:
            print(f"   ❌ {model} is NOT available - skipping")
    
    if not available_models:
        print("\n❌ No models available! Check your API key and model access.")
        sys.exit(1)
    
    models = available_models
    
    # Estimate time and cost
    total_calls = len(questions) * len(models)
    est_time = total_calls * (RATE_LIMIT_DELAY + 0.5) / 60
    est_cost = total_calls * 0.002  # ~$0.002 per request estimate
    
    print(f"\n⏱️  Estimated time: {est_time:.1f} minutes")
    print(f"💰 Estimated cost: ~${est_cost:.2f}")
    
    # Run evaluation
    results = run_evaluation(client, questions, models)
    
    # Extract results by model
    gpt4o_results = results.get("gpt-4o", [])
    gpt5_mini_results = results.get("gpt-5-mini", [])
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    
    if gpt4o_results:
        stats = calculate_statistics(gpt4o_results)
        print(f"\n   GPT-4o: {stats['correct']}/{stats['scorable']} correct ({stats['accuracy']:.1f}%)")
        if stats['text_answers'] > 0:
            print(f"           ({stats['text_answers']} text answers excluded)")
    
    if gpt5_mini_results:
        stats = calculate_statistics(gpt5_mini_results)
        print(f"\n   GPT-5-mini: {stats['correct']}/{stats['scorable']} correct ({stats['accuracy']:.1f}%)")
        if stats['text_answers'] > 0:
            print(f"               ({stats['text_answers']} text answers excluded)")
    
    # Save results
    print("\n💾 Saving results...")
    
    # Use test or full output directory
    if args.test:
        output_dir = OUTPUT_DIR / "test"
    else:
        output_dir = OUTPUT_DIR
    
    save_results(gpt4o_results, gpt5_mini_results, questions, output_dir)
    
    print("\n" + "=" * 60)
    print("✅ Evaluation complete!")
    if args.test:
        print("   Review results above. If everything looks good, run with --full")
    print("=" * 60)


if __name__ == "__main__":
    main()

