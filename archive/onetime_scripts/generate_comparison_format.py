#!/usr/bin/env python3
"""
Generate Comparison-Ready Format from Baseline Results

Creates unified formats optimized for comparing baseline vs distortion results:
1. baseline_comparison.json - Lookup table by question_id
2. baseline_comparison.csv - Flat CSV for Excel/Pandas analysis

Usage:
    python omnimath_distortion_workflow/flows/generate_comparison_format.py
"""

import csv
import json
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BASELINE_DIR = PROJECT_ROOT / "omnimath_distortion_workflow" / "evaluation" / "baseline_results"


def load_baseline_results():
    """Load baseline results from JSON files."""
    gpt4o_file = BASELINE_DIR / "gpt4o_results.json"
    gpt5_file = BASELINE_DIR / "gpt5_mini_results.json"
    
    with open(gpt4o_file, 'r') as f:
        gpt4o_results = json.load(f)
    
    with open(gpt5_file, 'r') as f:
        gpt5_results = json.load(f)
    
    return gpt4o_results, gpt5_results


def create_unified_lookup(gpt4o_results, gpt5_results):
    """
    Create a unified lookup table with question_id as key.
    
    Structure:
    {
        "2690": {
            "question_id": 2690,
            "difficulty": 1.0,
            "difficulty_category": "easy",
            "domain": "Mathematics -> Algebra -> Prealgebra -> Fractions",
            "original_question": "...",
            "correct_answer": "72",
            "baseline": {
                "gpt4o": {
                    "correct": true,
                    "answer": "72",
                    "match_type": "exact"
                },
                "gpt5_mini": {
                    "correct": true,
                    "answer": "72",
                    "match_type": "exact"
                }
            },
            "distorted": {}  # Placeholder for future distortion results
        }
    }
    """
    lookup = {}
    
    # Index GPT-4o results
    for r in gpt4o_results:
        qid = str(r["question_id"])
        lookup[qid] = {
            "question_id": r["question_id"],
            "difficulty": r["difficulty"],
            "difficulty_category": r["difficulty_category"],
            "domain": r["domain"],
            "original_question": r["question"],
            "correct_answer": r["ground_truth"],
            "baseline": {
                "gpt4o": {
                    "correct": r["is_correct"],
                    "answer": r["model_answer"],
                    "match_type": r["match_type"],
                    "api_success": r["api_success"]
                }
            },
            "distorted": {}  # Placeholder for distortion results
        }
    
    # Add GPT-5-mini results
    for r in gpt5_results:
        qid = str(r["question_id"])
        if qid in lookup:
            lookup[qid]["baseline"]["gpt5_mini"] = {
                "correct": r["is_correct"],
                "answer": r["model_answer"],
                "match_type": r["match_type"],
                "api_success": r["api_success"]
            }
    
    return lookup


def create_csv_summary(gpt4o_results, gpt5_results):
    """
    Create a flat CSV summary for easy analysis.
    
    Columns:
    - question_id, difficulty, difficulty_category, domain_short
    - correct_answer
    - gpt4o_baseline_correct, gpt4o_baseline_answer, gpt4o_baseline_match
    - gpt5_mini_baseline_correct, gpt5_mini_baseline_answer, gpt5_mini_baseline_match
    - (Future: miu_01_correct, miu_02_correct, etc.)
    """
    # Index results by question_id
    gpt4o_by_id = {r["question_id"]: r for r in gpt4o_results}
    gpt5_by_id = {r["question_id"]: r for r in gpt5_results}
    
    rows = []
    for qid in sorted(gpt4o_by_id.keys()):
        g4 = gpt4o_by_id[qid]
        g5 = gpt5_by_id.get(qid, {})
        
        # Extract short domain (last part of path)
        domain_parts = g4["domain"].split(" -> ") if g4["domain"] else []
        domain_short = domain_parts[-1] if domain_parts else ""
        
        row = {
            "question_id": qid,
            "difficulty": g4["difficulty"],
            "difficulty_category": g4["difficulty_category"],
            "domain_full": g4["domain"],
            "domain_short": domain_short,
            "correct_answer": g4["ground_truth"],
            "original_question": g4["question"][:100] + "..." if len(g4["question"]) > 100 else g4["question"],
            # GPT-4o baseline
            "gpt4o_baseline_correct": g4.get("is_correct", ""),
            "gpt4o_baseline_answer": g4.get("model_answer", ""),
            "gpt4o_baseline_match": g4.get("match_type", ""),
            # GPT-5-mini baseline
            "gpt5_mini_baseline_correct": g5.get("is_correct", ""),
            "gpt5_mini_baseline_answer": g5.get("model_answer", ""),
            "gpt5_mini_baseline_match": g5.get("match_type", ""),
            # Placeholders for distortion results (to be filled later)
            # "gpt4o_miu_01_correct": "",
            # "gpt4o_miu_02_correct": "",
            # etc.
        }
        rows.append(row)
    
    return rows


def create_statistics_summary(gpt4o_results, gpt5_results):
    """Create detailed statistics summary."""
    
    def calc_stats(results):
        total = len(results)
        scorable = [r for r in results if r["match_type"] != "text_answer"]
        correct = sum(1 for r in scorable if r["is_correct"])
        text_answers = sum(1 for r in results if r["match_type"] == "text_answer")
        api_errors = sum(1 for r in results if not r.get("api_success", True))
        
        return {
            "total": total,
            "scorable": len(scorable),
            "correct": correct,
            "accuracy": round(correct / len(scorable) * 100, 2) if scorable else 0,
            "text_answers": text_answers,
            "api_errors": api_errors
        }
    
    # Overall stats
    gpt4o_stats = calc_stats(gpt4o_results)
    gpt5_stats = calc_stats(gpt5_results)
    
    # Stats by difficulty
    difficulty_stats = {}
    for diff in sorted(set(r["difficulty"] for r in gpt4o_results)):
        g4_diff = [r for r in gpt4o_results if r["difficulty"] == diff]
        g5_diff = [r for r in gpt5_results if r["difficulty"] == diff]
        difficulty_stats[str(diff)] = {
            "gpt4o": calc_stats(g4_diff),
            "gpt5_mini": calc_stats(g5_diff)
        }
    
    # Stats by domain
    domain_stats = {}
    for domain in sorted(set(r["domain"] for r in gpt4o_results)):
        g4_dom = [r for r in gpt4o_results if r["domain"] == domain]
        g5_dom = [r for r in gpt5_results if r["domain"] == domain]
        domain_stats[domain] = {
            "gpt4o": calc_stats(g4_dom),
            "gpt5_mini": calc_stats(g5_dom)
        }
    
    return {
        "generated": datetime.now().isoformat(),
        "overall": {
            "gpt4o": gpt4o_stats,
            "gpt5_mini": gpt5_stats
        },
        "by_difficulty": difficulty_stats,
        "by_domain": domain_stats
    }


def main():
    print("=" * 60)
    print("📊 Generating Comparison-Ready Format")
    print("=" * 60)
    
    # Load baseline results
    print("\n📂 Loading baseline results...")
    gpt4o_results, gpt5_results = load_baseline_results()
    print(f"   GPT-4o results: {len(gpt4o_results)}")
    print(f"   GPT-5-mini results: {len(gpt5_results)}")
    
    # Create unified lookup table
    print("\n📋 Creating unified lookup table...")
    lookup = create_unified_lookup(gpt4o_results, gpt5_results)
    
    lookup_file = BASELINE_DIR / "baseline_comparison.json"
    with open(lookup_file, 'w') as f:
        json.dump({
            "metadata": {
                "generated": datetime.now().isoformat(),
                "description": "Unified lookup table by question_id for baseline vs distortion comparison",
                "total_questions": len(lookup),
                "models": ["gpt-4o", "gpt-5-mini"],
                "structure": {
                    "baseline": "Results from original (non-distorted) questions",
                    "distorted": "Placeholder for distortion results (miu_0.1 to miu_0.9)"
                }
            },
            "questions": lookup
        }, f, indent=2)
    print(f"   ✅ Saved: {lookup_file.name}")
    
    # Create CSV summary
    print("\n📊 Creating CSV summary...")
    csv_rows = create_csv_summary(gpt4o_results, gpt5_results)
    
    csv_file = BASELINE_DIR / "baseline_comparison.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"   ✅ Saved: {csv_file.name}")
    
    # Create statistics summary
    print("\n📈 Creating statistics summary...")
    stats = create_statistics_summary(gpt4o_results, gpt5_results)
    
    stats_file = BASELINE_DIR / "baseline_statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"   ✅ Saved: {stats_file.name}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 BASELINE STATISTICS SUMMARY")
    print("=" * 60)
    
    print(f"\n🎯 Overall Accuracy:")
    print(f"   GPT-4o:     {stats['overall']['gpt4o']['correct']}/{stats['overall']['gpt4o']['scorable']} = {stats['overall']['gpt4o']['accuracy']}%")
    print(f"   GPT-5-mini: {stats['overall']['gpt5_mini']['correct']}/{stats['overall']['gpt5_mini']['scorable']} = {stats['overall']['gpt5_mini']['accuracy']}%")
    
    print(f"\n📈 By Difficulty (GPT-4o / GPT-5-mini accuracy):")
    for diff, data in sorted(stats["by_difficulty"].items(), key=lambda x: float(x[0])):
        g4_acc = data["gpt4o"]["accuracy"]
        g5_acc = data["gpt5_mini"]["accuracy"]
        count = data["gpt4o"]["total"]
        print(f"   {diff:>4}: {g4_acc:>5.1f}% / {g5_acc:>5.1f}%  (n={count})")
    
    print(f"\n💾 Files created in: {BASELINE_DIR}")
    print("   - baseline_comparison.json  (Unified lookup table)")
    print("   - baseline_comparison.csv   (Flat CSV for analysis)")
    print("   - baseline_statistics.json  (Detailed statistics)")
    
    print("\n" + "=" * 60)
    print("✅ Comparison format generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()







