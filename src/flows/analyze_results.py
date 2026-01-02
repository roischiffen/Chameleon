#!/usr/bin/env python3
"""
Distortion Results Analysis Script

Analyzes model performance on distorted questions compared to baseline.
Generates comprehensive reports showing how distortion levels affect accuracy.

Usage:
    # Analyze single model on single difficulty
    python analyze_distortion_results.py --model gpt-4o --difficulty 1.0
    
    # Analyze all available results
    python analyze_distortion_results.py --all
    
    # Generate comparison report
    python analyze_distortion_results.py --compare

Output:
    - Console summary with accuracy by miu level
    - JSON report with detailed statistics
    - CSV export for further analysis
    - Markdown report for documentation
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================================
# PATHS
# ============================================================================

EVAL_DIR = project_root / "data" / "results"
DISTORTION_RESULTS_DIR = EVAL_DIR / "distortion"
BASELINE_RESULTS_DIR = EVAL_DIR / "baseline"
ANALYSIS_OUTPUT_DIR = project_root / "output" / "reports"


# ============================================================================
# DATA LOADING
# ============================================================================

def load_distortion_results(model: str, difficulty: float) -> List[Dict]:
    """Load distortion evaluation results for a model and difficulty."""
    # Try both batch and direct results
    for suffix in ["", "_direct"]:
        model_name = model.replace("-", "_")
        diff_str = str(difficulty).replace(".", "_")
        results_dir = DISTORTION_RESULTS_DIR / f"{model_name}_difficulty_{diff_str}{suffix}"
        results_file = results_dir / "results.jsonl"
        
        if results_file.exists():
            results = []
            with open(results_file, 'r') as f:
                for line in f:
                    if line.strip():
                        results.append(json.loads(line))
            if results:
                return results
    
    return []


def load_baseline_results(model: str) -> List[Dict]:
    """Load baseline evaluation results for a model."""
    model_key = model.lower().replace("-", "")
    
    # Try different file patterns
    patterns = [
        f"{model_key}_results.json",
        f"{model_key}_results_corrected.json",
        f"gpt4o_results.json" if "4o" in model else None,
        f"gpt5_mini_results.json" if "5" in model or "mini" in model else None,
    ]
    
    for pattern in patterns:
        if pattern:
            results_file = BASELINE_RESULTS_DIR / pattern
            if results_file.exists():
                with open(results_file, 'r') as f:
                    return json.load(f)
    
    return []


def find_available_results() -> List[Dict]:
    """Find all available evaluation results."""
    available = []
    
    if not DISTORTION_RESULTS_DIR.exists():
        return available
    
    for result_dir in DISTORTION_RESULTS_DIR.iterdir():
        if not result_dir.is_dir():
            continue
        
        results_file = result_dir / "results.jsonl"
        if not results_file.exists():
            continue
        
        # Parse directory name
        name = result_dir.name
        # e.g., "gpt_4o_difficulty_1_0" or "gpt_4o_difficulty_1_0_direct"
        
        # Count results
        with open(results_file, 'r') as f:
            count = sum(1 for line in f if line.strip())
        
        available.append({
            "directory": result_dir.name,
            "path": str(result_dir),
            "count": count
        })
    
    return available


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def analyze_results(results: List[Dict]) -> Dict:
    """Analyze results and compute statistics."""
    if not results:
        return {"error": "No results to analyze"}
    
    stats = {
        "total": len(results),
        "correct": 0,
        "incorrect": 0,
        "errors": 0,
        "accuracy": 0.0,
        "by_miu": {},
        "by_match_type": {},
        "by_domain": {},
        "token_usage": {
            "total_input": 0,
            "total_output": 0,
            "total_reasoning": 0
        }
    }
    
    miu_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    match_type_stats = defaultdict(int)
    domain_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    
    for r in results:
        miu = r.get("miu", 0)
        is_correct = r.get("is_correct", False)
        match_type = r.get("match_type", "unknown")
        domain = r.get("domain", "unknown")
        
        # Overall stats
        if r.get("api_error"):
            stats["errors"] += 1
        elif is_correct:
            stats["correct"] += 1
        else:
            stats["incorrect"] += 1
        
        # By miu
        miu_stats[miu]["total"] += 1
        if is_correct:
            miu_stats[miu]["correct"] += 1
        
        # By match type
        match_type_stats[match_type] += 1
        
        # By domain
        if domain:
            domain_stats[domain]["total"] += 1
            if is_correct:
                domain_stats[domain]["correct"] += 1
        
        # Token usage
        if r.get("input_tokens"):
            stats["token_usage"]["total_input"] += r["input_tokens"]
        if r.get("output_tokens"):
            stats["token_usage"]["total_output"] += r["output_tokens"]
        if r.get("reasoning_tokens"):
            stats["token_usage"]["total_reasoning"] += r["reasoning_tokens"]
    
    # Compute accuracy
    if stats["total"] > 0:
        stats["accuracy"] = stats["correct"] / stats["total"] * 100
    
    # Finalize miu stats
    for miu, data in sorted(miu_stats.items()):
        accuracy = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        stats["by_miu"][str(miu)] = {
            "correct": data["correct"],
            "total": data["total"],
            "accuracy": accuracy
        }
    
    # Match type stats
    stats["by_match_type"] = dict(match_type_stats)
    
    # Top domains by count
    sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1]["total"], reverse=True)
    for domain, data in sorted_domains[:10]:
        accuracy = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        stats["by_domain"][domain] = {
            "correct": data["correct"],
            "total": data["total"],
            "accuracy": accuracy
        }
    
    return stats


def compare_with_baseline(
    distortion_results: List[Dict],
    baseline_results: List[Dict],
    difficulty: float
) -> Dict:
    """Compare distortion results with baseline."""
    comparison = {
        "baseline": {"total": 0, "correct": 0, "accuracy": 0.0},
        "distorted": {"by_miu": {}},
        "degradation": {},
        "robustness_score": 0.0
    }
    
    # Filter baseline results by difficulty
    baseline_for_diff = [r for r in baseline_results 
                        if abs(r.get("difficulty", 0) - difficulty) < 0.01]
    
    if baseline_for_diff:
        baseline_correct = sum(1 for r in baseline_for_diff if r.get("is_correct"))
        comparison["baseline"]["total"] = len(baseline_for_diff)
        comparison["baseline"]["correct"] = baseline_correct
        comparison["baseline"]["accuracy"] = baseline_correct / len(baseline_for_diff) * 100
    
    # Analyze distortion results by miu
    miu_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in distortion_results:
        miu = r.get("miu", 0)
        miu_stats[miu]["total"] += 1
        if r.get("is_correct"):
            miu_stats[miu]["correct"] += 1
    
    for miu, data in sorted(miu_stats.items()):
        accuracy = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        comparison["distorted"]["by_miu"][str(miu)] = {
            "correct": data["correct"],
            "total": data["total"],
            "accuracy": accuracy
        }
        
        # Compute degradation from baseline
        if comparison["baseline"]["accuracy"] > 0:
            degradation = comparison["baseline"]["accuracy"] - accuracy
            comparison["degradation"][str(miu)] = {
                "absolute": degradation,
                "relative": degradation / comparison["baseline"]["accuracy"] * 100
            }
    
    # Compute robustness score (average accuracy across distortion levels / baseline)
    if comparison["baseline"]["accuracy"] > 0 and comparison["distorted"]["by_miu"]:
        avg_distorted_accuracy = sum(
            d["accuracy"] for d in comparison["distorted"]["by_miu"].values()
        ) / len(comparison["distorted"]["by_miu"])
        comparison["robustness_score"] = avg_distorted_accuracy / comparison["baseline"]["accuracy"] * 100
    
    return comparison


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_console_report(model: str, difficulty: float, stats: Dict, comparison: Optional[Dict] = None):
    """Print analysis report to console."""
    print(f"\n{'='*70}")
    print(f"📊 Distortion Analysis: {model} on Difficulty {difficulty}")
    print(f"{'='*70}")
    
    print(f"\n📋 Overall Statistics:")
    print(f"   Total questions: {stats['total']}")
    print(f"   Correct: {stats['correct']} ({stats['accuracy']:.1f}%)")
    print(f"   Incorrect: {stats['incorrect']}")
    if stats['errors'] > 0:
        print(f"   API Errors: {stats['errors']}")
    
    print(f"\n📈 Accuracy by Distortion Level (μ):")
    print(f"   {'μ':>5} | {'Correct':>8} | {'Total':>6} | {'Accuracy':>8}")
    print(f"   {'-'*35}")
    
    for miu, data in stats["by_miu"].items():
        print(f"   {miu:>5} | {data['correct']:>8} | {data['total']:>6} | {data['accuracy']:>7.1f}%")
    
    if comparison:
        print(f"\n📉 Comparison with Baseline:")
        print(f"   Baseline accuracy: {comparison['baseline']['accuracy']:.1f}%")
        print(f"\n   Degradation by μ level:")
        for miu, deg in comparison.get("degradation", {}).items():
            print(f"      μ={miu}: -{deg['absolute']:.1f}pp ({deg['relative']:.1f}% relative drop)")
        
        print(f"\n   🏆 Robustness Score: {comparison.get('robustness_score', 0):.1f}%")
        print(f"      (100% = no degradation from distortions)")
    
    if stats.get("by_match_type"):
        print(f"\n🔍 Match Type Distribution:")
        for match_type, count in sorted(stats["by_match_type"].items(), key=lambda x: -x[1]):
            pct = count / stats["total"] * 100
            print(f"   {match_type}: {count} ({pct:.1f}%)")
    
    print(f"\n💰 Token Usage:")
    print(f"   Input tokens: {stats['token_usage']['total_input']:,}")
    print(f"   Output tokens: {stats['token_usage']['total_output']:,}")
    if stats['token_usage']['total_reasoning'] > 0:
        print(f"   Reasoning tokens: {stats['token_usage']['total_reasoning']:,}")


def generate_markdown_report(
    model: str,
    difficulty: float,
    stats: Dict,
    comparison: Optional[Dict] = None
) -> str:
    """Generate markdown report."""
    lines = [
        f"# Distortion Analysis: {model} on Difficulty {difficulty}",
        f"",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Questions | {stats['total']} |",
        f"| Correct | {stats['correct']} |",
        f"| Accuracy | {stats['accuracy']:.1f}% |",
    ]
    
    if comparison:
        lines.extend([
            f"| Baseline Accuracy | {comparison['baseline']['accuracy']:.1f}% |",
            f"| Robustness Score | {comparison.get('robustness_score', 0):.1f}% |",
        ])
    
    lines.extend([
        f"",
        f"## Accuracy by Distortion Level",
        f"",
        f"| μ Level | Correct | Total | Accuracy |",
        f"|---------|---------|-------|----------|",
    ])
    
    for miu, data in stats["by_miu"].items():
        lines.append(f"| {miu} | {data['correct']} | {data['total']} | {data['accuracy']:.1f}% |")
    
    if comparison and comparison.get("degradation"):
        lines.extend([
            f"",
            f"## Degradation from Baseline",
            f"",
            f"| μ Level | Absolute Drop | Relative Drop |",
            f"|---------|---------------|---------------|",
        ])
        for miu, deg in comparison["degradation"].items():
            lines.append(f"| {miu} | {deg['absolute']:.1f}pp | {deg['relative']:.1f}% |")
    
    return "\n".join(lines)


def save_analysis(
    model: str,
    difficulty: float,
    stats: Dict,
    comparison: Optional[Dict] = None
):
    """Save analysis results to files."""
    ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    model_name = model.replace("-", "_")
    diff_str = str(difficulty).replace(".", "_")
    base_name = f"{model_name}_difficulty_{diff_str}"
    
    # Save JSON
    json_file = ANALYSIS_OUTPUT_DIR / f"{base_name}_analysis.json"
    output = {
        "model": model,
        "difficulty": difficulty,
        "statistics": stats,
        "comparison": comparison,
        "generated_at": datetime.now().isoformat()
    }
    with open(json_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Save Markdown
    md_file = ANALYSIS_OUTPUT_DIR / f"{base_name}_analysis.md"
    md_content = generate_markdown_report(model, difficulty, stats, comparison)
    with open(md_file, 'w') as f:
        f.write(md_content)
    
    print(f"\n📁 Analysis saved to:")
    print(f"   JSON: {json_file}")
    print(f"   Markdown: {md_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze distortion evaluation results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--model", type=str,
                       help="Model to analyze (e.g., gpt-4o)")
    parser.add_argument("--difficulty", type=float,
                       help="Difficulty level (1.0 or 1.5)")
    parser.add_argument("--all", action="store_true",
                       help="Analyze all available results")
    parser.add_argument("--compare", action="store_true",
                       help="Include baseline comparison")
    parser.add_argument("--save", action="store_true",
                       help="Save analysis to files")
    parser.add_argument("--list", action="store_true",
                       help="List available results")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("OmniMath Distortion Results Analysis")
    print("=" * 70)
    
    if args.list:
        available = find_available_results()
        if not available:
            print("\n❌ No evaluation results found.")
            print(f"   Run evaluate_distortions_batch.py or evaluate_distortions_direct.py first.")
            return
        
        print(f"\n📋 Available Results:")
        for result in available:
            print(f"   {result['directory']}: {result['count']} results")
        return
    
    if args.all:
        available = find_available_results()
        if not available:
            print("\n❌ No results found. Run evaluation first.")
            return
        
        for result in available:
            # Parse model and difficulty from directory name
            # This is a simplified parser
            print(f"\n📂 Analyzing: {result['directory']}")
    
    elif args.model and args.difficulty:
        results = load_distortion_results(args.model, args.difficulty)
        
        if not results:
            print(f"\n❌ No results found for {args.model} on difficulty {args.difficulty}")
            print(f"   Run evaluation first with:")
            print(f"   python evaluate_distortions_batch.py --run --model {args.model} --difficulty {args.difficulty}")
            return
        
        stats = analyze_results(results)
        
        comparison = None
        if args.compare:
            baseline = load_baseline_results(args.model)
            if baseline:
                comparison = compare_with_baseline(results, baseline, args.difficulty)
            else:
                print(f"\n⚠️  No baseline results found for {args.model}")
        
        generate_console_report(args.model, args.difficulty, stats, comparison)
        
        if args.save:
            save_analysis(args.model, args.difficulty, stats, comparison)
    
    else:
        print("\n❌ Please specify --model and --difficulty, or use --all")
        parser.print_help()


if __name__ == "__main__":
    main()
