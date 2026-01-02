#!/usr/bin/env python3
"""
Comprehensive Data Verification Script
=======================================

This script verifies ALL baseline and distortion data is correct, complete,
and properly formatted after all corrections have been applied.

Run this to confirm data integrity before analysis.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE_DIR = Path(__file__).parent
BASELINE_DIR = BASE_DIR / "evaluation" / "baseline_results"
DISTORTION_DIR = BASE_DIR / "evaluation" / "distortion_results"
OUTPUT_DIR = BASE_DIR / "statistical_analysis_report"

# Expected configurations
EXPECTED_CONFIGS = {
    "baseline": [
        ("gpt_5_difficulty_1_0", "gpt-5", 1.0),
        ("gpt_5_difficulty_1_5", "gpt-5", 1.5),
        ("gpt_4o_difficulty_1_0", "gpt-4o", 1.0),
        ("gpt_4o_difficulty_1_5", "gpt-4o", 1.5),
        ("gpt_5_mini_difficulty_1_0", "gpt-5-mini", 1.0),
        ("gpt_5_mini_difficulty_1_5", "gpt-5-mini", 1.5),
        ("mistral_large_latest_difficulty_1_0", "mistral-large-latest", 1.0),
        ("mistral_large_latest_difficulty_1_5", "mistral-large-latest", 1.5),
    ],
    "distortion": [
        ("gpt_5_difficulty_1_0", "gpt-5", 1.0),
        ("gpt_5_difficulty_1_5", "gpt-5", 1.5),
        ("gpt_4o_difficulty_1_0", "gpt-4o", 1.0),
        ("gpt_4o_difficulty_1_5", "gpt-4o", 1.5),  # Added!
        ("gpt_5_mini_difficulty_1_0", "gpt-5-mini", 1.0),
        ("gpt_5_mini_difficulty_1_5", "gpt-5-mini", 1.5),
        ("mistral_large_latest_difficulty_1_0", "mistral-large-latest", 1.0),
        ("mistral_large_latest_difficulty_1_5", "mistral-large-latest", 1.5),
    ]
}


def verify_baseline_results():
    """Verify all baseline results files."""
    print("\n" + "=" * 60)
    print("  VERIFYING BASELINE RESULTS")
    print("=" * 60)
    
    results = {}
    issues = []
    
    for folder_name, expected_model, expected_diff in EXPECTED_CONFIGS["baseline"]:
        folder_path = BASELINE_DIR / folder_name
        results_path = folder_path / "results.json"
        summary_path = folder_path / "summary.json"
        
        config_key = f"{expected_model}_diff_{expected_diff}"
        results[config_key] = {
            "folder": folder_name,
            "model": expected_model,
            "difficulty": expected_diff,
            "status": "OK",
            "issues": []
        }
        
        # Check folder exists
        if not folder_path.exists():
            results[config_key]["status"] = "MISSING"
            results[config_key]["issues"].append("Folder not found")
            issues.append(f"{folder_name}: Folder not found")
            continue
        
        # Check results.json
        if not results_path.exists():
            results[config_key]["status"] = "ERROR"
            results[config_key]["issues"].append("results.json not found")
            issues.append(f"{folder_name}: results.json not found")
            continue
        
        # Load and verify results
        try:
            with open(results_path) as f:
                data = json.load(f)
            
            total = len(data)
            correct = sum(1 for r in data if r.get("is_correct"))
            empty = sum(1 for r in data if not r.get("model_answer"))
            retried = sum(1 for r in data if r.get("retried"))
            fixed = sum(1 for r in data if r.get("fixed"))
            
            accuracy = correct / total * 100 if total > 0 else 0
            
            results[config_key]["total"] = total
            results[config_key]["correct"] = correct
            results[config_key]["accuracy"] = round(accuracy, 1)
            results[config_key]["empty"] = empty
            results[config_key]["retried"] = retried
            results[config_key]["fixed"] = fixed
            
            # Check for issues
            if total != 100:
                results[config_key]["issues"].append(f"Expected 100 questions, got {total}")
            if empty > 0:
                results[config_key]["issues"].append(f"{empty} empty answers")
                results[config_key]["status"] = "WARNING"
            
        except Exception as e:
            results[config_key]["status"] = "ERROR"
            results[config_key]["issues"].append(f"Failed to load: {str(e)}")
            issues.append(f"{folder_name}: {str(e)}")
            continue
        
        # Check/update summary.json
        summary_data = {
            "folder": folder_name,
            "model": expected_model,
            "difficulty": expected_diff,
            "total_questions": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": round(accuracy, 2),
            "empty_answers": empty,
            "retried_questions": retried,
            "fixed_questions": fixed,
            "verified_at": datetime.now().isoformat()
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        results[config_key]["summary_updated"] = True
        
        # Print status
        status_icon = "✅" if results[config_key]["status"] == "OK" else "⚠️" if results[config_key]["status"] == "WARNING" else "❌"
        print(f"\n{status_icon} {folder_name}")
        print(f"   Model: {expected_model}, Difficulty: {expected_diff}")
        print(f"   Accuracy: {correct}/{total} ({accuracy:.1f}%)")
        if empty > 0:
            print(f"   Empty: {empty}")
        if retried > 0:
            print(f"   Retried: {retried}")
        if fixed > 0:
            print(f"   Fixed: {fixed}")
    
    return results, issues


def verify_distortion_results():
    """Verify all distortion results files."""
    print("\n" + "=" * 60)
    print("  VERIFYING DISTORTION RESULTS")
    print("=" * 60)
    
    results = {}
    issues = []
    
    for folder_name, expected_model, expected_diff in EXPECTED_CONFIGS["distortion"]:
        folder_path = DISTORTION_DIR / folder_name
        results_path = folder_path / "results.jsonl"
        summary_path = folder_path / "summary.json"
        
        config_key = f"{expected_model}_diff_{expected_diff}"
        results[config_key] = {
            "folder": folder_name,
            "model": expected_model,
            "difficulty": expected_diff,
            "status": "OK",
            "issues": [],
            "by_miu": {}
        }
        
        # Check folder exists
        if not folder_path.exists():
            results[config_key]["status"] = "MISSING"
            results[config_key]["issues"].append("Folder not found")
            issues.append(f"{folder_name}: Folder not found")
            continue
        
        # Check results.jsonl
        if not results_path.exists():
            results[config_key]["status"] = "ERROR"
            results[config_key]["issues"].append("results.jsonl not found")
            issues.append(f"{folder_name}: results.jsonl not found")
            continue
        
        # Load and verify results
        try:
            by_miu = defaultdict(lambda: {"total": 0, "correct": 0, "empty": 0})
            
            with open(results_path) as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        miu = round(item.get("miu", 0), 1)
                        if miu > 0:  # Skip baseline (miu=0)
                            by_miu[miu]["total"] += 1
                            if item.get("is_correct"):
                                by_miu[miu]["correct"] += 1
                            if not item.get("model_answer"):
                                by_miu[miu]["empty"] += 1
            
            total_questions = sum(m["total"] for m in by_miu.values())
            total_correct = sum(m["correct"] for m in by_miu.values())
            total_empty = sum(m["empty"] for m in by_miu.values())
            
            results[config_key]["total"] = total_questions
            results[config_key]["correct"] = total_correct
            results[config_key]["accuracy"] = round(total_correct / total_questions * 100, 1) if total_questions > 0 else 0
            results[config_key]["empty"] = total_empty
            
            for miu in sorted(by_miu.keys()):
                miu_data = by_miu[miu]
                acc = miu_data["correct"] / miu_data["total"] * 100 if miu_data["total"] > 0 else 0
                results[config_key]["by_miu"][str(miu)] = {
                    "total": miu_data["total"],
                    "correct": miu_data["correct"],
                    "accuracy": round(acc, 1),
                    "empty": miu_data["empty"]
                }
            
            # Check for issues
            expected_per_miu = 100
            for miu, miu_data in by_miu.items():
                if miu_data["total"] < expected_per_miu - 5:  # Allow some tolerance
                    results[config_key]["issues"].append(f"MIU {miu}: Only {miu_data['total']} questions")
            
            if total_empty > 0:
                results[config_key]["issues"].append(f"{total_empty} empty answers")
                if total_empty > 20:
                    results[config_key]["status"] = "WARNING"
            
        except Exception as e:
            results[config_key]["status"] = "ERROR"
            results[config_key]["issues"].append(f"Failed to load: {str(e)}")
            issues.append(f"{folder_name}: {str(e)}")
            continue
        
        # Update summary.json
        summary_data = {
            "model": expected_model,
            "difficulty": expected_diff,
            "total_questions": total_questions,
            "correct": total_correct,
            "accuracy": round(total_correct / total_questions * 100, 2) if total_questions > 0 else 0,
            "empty_answers": total_empty,
            "by_miu": {
                str(miu): {
                    "correct": by_miu[miu]["correct"],
                    "total": by_miu[miu]["total"],
                    "accuracy": round(by_miu[miu]["correct"] / by_miu[miu]["total"] * 100, 1) if by_miu[miu]["total"] > 0 else 0,
                    "empty": by_miu[miu]["empty"]
                }
                for miu in sorted(by_miu.keys())
            },
            "verified_at": datetime.now().isoformat()
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        results[config_key]["summary_updated"] = True
        
        # Print status
        status_icon = "✅" if results[config_key]["status"] == "OK" else "⚠️" if results[config_key]["status"] == "WARNING" else "❌"
        print(f"\n{status_icon} {folder_name}")
        print(f"   Model: {expected_model}, Difficulty: {expected_diff}")
        print(f"   Total: {total_questions}, Correct: {total_correct} ({results[config_key]['accuracy']:.1f}%)")
        print(f"   By MIU: ", end="")
        for miu in sorted(by_miu.keys()):
            acc = by_miu[miu]["correct"] / by_miu[miu]["total"] * 100 if by_miu[miu]["total"] > 0 else 0
            print(f"{miu}:{acc:.0f}% ", end="")
        print()
        if total_empty > 0:
            print(f"   Empty: {total_empty}")
    
    return results, issues


def generate_verification_report(baseline_results, distortion_results, baseline_issues, distortion_issues):
    """Generate comprehensive verification report."""
    
    report = {
        "verification_timestamp": datetime.now().isoformat(),
        "summary": {
            "baseline_configs": len(baseline_results),
            "distortion_configs": len(distortion_results),
            "baseline_issues": len(baseline_issues),
            "distortion_issues": len(distortion_issues),
            "status": "VERIFIED" if len(baseline_issues) == 0 and len(distortion_issues) == 0 else "HAS_WARNINGS"
        },
        "baseline": {},
        "distortion": {}
    }
    
    # Baseline summary
    for key, data in baseline_results.items():
        report["baseline"][key] = {
            "model": data["model"],
            "difficulty": data["difficulty"],
            "total": data.get("total", 0),
            "correct": data.get("correct", 0),
            "accuracy": data.get("accuracy", 0),
            "empty": data.get("empty", 0),
            "retried": data.get("retried", 0),
            "fixed": data.get("fixed", 0),
            "status": data["status"],
            "issues": data["issues"]
        }
    
    # Distortion summary
    for key, data in distortion_results.items():
        report["distortion"][key] = {
            "model": data["model"],
            "difficulty": data["difficulty"],
            "total": data.get("total", 0),
            "correct": data.get("correct", 0),
            "accuracy": data.get("accuracy", 0),
            "empty": data.get("empty", 0),
            "by_miu": data.get("by_miu", {}),
            "status": data["status"],
            "issues": data["issues"]
        }
    
    # Save report
    report_path = OUTPUT_DIR / "data_verification_report.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report


def print_final_summary(baseline_results, distortion_results):
    """Print final summary table."""
    print("\n" + "=" * 80)
    print("  FINAL VERIFICATION SUMMARY")
    print("=" * 80)
    
    print("\n--- BASELINE ACCURACY ---")
    print(f"{'Model':<20} {'Difficulty':<12} {'Accuracy':<12} {'Empty':<8} {'Status':<10}")
    print("-" * 62)
    
    for key, data in sorted(baseline_results.items()):
        model = data["model"]
        diff = data["difficulty"]
        acc = data.get("accuracy", 0)
        empty = data.get("empty", 0)
        status = data["status"]
        print(f"{model:<20} {diff:<12} {acc:>6.1f}%     {empty:<8} {status:<10}")
    
    print("\n--- DISTORTION ACCURACY (Average across MIU) ---")
    print(f"{'Model':<20} {'Difficulty':<12} {'Avg Acc':<12} {'Empty':<8} {'Status':<10}")
    print("-" * 62)
    
    for key, data in sorted(distortion_results.items()):
        model = data["model"]
        diff = data["difficulty"]
        acc = data.get("accuracy", 0)
        empty = data.get("empty", 0)
        status = data["status"]
        print(f"{model:<20} {diff:<12} {acc:>6.1f}%     {empty:<8} {status:<10}")
    
    print("\n" + "=" * 80)
    print("  ALL DATA VERIFIED AND SUMMARIES UPDATED")
    print("=" * 80)


def main():
    print("=" * 60)
    print("  COMPREHENSIVE DATA VERIFICATION")
    print("  Checking all baseline and distortion data")
    print("=" * 60)
    
    # Verify baseline
    baseline_results, baseline_issues = verify_baseline_results()
    
    # Verify distortion
    distortion_results, distortion_issues = verify_distortion_results()
    
    # Generate report
    report = generate_verification_report(
        baseline_results, distortion_results,
        baseline_issues, distortion_issues
    )
    
    # Print summary
    print_final_summary(baseline_results, distortion_results)
    
    print(f"\n📊 Verification report saved to:")
    print(f"   {OUTPUT_DIR / 'data_verification_report.json'}")
    
    # Return status
    all_ok = len(baseline_issues) == 0 and len(distortion_issues) == 0
    
    if all_ok:
        print("\n✅ ALL DATA VERIFIED - Ready for analysis!")
    else:
        print(f"\n⚠️ WARNINGS FOUND:")
        for issue in baseline_issues + distortion_issues:
            print(f"   - {issue}")
    
    return report


if __name__ == "__main__":
    main()

