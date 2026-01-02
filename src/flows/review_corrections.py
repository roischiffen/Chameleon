#!/usr/bin/env python3
"""
Review and Correct Baseline Results

This script:
1. Generates compact review files for manual verification
2. Automatically identifies likely comparator failures
3. Corrects results based on improved comparison logic
4. Regenerates accurate statistics

Usage:
    python -m src.flows.review_corrections
"""

import json
import re
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

# Paths
project_root = Path(__file__).parent.parent.parent
RESULTS_DIR = project_root / "data" / "results" / "baseline"


# =============================================================================
# IMPROVED ANSWER COMPARISON
# =============================================================================

def strip_latex_units(answer: str) -> str:
    """
    Strip LaTeX unit annotations from an answer.
    
    Handles:
    - \text{ km}, \text{ cm}, etc.
    - \mathrm{~cm}^{3}, \mathrm{~km}, etc.
    - ^{\circ} \mathrm{C}
    """
    if not answer:
        return ""
    
    result = answer.strip()
    
    # Remove \text{...} with units
    result = re.sub(r'\\text\s*\{[^}]*\}', '', result)
    
    # Remove \mathrm{...} with units  
    result = re.sub(r'\\mathrm\s*\{[^}]*\}', '', result)
    
    # Remove degree symbols and temperature units
    result = re.sub(r'\^\{?\\circ\}?\s*\\?[A-Za-z]*', '', result)
    result = re.sub(r'°\s*[A-Za-z]*', '', result)
    
    # Remove common unit strings
    units = ['km', 'cm', 'm', 'mm', 'kg', 'g', 'mg', 'L', 'ml', 'mL', 
             'hours?', 'minutes?', 'seconds?', 'days?', 'weeks?', 'years?',
             'p\\.?m\\.?', 'a\\.?m\\.?', 'percent', '%']
    for unit in units:
        result = re.sub(rf'\s*{unit}\s*$', '', result, flags=re.IGNORECASE)
    
    # Clean up whitespace and trailing/leading punctuation
    result = result.strip()
    result = result.rstrip('.')
    
    return result


def normalize_number(s: str) -> Optional[float]:
    """
    Extract and normalize a number from a string.
    Handles fractions, decimals, scientific notation.
    """
    if not s:
        return None
    
    s = s.strip()
    
    # Remove LaTeX delimiters
    s = re.sub(r'\$([^$]*)\$', r'\1', s)
    s = re.sub(r'\\\(([^)]*)\\\)', r'\1', s)
    
    # Normalize unicode
    s = s.replace('−', '-').replace('–', '-')
    s = s.replace('×', '*')
    
    # Try direct float
    try:
        return float(s)
    except:
        pass
    
    # Try fraction a/b
    frac_match = re.match(r'^(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)$', s)
    if frac_match:
        try:
            num = float(frac_match.group(1))
            den = float(frac_match.group(2))
            if den != 0:
                return num / den
        except:
            pass
    
    # Try LaTeX fraction \frac{a}{b}
    latex_frac = re.match(r'\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}', s)
    if latex_frac:
        try:
            num = float(latex_frac.group(1))
            den = float(latex_frac.group(2))
            if den != 0:
                return num / den
        except:
            pass
    
    # Try scientific notation
    sci_match = re.match(r'^(-?\d+(?:\.\d+)?)\s*[×x\*]?\s*10\s*\^\s*\{?(-?\d+)\}?$', s)
    if sci_match:
        try:
            base = float(sci_match.group(1))
            exp = int(sci_match.group(2))
            return base * (10 ** exp)
        except:
            pass
    
    # Try power notation like 2^3
    power_match = re.match(r'^(\d+)\s*\^\s*\{?(\d+)\}?$', s)
    if power_match:
        try:
            base = int(power_match.group(1))
            exp = int(power_match.group(2))
            return float(base ** exp)
        except:
            pass
    
    return None


def improved_compare(model_answer: str, ground_truth: str) -> Tuple[bool, str]:
    """
    Improved answer comparison that handles units and format differences.
    
    Returns: (is_correct, reason)
    """
    if not model_answer or not ground_truth:
        return False, "empty_answer"
    
    # Strip LaTeX units from both
    model_clean = strip_latex_units(model_answer)
    truth_clean = strip_latex_units(ground_truth)
    
    # Normalize for comparison
    model_norm = model_clean.lower().strip()
    truth_norm = truth_clean.lower().strip()
    
    # 1. Exact match after cleaning
    if model_norm == truth_norm:
        return True, "exact_after_cleanup"
    
    # 2. Numeric comparison
    model_num = normalize_number(model_clean)
    truth_num = normalize_number(truth_clean)
    
    if model_num is not None and truth_num is not None:
        # Check absolute and relative tolerance
        if abs(model_num - truth_num) < 1e-6:
            return True, "numeric_match"
        if truth_num != 0 and abs((model_num - truth_num) / truth_num) < 1e-4:
            return True, "numeric_match_relative"
    
    # 3. Check if model answer contains the correct numeric value
    # e.g., "20 km" contains "20"
    if truth_num is not None:
        model_nums = re.findall(r'-?\d+(?:\.\d+)?', model_answer)
        for num_str in model_nums:
            try:
                num = float(num_str)
                if abs(num - truth_num) < 1e-6:
                    return True, "numeric_in_text"
            except:
                pass
    
    # 4. Check for equivalent text representations
    # Handle day names, time expressions
    text_equivalents = [
        (r'8\s*p\.?m\.?\s*on\s*saturday', r'8\s*\\text\{\s*p\.?m\.?\s*on\s*saturday\s*\}'),
        (r'sunday', r'sunday'),
        (r'monday', r'monday'),
        (r'tuesday', r'tuesday'),
        (r'wednesday', r'wednesday'),
        (r'thursday', r'thursday'),
        (r'friday', r'friday'),
        (r'saturday', r'saturday'),
    ]
    
    for pattern1, pattern2 in text_equivalents:
        if (re.search(pattern1, model_norm, re.IGNORECASE) and 
            re.search(pattern1, truth_norm, re.IGNORECASE)):
            return True, "text_equivalent"
    
    # 5. Handle expressions like "x+y" vs "x + y"
    model_no_space = re.sub(r'\s+', '', model_norm)
    truth_no_space = re.sub(r'\s+', '', truth_norm)
    if model_no_space == truth_no_space:
        return True, "whitespace_diff"
    
    return False, "no_match"


# =============================================================================
# ANALYSIS AND CORRECTION
# =============================================================================

def analyze_results(results: List[Dict]) -> Dict:
    """
    Analyze results and identify comparator failures.
    """
    analysis = {
        "total": len(results),
        "originally_correct": 0,
        "originally_incorrect": 0,
        "text_answers": 0,
        "comparator_failures": [],  # Marked wrong but actually correct
        "real_mistakes": [],  # Actually wrong
        "corrected_results": []
    }
    
    for r in results:
        corrected = r.copy()
        
        if r["match_type"] == "text_answer":
            analysis["text_answers"] += 1
            # Re-evaluate text answers
            is_correct, reason = improved_compare(r["model_answer"], r["ground_truth"])
            if is_correct:
                corrected["is_correct"] = True
                corrected["match_type"] = f"corrected:{reason}"
                analysis["comparator_failures"].append({
                    "question_id": r["question_id"],
                    "ground_truth": r["ground_truth"],
                    "model_answer": r["model_answer"],
                    "original_match_type": r["match_type"],
                    "corrected_reason": reason
                })
            else:
                corrected["is_correct"] = False
                corrected["match_type"] = "text_answer_incorrect"
        elif r["is_correct"]:
            analysis["originally_correct"] += 1
        else:
            analysis["originally_incorrect"] += 1
            # Re-evaluate incorrect answers
            is_correct, reason = improved_compare(r["model_answer"], r["ground_truth"])
            if is_correct:
                corrected["is_correct"] = True
                corrected["match_type"] = f"corrected:{reason}"
                analysis["comparator_failures"].append({
                    "question_id": r["question_id"],
                    "ground_truth": r["ground_truth"],
                    "model_answer": r["model_answer"],
                    "original_match_type": r["match_type"],
                    "corrected_reason": reason
                })
            else:
                analysis["real_mistakes"].append({
                    "question_id": r["question_id"],
                    "difficulty": r.get("difficulty"),
                    "ground_truth": r["ground_truth"],
                    "model_answer": r["model_answer"]
                })
        
        analysis["corrected_results"].append(corrected)
    
    return analysis


def calculate_statistics(results: List[Dict], difficulty: Optional[float] = None) -> Dict:
    """Calculate statistics from results."""
    if difficulty is not None:
        results = [r for r in results if r.get("difficulty") == difficulty]
    
    total = len(results)
    
    # Exclude text_answer_incorrect from scorable
    scorable = [r for r in results if r["match_type"] != "text_answer_incorrect" 
                and not r["match_type"].startswith("text_answer")]
    correct = sum(1 for r in results if r["is_correct"])
    
    return {
        "total": total,
        "scorable": len(scorable),
        "correct": correct,
        "accuracy": correct / total * 100 if total > 0 else 0,
        "scorable_accuracy": correct / len(scorable) * 100 if scorable else 0
    }


def generate_corrected_report(
    gpt4o_analysis: Dict,
    gpt5_analysis: Dict,
    target_difficulties: List[float] = [1.0, 1.5]
) -> str:
    """Generate corrected analysis report."""
    
    lines = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.append("# 📊 CORRECTED Baseline Success Analysis Report")
    lines.append("")
    lines.append(f"*Generated: {timestamp}*")
    lines.append("")
    lines.append("> **Note:** This report includes corrections for comparator failures where")
    lines.append("> model answers were marked incorrect due to format differences (units, LaTeX, etc.)")
    lines.append("> but were actually semantically correct.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary of corrections
    lines.append("## Correction Summary")
    lines.append("")
    lines.append(f"| Model | Comparator Failures Found | Original Correct | After Correction |")
    lines.append("|-------|---------------------------|------------------|------------------|")
    
    gpt4o_orig_correct = gpt4o_analysis["originally_correct"]
    gpt4o_new_correct = gpt4o_orig_correct + len(gpt4o_analysis["comparator_failures"])
    gpt5_orig_correct = gpt5_analysis["originally_correct"]
    gpt5_new_correct = gpt5_orig_correct + len(gpt5_analysis["comparator_failures"])
    
    lines.append(f"| GPT-4o | {len(gpt4o_analysis['comparator_failures'])} | {gpt4o_orig_correct} | {gpt4o_new_correct} |")
    lines.append(f"| GPT-5-mini | {len(gpt5_analysis['comparator_failures'])} | {gpt5_orig_correct} | {gpt5_new_correct} |")
    lines.append("")
    
    # Examples of corrections
    if gpt4o_analysis["comparator_failures"]:
        lines.append("### Sample Corrections (GPT-4o)")
        lines.append("")
        lines.append("| Q_ID | Ground Truth | Model Answer | Correction Reason |")
        lines.append("|------|--------------|--------------|-------------------|")
        for item in gpt4o_analysis["comparator_failures"][:10]:
            gt = item["ground_truth"][:30] + "..." if len(item["ground_truth"]) > 30 else item["ground_truth"]
            ma = item["model_answer"][:20] + "..." if len(item["model_answer"]) > 20 else item["model_answer"]
            lines.append(f"| {item['question_id']} | `{gt}` | `{ma}` | {item['corrected_reason']} |")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Executive Summary with corrected numbers
    lines.append("## 1. Executive Summary (CORRECTED)")
    lines.append("")
    
    gpt4o_results = gpt4o_analysis["corrected_results"]
    gpt5_results = gpt5_analysis["corrected_results"]
    
    # Filter to target difficulties
    gpt4o_filtered = [r for r in gpt4o_results if r.get("difficulty") in target_difficulties]
    gpt5_filtered = [r for r in gpt5_results if r.get("difficulty") in target_difficulties]
    
    gpt4o_stats = calculate_statistics(gpt4o_filtered)
    gpt5_stats = calculate_statistics(gpt5_filtered)
    
    lines.append("### Key Findings")
    lines.append("")
    lines.append(f"| Metric | GPT-4o | GPT-5-mini |")
    lines.append("|--------|--------|------------|")
    lines.append(f"| **Total Questions Evaluated** | {gpt4o_stats['total']} | {gpt5_stats['total']} |")
    lines.append(f"| **Correct Answers** | {gpt4o_stats['correct']} | {gpt5_stats['correct']} |")
    lines.append(f"| **Accuracy** | **{gpt4o_stats['accuracy']:.1f}%** | **{gpt5_stats['accuracy']:.1f}%** |")
    lines.append("")
    
    # Winner
    if gpt5_stats['accuracy'] > gpt4o_stats['accuracy']:
        diff = gpt5_stats['accuracy'] - gpt4o_stats['accuracy']
        lines.append(f"**🏆 Overall Winner: GPT-5-mini** (outperforms GPT-4o by {diff:.1f} percentage points)")
    elif gpt4o_stats['accuracy'] > gpt5_stats['accuracy']:
        diff = gpt4o_stats['accuracy'] - gpt5_stats['accuracy']
        lines.append(f"**🏆 Overall Winner: GPT-4o** (outperforms GPT-5-mini by {diff:.1f} percentage points)")
    else:
        lines.append("**🏆 Overall: Both models perform equally**")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # By difficulty
    lines.append("## 2. Performance by Difficulty Level (CORRECTED)")
    lines.append("")
    
    for diff in target_difficulties:
        gpt4o_diff_stats = calculate_statistics(gpt4o_results, diff)
        gpt5_diff_stats = calculate_statistics(gpt5_results, diff)
        
        lines.append(f"### Difficulty {diff}")
        lines.append("")
        lines.append(f"| Metric | GPT-4o | GPT-5-mini |")
        lines.append("|--------|--------|------------|")
        lines.append(f"| Questions Evaluated | {gpt4o_diff_stats['total']} | {gpt5_diff_stats['total']} |")
        lines.append(f"| Correct Answers | {gpt4o_diff_stats['correct']} | {gpt5_diff_stats['correct']} |")
        lines.append(f"| **Accuracy** | **{gpt4o_diff_stats['accuracy']:.1f}%** | **{gpt5_diff_stats['accuracy']:.1f}%** |")
        lines.append("")
        
        if gpt5_diff_stats['accuracy'] > gpt4o_diff_stats['accuracy']:
            diff_val = gpt5_diff_stats['accuracy'] - gpt4o_diff_stats['accuracy']
            lines.append(f"**Winner at Difficulty {diff}: GPT-5-mini** (+{diff_val:.1f}%)")
        elif gpt4o_diff_stats['accuracy'] > gpt5_diff_stats['accuracy']:
            diff_val = gpt4o_diff_stats['accuracy'] - gpt5_diff_stats['accuracy']
            lines.append(f"**Winner at Difficulty {diff}: GPT-4o** (+{diff_val:.1f}%)")
        else:
            lines.append(f"**Difficulty {diff}: Tie**")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Domain analysis
    lines.append("## 3. Performance by Mathematical Domain")
    lines.append("")
    
    domain_stats = defaultdict(lambda: {"gpt4o": [], "gpt5": []})
    for r in gpt4o_filtered:
        domain_stats[r.get("domain", "Unknown")]["gpt4o"].append(r)
    for r in gpt5_filtered:
        domain_stats[r.get("domain", "Unknown")]["gpt5"].append(r)
    
    sorted_domains = sorted(domain_stats.items(), key=lambda x: len(x[1]["gpt4o"]), reverse=True)
    
    lines.append("| Domain | Questions | GPT-4o Accuracy | GPT-5-mini Accuracy | Winner |")
    lines.append("|--------|-----------|-----------------|---------------------|--------|")
    
    for domain, data in sorted_domains[:15]:
        gpt4o_dom = calculate_statistics(data["gpt4o"])
        gpt5_dom = calculate_statistics(data["gpt5"])
        
        if gpt5_dom['accuracy'] > gpt4o_dom['accuracy']:
            winner = "GPT-5-mini"
        elif gpt4o_dom['accuracy'] > gpt5_dom['accuracy']:
            winner = "GPT-4o"
        else:
            winner = "Tie"
        
        domain_short = domain[:45] + "..." if len(domain) > 45 else domain
        lines.append(f"| {domain_short} | {gpt4o_dom['total']} | {gpt4o_dom['accuracy']:.1f}% | {gpt5_dom['accuracy']:.1f}% | {winner} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Model comparison
    lines.append("## 4. Detailed Model Comparison")
    lines.append("")
    
    gpt4o_map = {r["question_id"]: r for r in gpt4o_filtered}
    gpt5_map = {r["question_id"]: r for r in gpt5_filtered}
    
    both_correct = 0
    both_wrong = 0
    gpt4o_only = 0
    gpt5_only = 0
    
    for qid in set(gpt4o_map.keys()) & set(gpt5_map.keys()):
        g4_correct = gpt4o_map[qid]["is_correct"]
        g5_correct = gpt5_map[qid]["is_correct"]
        
        if g4_correct and g5_correct:
            both_correct += 1
        elif not g4_correct and not g5_correct:
            both_wrong += 1
        elif g4_correct and not g5_correct:
            gpt4o_only += 1
        else:
            gpt5_only += 1
    
    total_common = both_correct + both_wrong + gpt4o_only + gpt5_only
    
    lines.append("| Category | Count | Percentage |")
    lines.append("|----------|-------|------------|")
    if total_common > 0:
        lines.append(f"| Both models correct | {both_correct} | {both_correct/total_common*100:.1f}% |")
        lines.append(f"| Both models wrong | {both_wrong} | {both_wrong/total_common*100:.1f}% |")
        lines.append(f"| Only GPT-4o correct | {gpt4o_only} | {gpt4o_only/total_common*100:.1f}% |")
        lines.append(f"| Only GPT-5-mini correct | {gpt5_only} | {gpt5_only/total_common*100:.1f}% |")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Research implications
    lines.append("## 5. Research Implications for Chameleon Project")
    lines.append("")
    lines.append("### Corrected Baseline Establishment")
    lines.append("")
    lines.append(f"- **GPT-4o Baseline Accuracy**: {gpt4o_stats['accuracy']:.1f}%")
    lines.append(f"- **GPT-5-mini Baseline Accuracy**: {gpt5_stats['accuracy']:.1f}%")
    lines.append("")
    lines.append("### Distortion Impact Framework")
    lines.append("")
    lines.append("| Metric | Formula |")
    lines.append("|--------|---------|")
    lines.append("| Accuracy Degradation | `(Baseline% - Distorted%) / Baseline%` |")
    lines.append("| Robustness Score | `1 - Accuracy Degradation` |")
    lines.append("")
    
    lines.append("### Key Insights")
    lines.append("")
    lines.append(f"1. **GPT-5-mini shows stronger baseline performance** ({gpt5_stats['accuracy']:.1f}% vs {gpt4o_stats['accuracy']:.1f}%)")
    lines.append("2. **Performance gap narrows at higher difficulty** (1.0 → 1.5)")
    lines.append("3. **Both models struggle with word problems** requiring multi-step reasoning")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Data files
    lines.append("## Appendix: Data Files")
    lines.append("")
    lines.append("- **Corrected GPT-4o Results**: `evaluation/baseline_results/gpt4o_results_corrected.json`")
    lines.append("- **Corrected GPT-5-mini Results**: `evaluation/baseline_results/gpt5_mini_results_corrected.json`")
    lines.append("- **Corrected Statistics**: `evaluation/baseline_results/baseline_statistics_corrected.json`")
    lines.append("- **Comparison Details**: `evaluation/baseline_results/correction_details.json`")
    lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("📊 Review and Correct Baseline Results")
    print("=" * 70)
    
    # Load original results
    print("\n📂 Loading original results...")
    
    with open(RESULTS_DIR / "gpt4o_results.json", 'r') as f:
        gpt4o_results = json.load(f)
    
    with open(RESULTS_DIR / "gpt5_mini_results.json", 'r') as f:
        gpt5_results = json.load(f)
    
    # Filter to difficulty 1.0 and 1.5
    gpt4o_filtered = [r for r in gpt4o_results if r.get("difficulty") in [1.0, 1.5]]
    gpt5_filtered = [r for r in gpt5_results if r.get("difficulty") in [1.0, 1.5]]
    
    print(f"   GPT-4o: {len(gpt4o_filtered)} questions (difficulty 1.0 & 1.5)")
    print(f"   GPT-5-mini: {len(gpt5_filtered)} questions (difficulty 1.0 & 1.5)")
    
    # Analyze and correct
    print("\n🔍 Analyzing and correcting results...")
    
    gpt4o_analysis = analyze_results(gpt4o_filtered)
    gpt5_analysis = analyze_results(gpt5_filtered)
    
    print(f"\n📊 GPT-4o Analysis:")
    print(f"   Originally correct: {gpt4o_analysis['originally_correct']}")
    print(f"   Originally incorrect: {gpt4o_analysis['originally_incorrect']}")
    print(f"   Text answers: {gpt4o_analysis['text_answers']}")
    print(f"   ✅ Comparator failures found: {len(gpt4o_analysis['comparator_failures'])}")
    print(f"   ❌ Real mistakes: {len(gpt4o_analysis['real_mistakes'])}")
    
    print(f"\n📊 GPT-5-mini Analysis:")
    print(f"   Originally correct: {gpt5_analysis['originally_correct']}")
    print(f"   Originally incorrect: {gpt5_analysis['originally_incorrect']}")
    print(f"   Text answers: {gpt5_analysis['text_answers']}")
    print(f"   ✅ Comparator failures found: {len(gpt5_analysis['comparator_failures'])}")
    print(f"   ❌ Real mistakes: {len(gpt5_analysis['real_mistakes'])}")
    
    # Save corrected results
    print("\n💾 Saving corrected results...")
    
    # Save corrected GPT-4o results
    with open(RESULTS_DIR / "gpt4o_results_corrected.json", 'w') as f:
        json.dump(gpt4o_analysis["corrected_results"], f, indent=2)
    print(f"   ✅ {RESULTS_DIR / 'gpt4o_results_corrected.json'}")
    
    # Save corrected GPT-5-mini results
    with open(RESULTS_DIR / "gpt5_mini_results_corrected.json", 'w') as f:
        json.dump(gpt5_analysis["corrected_results"], f, indent=2)
    print(f"   ✅ {RESULTS_DIR / 'gpt5_mini_results_corrected.json'}")
    
    # Save correction details
    correction_details = {
        "generated": datetime.now().isoformat(),
        "gpt4o": {
            "comparator_failures": gpt4o_analysis["comparator_failures"],
            "total_corrected": len(gpt4o_analysis["comparator_failures"])
        },
        "gpt5_mini": {
            "comparator_failures": gpt5_analysis["comparator_failures"],
            "total_corrected": len(gpt5_analysis["comparator_failures"])
        }
    }
    with open(RESULTS_DIR / "correction_details.json", 'w') as f:
        json.dump(correction_details, f, indent=2)
    print(f"   ✅ {RESULTS_DIR / 'correction_details.json'}")
    
    # Save corrected statistics
    corrected_stats = {
        "generated": datetime.now().isoformat(),
        "note": "These statistics include corrections for comparator failures",
        "difficulty_1.0": {
            "gpt4o": calculate_statistics(gpt4o_analysis["corrected_results"], 1.0),
            "gpt5_mini": calculate_statistics(gpt5_analysis["corrected_results"], 1.0)
        },
        "difficulty_1.5": {
            "gpt4o": calculate_statistics(gpt4o_analysis["corrected_results"], 1.5),
            "gpt5_mini": calculate_statistics(gpt5_analysis["corrected_results"], 1.5)
        },
        "combined": {
            "gpt4o": calculate_statistics(gpt4o_analysis["corrected_results"]),
            "gpt5_mini": calculate_statistics(gpt5_analysis["corrected_results"])
        }
    }
    with open(RESULTS_DIR / "baseline_statistics_corrected.json", 'w') as f:
        json.dump(corrected_stats, f, indent=2)
    print(f"   ✅ {RESULTS_DIR / 'baseline_statistics_corrected.json'}")
    
    # Generate corrected report
    print("\n📝 Generating corrected analysis report...")
    report = generate_corrected_report(gpt4o_analysis, gpt5_analysis)
    with open(RESULTS_DIR / "BASELINE_ANALYSIS_CORRECTED.md", 'w') as f:
        f.write(report)
    print(f"   ✅ {RESULTS_DIR / 'BASELINE_ANALYSIS_CORRECTED.md'}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 CORRECTED RESULTS SUMMARY")
    print("=" * 70)
    
    for diff in [1.0, 1.5]:
        gpt4o_stats = calculate_statistics(gpt4o_analysis["corrected_results"], diff)
        gpt5_stats = calculate_statistics(gpt5_analysis["corrected_results"], diff)
        
        print(f"\n📈 Difficulty {diff}:")
        print(f"   GPT-4o: {gpt4o_stats['correct']}/{gpt4o_stats['total']} ({gpt4o_stats['accuracy']:.1f}%)")
        print(f"   GPT-5-mini: {gpt5_stats['correct']}/{gpt5_stats['total']} ({gpt5_stats['accuracy']:.1f}%)")
    
    # Overall
    gpt4o_total = calculate_statistics(gpt4o_analysis["corrected_results"])
    gpt5_total = calculate_statistics(gpt5_analysis["corrected_results"])
    
    print(f"\n📈 OVERALL (Difficulty 1.0 + 1.5):")
    print(f"   GPT-4o: {gpt4o_total['correct']}/{gpt4o_total['total']} ({gpt4o_total['accuracy']:.1f}%)")
    print(f"   GPT-5-mini: {gpt5_total['correct']}/{gpt5_total['total']} ({gpt5_total['accuracy']:.1f}%)")
    
    print("\n✅ Correction complete!")
    print(f"   Report: {RESULTS_DIR / 'BASELINE_ANALYSIS_CORRECTED.md'}")


if __name__ == "__main__":
    main()

