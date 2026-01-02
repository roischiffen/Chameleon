#!/usr/bin/env python3
"""
Scoring Pipeline for OmniMath GPT-5 Evaluation

Combines parsed results with ground truth to score all evaluations.

Usage:
    python omnimath_distortion_workflow/flows/score_results.py

Output:
    - evaluation/scored/scored_results.json (full data)
    - evaluation/scored/scored_results.csv (for analysis)
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from omnimath_distortion_workflow.modules.results_parser import (
    parse_batch_results,
    get_parsing_summary
)
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers
from omnimath_distortion_workflow.modules.batch_converter import load_distortion_batch


# Paths
DATA_BATCHES_DIR = project_root / "omnimath_distortion_workflow" / "data" / "batches"
EVAL_RESULTS_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "results"
SCORED_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "scored"


def load_ground_truth() -> Dict[int, Dict[str, Any]]:
    """
    Load ground truth data from all distortion batches.
    
    Returns:
        Dict mapping question_id to question metadata (including correct_answer)
    """
    ground_truth = {}
    
    for batch_dir in sorted(DATA_BATCHES_DIR.iterdir()):
        if not batch_dir.is_dir() or not batch_dir.name.startswith("batch"):
            continue
        
        try:
            distortions = load_distortion_batch(batch_dir)
            
            for entry in distortions:
                question_id = entry["question_id"]
                
                # Store the first occurrence (all have same ground truth)
                if question_id not in ground_truth:
                    ground_truth[question_id] = {
                        "question_id": question_id,
                        "correct_answer": entry["correct_answer"],
                        "original_question": entry["original_question"],
                        "domain": entry.get("domain", ""),
                        "subject": entry.get("subject", []),
                        "difficulty": entry.get("difficulty"),
                        "difficulty_category": entry.get("difficulty_category", ""),
                        "source": entry.get("source", "omnimath")
                    }
                
                # Also store distorted questions by miu level
                miu = entry["miu"]
                miu_key = f"miu_{miu}"
                if miu_key not in ground_truth[question_id]:
                    ground_truth[question_id][miu_key] = {
                        "distorted_question": entry["distorted_question"],
                        "miu_description": entry.get("miu_description", "")
                    }
                    
        except Exception as e:
            print(f"Warning: Error loading {batch_dir.name}: {e}")
    
    return ground_truth


def load_all_results() -> List[Dict[str, Any]]:
    """
    Load all parsed results from the results directory.
    
    Handles both:
    - Batch API results (parsed with results_parser)
    - Direct evaluation results (already contains is_correct, etc.)
    
    Returns:
        List of all parsed results
    """
    all_results = []
    
    if not EVAL_RESULTS_DIR.exists():
        print(f"Warning: Results directory not found: {EVAL_RESULTS_DIR}")
        return all_results
    
    for results_file in sorted(EVAL_RESULTS_DIR.glob("*.jsonl")):
        print(f"  Loading: {results_file.name}")
        
        # Check if it's a direct evaluation file (has 'is_correct' field)
        with open(results_file, 'r') as f:
            first_line = f.readline()
            if first_line:
                first_result = json.loads(first_line)
                is_direct_eval = "is_correct" in first_result and "ground_truth" in first_result
        
        if is_direct_eval:
            # Direct evaluation format - already scored
            print(f"    (direct evaluation format)")
            with open(results_file, 'r') as f:
                for line in f:
                    if line.strip():
                        result = json.loads(line)
                        # Normalize field names for consistency
                        result["success"] = result.get("api_success", True)
                        result["error"] = result.get("api_error")
                        all_results.append(result)
            print(f"    → {len([r for r in all_results if 'direct' not in str(results_file)])} results")
        else:
            # Batch API format - needs parsing
            results = parse_batch_results(results_file)
            all_results.extend(results)
            print(f"    → {len(results)} results")
    
    return all_results


def score_result(result: Dict[str, Any], ground_truth: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Score a single result against ground truth.
    
    Args:
        result: Parsed result from results_parser or direct evaluation
        ground_truth: Ground truth lookup dict
        
    Returns:
        Scored result with all metadata
    """
    # Check if already scored (direct evaluation format)
    if "is_correct" in result and "ground_truth" in result and result.get("ground_truth"):
        # Already scored - just ensure consistent field names
        scored = result.copy()
        scored["api_success"] = result.get("api_success", result.get("success", True))
        scored["api_error"] = result.get("api_error", result.get("error"))
        return scored
    
    question_id = result.get("question_id")
    miu = result.get("miu")
    
    # Initialize scored result
    scored = {
        "question_id": question_id,
        "miu": miu,
        "miu_description": "",
        "domain": "",
        "difficulty": None,
        "difficulty_category": "",
        "original_question": "",
        "distorted_question": "",
        "ground_truth": "",
        "model_answer": result.get("model_answer", ""),
        "is_correct": False,
        "match_type": "no_match",
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "reasoning_tokens": result.get("reasoning_tokens"),
        "api_success": result.get("success", False),
        "api_error": result.get("error")
    }
    
    # Look up ground truth
    if question_id is None or question_id not in ground_truth:
        scored["api_error"] = scored.get("api_error") or f"Question {question_id} not found in ground truth"
        return scored
    
    gt = ground_truth[question_id]
    
    # Fill in metadata
    scored["ground_truth"] = gt["correct_answer"]
    scored["original_question"] = gt["original_question"]
    scored["domain"] = gt["domain"]
    scored["difficulty"] = gt["difficulty"]
    scored["difficulty_category"] = gt["difficulty_category"]
    
    # Get distorted question and miu_description for non-baseline
    if miu is not None and miu > 0:
        miu_key = f"miu_{miu}"
        if miu_key in gt:
            scored["distorted_question"] = gt[miu_key]["distorted_question"]
            scored["miu_description"] = gt[miu_key]["miu_description"]
        else:
            scored["distorted_question"] = gt["original_question"]  # Fallback
    else:
        # Baseline (μ=0.0) uses original question
        scored["distorted_question"] = gt["original_question"]
        scored["miu_description"] = "Baseline (Original)"
    
    # Compare answers (only if API call was successful)
    if result.get("success") and scored["model_answer"]:
        is_correct, match_type = compare_answers(scored["model_answer"], scored["ground_truth"])
        scored["is_correct"] = is_correct
        scored["match_type"] = match_type
    
    return scored


def score_all_results(results: List[Dict], ground_truth: Dict[int, Dict]) -> List[Dict[str, Any]]:
    """
    Score all results against ground truth.
    
    Args:
        results: List of parsed results
        ground_truth: Ground truth lookup dict
        
    Returns:
        List of scored results
    """
    scored_results = []
    
    for result in results:
        scored = score_result(result, ground_truth)
        scored_results.append(scored)
    
    return scored_results


def calculate_summary_stats(scored_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics from scored results.
    
    Args:
        scored_results: List of scored results
        
    Returns:
        Summary statistics dict
    """
    total = len(scored_results)
    
    if total == 0:
        return {"error": "No results to analyze"}
    
    # Filter to API-successful results
    successful = [r for r in scored_results if r["api_success"]]
    total_successful = len(successful)
    
    # Overall accuracy
    correct = sum(1 for r in successful if r["is_correct"])
    
    # Accuracy by μ level
    by_miu = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in successful:
        miu_key = str(r["miu"]) if r["miu"] is not None else "unknown"
        by_miu[miu_key]["total"] += 1
        if r["is_correct"]:
            by_miu[miu_key]["correct"] += 1
    
    miu_accuracy = {}
    for miu_key in sorted(by_miu.keys(), key=lambda x: float(x) if x != "unknown" else 999):
        data = by_miu[miu_key]
        miu_accuracy[miu_key] = {
            "total": data["total"],
            "correct": data["correct"],
            "accuracy": (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
        }
    
    # Accuracy by difficulty
    by_difficulty = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in successful:
        diff_key = r["difficulty_category"] or "unknown"
        by_difficulty[diff_key]["total"] += 1
        if r["is_correct"]:
            by_difficulty[diff_key]["correct"] += 1
    
    difficulty_accuracy = {}
    for diff_key in sorted(by_difficulty.keys()):
        data = by_difficulty[diff_key]
        difficulty_accuracy[diff_key] = {
            "total": data["total"],
            "correct": data["correct"],
            "accuracy": (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
        }
    
    # Match type distribution
    match_types = defaultdict(int)
    for r in successful:
        match_types[r["match_type"]] += 1
    
    # Token statistics
    input_tokens = [r["input_tokens"] for r in successful if r["input_tokens"] is not None]
    output_tokens = [r["output_tokens"] for r in successful if r["output_tokens"] is not None]
    reasoning_tokens = [r["reasoning_tokens"] for r in successful if r["reasoning_tokens"] is not None]
    
    return {
        "total_evaluations": total,
        "api_successful": total_successful,
        "api_failed": total - total_successful,
        "overall_correct": correct,
        "overall_accuracy": (correct / total_successful * 100) if total_successful > 0 else 0,
        "accuracy_by_miu": miu_accuracy,
        "accuracy_by_difficulty": difficulty_accuracy,
        "match_type_distribution": dict(match_types),
        "token_stats": {
            "total_input_tokens": sum(input_tokens) if input_tokens else 0,
            "total_output_tokens": sum(output_tokens) if output_tokens else 0,
            "total_reasoning_tokens": sum(reasoning_tokens) if reasoning_tokens else 0,
            "avg_input_tokens": (sum(input_tokens) / len(input_tokens)) if input_tokens else 0,
            "avg_output_tokens": (sum(output_tokens) / len(output_tokens)) if output_tokens else 0
        },
        "generated_at": datetime.now().isoformat()
    }


def save_results(scored_results: List[Dict], summary: Dict, output_dir: Path) -> None:
    """
    Save scored results to JSON and CSV files.
    
    Args:
        scored_results: List of scored results
        summary: Summary statistics
        output_dir: Directory to save files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full JSON
    json_path = output_dir / "scored_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": summary,
            "results": scored_results
        }, f, indent=2)
    print(f"  ✅ JSON: {json_path}")
    
    # Save summary JSON separately
    summary_path = output_dir / "scoring_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✅ Summary: {summary_path}")
    
    # Save CSV for analysis
    csv_path = output_dir / "scored_results.csv"
    if scored_results:
        # Define CSV columns
        fieldnames = [
            "question_id", "miu", "miu_description", "domain", 
            "difficulty", "difficulty_category",
            "ground_truth", "model_answer", "is_correct", "match_type",
            "input_tokens", "output_tokens", "reasoning_tokens",
            "api_success", "api_error"
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(scored_results)
        print(f"  ✅ CSV: {csv_path}")


def print_summary(summary: Dict) -> None:
    """Print a formatted summary to console."""
    
    print("\n" + "=" * 60)
    print("SCORING SUMMARY")
    print("=" * 60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total evaluations: {summary['total_evaluations']}")
    print(f"   API successful: {summary['api_successful']}")
    print(f"   API failed: {summary['api_failed']}")
    print(f"   Correct answers: {summary['overall_correct']}")
    print(f"   Overall accuracy: {summary['overall_accuracy']:.1f}%")
    
    print(f"\n📈 Accuracy by μ-Level:")
    for miu, data in summary['accuracy_by_miu'].items():
        bar = "█" * int(data['accuracy'] / 5) + "░" * (20 - int(data['accuracy'] / 5))
        print(f"   μ={miu}: {data['accuracy']:5.1f}% ({data['correct']:3}/{data['total']:3}) {bar}")
    
    print(f"\n📊 Accuracy by Difficulty:")
    for diff, data in summary['accuracy_by_difficulty'].items():
        print(f"   {diff}: {data['accuracy']:.1f}% ({data['correct']}/{data['total']})")
    
    print(f"\n🔤 Match Types:")
    for match_type, count in summary['match_type_distribution'].items():
        print(f"   {match_type}: {count}")
    
    print(f"\n💰 Token Usage:")
    ts = summary['token_stats']
    print(f"   Total input tokens: {ts['total_input_tokens']:,}")
    print(f"   Total output tokens: {ts['total_output_tokens']:,}")
    print(f"   Total reasoning tokens: {ts['total_reasoning_tokens']:,}")
    print(f"   Avg input tokens/request: {ts['avg_input_tokens']:.1f}")
    print(f"   Avg output tokens/request: {ts['avg_output_tokens']:.1f}")


def main():
    """Main scoring pipeline."""
    
    print("=" * 60)
    print("OmniMath Scoring Pipeline")
    print("=" * 60)
    
    # Step 1: Load ground truth
    print("\n📚 Loading ground truth data...")
    ground_truth = load_ground_truth()
    print(f"   Loaded {len(ground_truth)} unique questions")
    
    # Step 2: Load results
    print("\n📥 Loading evaluation results...")
    results = load_all_results()
    
    if not results:
        print("\n❌ No results found in", EVAL_RESULTS_DIR)
        print("   Make sure you've run the batch submissions and downloaded results.")
        print("   Use: python flows/submit_eval_batches.py download")
        return 1
    
    print(f"\n   Total results loaded: {len(results)}")
    
    # Step 3: Score results
    print("\n🎯 Scoring results...")
    scored_results = score_all_results(results, ground_truth)
    print(f"   Scored {len(scored_results)} evaluations")
    
    # Step 4: Calculate summary
    print("\n📊 Calculating statistics...")
    summary = calculate_summary_stats(scored_results)
    
    # Step 5: Save results
    print("\n💾 Saving results...")
    save_results(scored_results, summary, SCORED_DIR)
    
    # Step 6: Print summary
    print_summary(summary)
    
    print("\n" + "=" * 60)
    print("✅ Scoring complete!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

