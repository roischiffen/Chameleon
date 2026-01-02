#!/usr/bin/env python3
"""
Complete Baseline Evaluation for Difficulty 1.0 and 1.5

This script:
1. Identifies which baseline questions have already been evaluated
2. Evaluates remaining questions for difficulty 1.0 and 1.5
3. Merges results with existing baseline results
4. Generates a comprehensive analysis report

Usage:
    # Check which questions are remaining (dry run)
    python omnimath_distortion_workflow/flows/complete_baseline_evaluation.py --check
    
    # Run evaluation on remaining questions
    python omnimath_distortion_workflow/flows/complete_baseline_evaluation.py --run
    
    # Run with specific difficulty only
    python omnimath_distortion_workflow/flows/complete_baseline_evaluation.py --run --difficulty 1.0

Environment:
    OPENAI_API_KEY: Your OpenAI API key (required)
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
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

try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_CONFIGS = {
    "gpt-4o": {
        "model": "gpt-4o",
        "max_tokens": 150,
        "temperature": 0
    },
    "gpt-5-mini": {
        "model": "gpt-5-mini",
        "reasoning_effort": "low",
        "max_completion_tokens": 150
    }
}

DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"
OUTPUT_DIR = project_root / "omnimath_distortion_workflow" / "evaluation" / "baseline_results"

RATE_LIMIT_DELAY = 0.5


# =============================================================================
# DATA LOADING
# =============================================================================

def load_evaluated_question_ids() -> Tuple[Set[int], Set[int]]:
    """
    Load question IDs that have already been evaluated from existing results.
    
    Returns:
        Tuple of (gpt4o_evaluated_ids, gpt5_evaluated_ids)
    """
    gpt4o_ids = set()
    gpt5_ids = set()
    
    # Load GPT-4o results
    gpt4o_file = OUTPUT_DIR / "gpt4o_results.json"
    if gpt4o_file.exists():
        with open(gpt4o_file, 'r') as f:
            results = json.load(f)
            gpt4o_ids = {r["question_id"] for r in results}
    
    # Load GPT-5-mini results
    gpt5_file = OUTPUT_DIR / "gpt5_mini_results.json"
    if gpt5_file.exists():
        with open(gpt5_file, 'r') as f:
            results = json.load(f)
            gpt5_ids = {r["question_id"] for r in results}
    
    return gpt4o_ids, gpt5_ids


def load_baseline_questions_for_difficulty(difficulty: float) -> List[Dict[str, Any]]:
    """
    Load baseline questions for a specific difficulty level.
    Handles both naming conventions: difficulty_1 and difficulty_1.0
    """
    # Try both naming conventions
    difficulty_str = str(difficulty)
    difficulty_str_alt = str(int(difficulty)) if difficulty == int(difficulty) else difficulty_str
    
    # Try with the float version first (e.g., difficulty_1.5)
    folder = DATA_DIR / f"difficulty_{difficulty_str}"
    baseline_file = folder / f"difficulty_{difficulty_str}_baseline_questions.json"
    
    # If not found, try the integer version (e.g., difficulty_1 for 1.0)
    if not baseline_file.exists():
        folder = DATA_DIR / f"difficulty_{difficulty_str_alt}"
        baseline_file = folder / f"difficulty_{difficulty_str_alt}_baseline_questions.json"
    
    if not baseline_file.exists():
        print(f"   ⚠️  Baseline file not found for difficulty {difficulty}")
        return []
    
    with open(baseline_file, 'r') as f:
        return json.load(f)


def get_unevaluated_questions(
    difficulty: float,
    evaluated_ids: Set[int]
) -> List[Dict[str, Any]]:
    """
    Get questions that haven't been evaluated yet for a specific difficulty.
    """
    all_questions = load_baseline_questions_for_difficulty(difficulty)
    
    unevaluated = [
        q for q in all_questions 
        if q["question_id"] not in evaluated_ids
    ]
    
    return unevaluated


# =============================================================================
# API CLIENT
# =============================================================================

def get_client() -> openai.OpenAI:
    """Get OpenAI client with API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
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
    """
    import re
    
    config = MODEL_CONFIGS[model_name]
    prompt = create_evaluation_prompt(question_data["original_question"])
    
    result = {
        "question_id": question_data["question_id"],
        "domain": question_data.get("domain", ""),
        "difficulty": question_data.get("difficulty", 0),
        "difficulty_category": question_data.get("difficulty_category", ""),
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
        request_params = {
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if "gpt-5" in config["model"].lower():
            if "reasoning_effort" in config:
                request_params["reasoning_effort"] = config["reasoning_effort"]
            request_params["max_completion_tokens"] = config.get("max_completion_tokens", 150)
        else:
            request_params["max_tokens"] = config.get("max_tokens", 150)
            if "temperature" in config:
                request_params["temperature"] = config["temperature"]
        
        response = client.chat.completions.create(**request_params)
        
        model_answer = response.choices[0].message.content.strip()
        
        for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*', r'^final\s+answer\s*:?\s*']:
            model_answer = re.sub(pattern, '', model_answer, flags=re.IGNORECASE)
        model_answer = model_answer.strip().rstrip('.')
        
        result["model_answer"] = model_answer
        result["api_success"] = True
        
        if response.usage:
            result["input_tokens"] = getattr(response.usage, 'prompt_tokens', None) or getattr(response.usage, 'input_tokens', None)
            result["output_tokens"] = getattr(response.usage, 'completion_tokens', None) or getattr(response.usage, 'output_tokens', None)
            
            if hasattr(response.usage, 'completion_tokens_details'):
                details = response.usage.completion_tokens_details
                if details:
                    result["reasoning_tokens"] = getattr(details, 'reasoning_tokens', None)
        
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
                print(f"   [{current:>4}/{total_evaluations}] Q{result['question_id']} | {model[:10]:>10} | {status} | {result['model_answer'][:30]}")
            
            time.sleep(RATE_LIMIT_DELAY)
    
    return results


# =============================================================================
# MERGE AND SAVE RESULTS
# =============================================================================

def merge_results(existing_file: Path, new_results: List[Dict]) -> List[Dict]:
    """
    Merge new results with existing results.
    """
    existing = []
    if existing_file.exists():
        with open(existing_file, 'r') as f:
            existing = json.load(f)
    
    # Create map of existing by question_id
    existing_map = {r["question_id"]: r for r in existing}
    
    # Add new results (overwrite if duplicate)
    for r in new_results:
        existing_map[r["question_id"]] = r
    
    # Return sorted by question_id
    merged = list(existing_map.values())
    merged.sort(key=lambda x: x["question_id"])
    
    return merged


def calculate_statistics(results: List[Dict], difficulty: Optional[float] = None) -> Dict:
    """Calculate statistics from evaluation results."""
    if difficulty is not None:
        results = [r for r in results if r.get("difficulty") == difficulty]
    
    total = len(results)
    scorable = [r for r in results if r["match_type"] != "text_answer"]
    correct = sum(1 for r in scorable if r["is_correct"])
    text_answers = sum(1 for r in results if r["match_type"] == "text_answer")
    api_errors = sum(1 for r in results if r.get("api_error"))
    
    return {
        "total": total,
        "scorable": len(scorable),
        "correct": correct,
        "accuracy": correct / len(scorable) * 100 if scorable else 0,
        "text_answers": text_answers,
        "api_errors": api_errors
    }


def generate_comprehensive_report(
    gpt4o_results: List[Dict],
    gpt5_results: List[Dict],
    target_difficulties: List[float] = [1.0, 1.5]
) -> str:
    """
    Generate a comprehensive baseline success analysis report.
    """
    lines = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.append("# 📊 Comprehensive Baseline Success Analysis Report")
    lines.append("")
    lines.append(f"*Generated: {timestamp}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # ==========================================================================
    # EXECUTIVE SUMMARY
    # ==========================================================================
    lines.append("## 1. Executive Summary")
    lines.append("")
    
    # Overall stats for target difficulties
    gpt4o_filtered = [r for r in gpt4o_results if r.get("difficulty") in target_difficulties]
    gpt5_filtered = [r for r in gpt5_results if r.get("difficulty") in target_difficulties]
    
    gpt4o_total_stats = calculate_statistics(gpt4o_filtered)
    gpt5_total_stats = calculate_statistics(gpt5_filtered)
    
    lines.append("### Key Findings")
    lines.append("")
    lines.append(f"| Metric | GPT-4o | GPT-5-mini |")
    lines.append("|--------|--------|------------|")
    lines.append(f"| **Total Questions Evaluated** | {gpt4o_total_stats['total']} | {gpt5_total_stats['total']} |")
    lines.append(f"| **Scorable Questions** | {gpt4o_total_stats['scorable']} | {gpt5_total_stats['scorable']} |")
    lines.append(f"| **Correct Answers** | {gpt4o_total_stats['correct']} | {gpt5_total_stats['correct']} |")
    lines.append(f"| **Overall Accuracy** | {gpt4o_total_stats['accuracy']:.1f}% | {gpt5_total_stats['accuracy']:.1f}% |")
    lines.append(f"| **Text Answers (Manual Review)** | {gpt4o_total_stats['text_answers']} | {gpt5_total_stats['text_answers']} |")
    lines.append("")
    
    # Winner summary
    if gpt5_total_stats['accuracy'] > gpt4o_total_stats['accuracy']:
        diff = gpt5_total_stats['accuracy'] - gpt4o_total_stats['accuracy']
        lines.append(f"**🏆 Overall Winner: GPT-5-mini** (outperforms GPT-4o by {diff:.1f} percentage points)")
    elif gpt4o_total_stats['accuracy'] > gpt5_total_stats['accuracy']:
        diff = gpt4o_total_stats['accuracy'] - gpt5_total_stats['accuracy']
        lines.append(f"**🏆 Overall Winner: GPT-4o** (outperforms GPT-5-mini by {diff:.1f} percentage points)")
    else:
        lines.append("**🏆 Overall: Both models perform equally**")
    lines.append("")
    
    # ==========================================================================
    # DIFFICULTY LEVEL ANALYSIS
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## 2. Performance by Difficulty Level")
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
        
        # Winner for this difficulty
        if gpt5_diff_stats['accuracy'] > gpt4o_diff_stats['accuracy']:
            diff_val = gpt5_diff_stats['accuracy'] - gpt4o_diff_stats['accuracy']
            lines.append(f"**Winner at Difficulty {diff}: GPT-5-mini** (+{diff_val:.1f}%)")
        elif gpt4o_diff_stats['accuracy'] > gpt5_diff_stats['accuracy']:
            diff_val = gpt4o_diff_stats['accuracy'] - gpt5_diff_stats['accuracy']
            lines.append(f"**Winner at Difficulty {diff}: GPT-4o** (+{diff_val:.1f}%)")
        else:
            lines.append(f"**Difficulty {diff}: Tie**")
        lines.append("")
    
    # ==========================================================================
    # DOMAIN ANALYSIS
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## 3. Performance by Mathematical Domain")
    lines.append("")
    
    # Group by domain for target difficulties
    domain_stats = defaultdict(lambda: {"gpt4o": [], "gpt5": []})
    
    for r in gpt4o_filtered:
        domain = r.get("domain", "Unknown")
        domain_stats[domain]["gpt4o"].append(r)
    
    for r in gpt5_filtered:
        domain = r.get("domain", "Unknown")
        domain_stats[domain]["gpt5"].append(r)
    
    # Sort by question count
    sorted_domains = sorted(domain_stats.items(), key=lambda x: len(x[1]["gpt4o"]), reverse=True)
    
    lines.append("| Domain | Questions | GPT-4o Accuracy | GPT-5-mini Accuracy | Winner |")
    lines.append("|--------|-----------|-----------------|---------------------|--------|")
    
    domain_winners = {"gpt4o": 0, "gpt5": 0, "tie": 0}
    
    for domain, data in sorted_domains[:20]:  # Top 20 domains
        gpt4o_dom = calculate_statistics(data["gpt4o"])
        gpt5_dom = calculate_statistics(data["gpt5"])
        
        if gpt5_dom['accuracy'] > gpt4o_dom['accuracy']:
            winner = "GPT-5-mini"
            domain_winners["gpt5"] += 1
        elif gpt4o_dom['accuracy'] > gpt5_dom['accuracy']:
            winner = "GPT-4o"
            domain_winners["gpt4o"] += 1
        else:
            winner = "Tie"
            domain_winners["tie"] += 1
        
        domain_short = domain[:50] + "..." if len(domain) > 50 else domain
        lines.append(f"| {domain_short} | {gpt4o_dom['total']} | {gpt4o_dom['accuracy']:.1f}% | {gpt5_dom['accuracy']:.1f}% | {winner} |")
    
    lines.append("")
    lines.append(f"**Domain-level summary:** GPT-4o wins in {domain_winners['gpt4o']} domains, GPT-5-mini wins in {domain_winners['gpt5']} domains, {domain_winners['tie']} ties")
    lines.append("")
    
    # ==========================================================================
    # DETAILED COMPARISON - WHERE MODELS DIFFER
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## 4. Detailed Model Comparison")
    lines.append("")
    lines.append("### Questions Where Models Disagreed")
    lines.append("")
    
    # Find questions where one got it right and the other wrong
    gpt4o_map = {r["question_id"]: r for r in gpt4o_filtered}
    gpt5_map = {r["question_id"]: r for r in gpt5_filtered}
    
    gpt4o_only_correct = []
    gpt5_only_correct = []
    both_correct = []
    both_wrong = []
    
    for qid in set(gpt4o_map.keys()) & set(gpt5_map.keys()):
        g4 = gpt4o_map[qid]
        g5 = gpt5_map[qid]
        
        g4_correct = g4["is_correct"] and g4["match_type"] != "text_answer"
        g5_correct = g5["is_correct"] and g5["match_type"] != "text_answer"
        
        if g4_correct and not g5_correct:
            gpt4o_only_correct.append(qid)
        elif g5_correct and not g4_correct:
            gpt5_only_correct.append(qid)
        elif g4_correct and g5_correct:
            both_correct.append(qid)
        else:
            both_wrong.append(qid)
    
    lines.append(f"| Category | Count | Percentage |")
    lines.append("|----------|-------|------------|")
    total_common = len(gpt4o_only_correct) + len(gpt5_only_correct) + len(both_correct) + len(both_wrong)
    if total_common > 0:
        lines.append(f"| Both models correct | {len(both_correct)} | {len(both_correct)/total_common*100:.1f}% |")
        lines.append(f"| Both models wrong | {len(both_wrong)} | {len(both_wrong)/total_common*100:.1f}% |")
        lines.append(f"| Only GPT-4o correct | {len(gpt4o_only_correct)} | {len(gpt4o_only_correct)/total_common*100:.1f}% |")
        lines.append(f"| Only GPT-5-mini correct | {len(gpt5_only_correct)} | {len(gpt5_only_correct)/total_common*100:.1f}% |")
    lines.append("")
    
    # Sample of questions where models differed
    if gpt4o_only_correct[:5]:
        lines.append("#### Sample Questions - Only GPT-4o Correct")
        lines.append("")
        lines.append("| Q_ID | Difficulty | Domain | Ground Truth | GPT-4o Answer | GPT-5-mini Answer |")
        lines.append("|------|------------|--------|--------------|---------------|-------------------|")
        for qid in gpt4o_only_correct[:5]:
            g4 = gpt4o_map[qid]
            g5 = gpt5_map[qid]
            domain_short = g4["domain"].split(" -> ")[-1][:20] if g4["domain"] else ""
            lines.append(f"| {qid} | {g4['difficulty']} | {domain_short} | {g4['ground_truth'][:15]} | {g4['model_answer'][:15]} | {g5['model_answer'][:15]} |")
        lines.append("")
    
    if gpt5_only_correct[:5]:
        lines.append("#### Sample Questions - Only GPT-5-mini Correct")
        lines.append("")
        lines.append("| Q_ID | Difficulty | Domain | Ground Truth | GPT-4o Answer | GPT-5-mini Answer |")
        lines.append("|------|------------|--------|--------------|---------------|-------------------|")
        for qid in gpt5_only_correct[:5]:
            g4 = gpt4o_map[qid]
            g5 = gpt5_map[qid]
            domain_short = g4["domain"].split(" -> ")[-1][:20] if g4["domain"] else ""
            lines.append(f"| {qid} | {g4['difficulty']} | {domain_short} | {g4['ground_truth'][:15]} | {g4['model_answer'][:15]} | {g5['model_answer'][:15]} |")
        lines.append("")
    
    # ==========================================================================
    # STRENGTHS AND WEAKNESSES
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## 5. Model Strengths and Weaknesses")
    lines.append("")
    
    # Find domains where each model excels
    gpt4o_strong_domains = []
    gpt5_strong_domains = []
    
    for domain, data in sorted_domains:
        if len(data["gpt4o"]) >= 3:  # Minimum sample size
            gpt4o_dom = calculate_statistics(data["gpt4o"])
            gpt5_dom = calculate_statistics(data["gpt5"])
            
            if gpt4o_dom['accuracy'] > gpt5_dom['accuracy'] + 15:  # 15% margin
                gpt4o_strong_domains.append((domain, gpt4o_dom['accuracy'], gpt5_dom['accuracy']))
            elif gpt5_dom['accuracy'] > gpt4o_dom['accuracy'] + 15:
                gpt5_strong_domains.append((domain, gpt5_dom['accuracy'], gpt4o_dom['accuracy']))
    
    lines.append("### GPT-4o Strengths")
    lines.append("")
    if gpt4o_strong_domains:
        for domain, g4_acc, g5_acc in gpt4o_strong_domains[:5]:
            domain_short = domain.split(" -> ")[-1] if " -> " in domain else domain
            lines.append(f"- **{domain_short}**: {g4_acc:.1f}% vs {g5_acc:.1f}% (GPT-5-mini)")
    else:
        lines.append("- No domains with significant advantage (>15%)")
    lines.append("")
    
    lines.append("### GPT-5-mini Strengths")
    lines.append("")
    if gpt5_strong_domains:
        for domain, g5_acc, g4_acc in gpt5_strong_domains[:5]:
            domain_short = domain.split(" -> ")[-1] if " -> " in domain else domain
            lines.append(f"- **{domain_short}**: {g5_acc:.1f}% vs {g4_acc:.1f}% (GPT-4o)")
    else:
        lines.append("- No domains with significant advantage (>15%)")
    lines.append("")
    
    # ==========================================================================
    # RESEARCH IMPLICATIONS
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## 6. Research Implications for Chameleon Project")
    lines.append("")
    lines.append("### Baseline Establishment")
    lines.append("")
    lines.append("This baseline evaluation establishes the ground truth performance of both models")
    lines.append("on undistorted questions. Key implications:")
    lines.append("")
    lines.append(f"1. **Baseline Accuracy Benchmark**: GPT-4o achieves {gpt4o_total_stats['accuracy']:.1f}%, GPT-5-mini achieves {gpt5_total_stats['accuracy']:.1f}%")
    lines.append("2. **Distortion Impact Measurement**: Any accuracy degradation in distorted questions")
    lines.append("   should be measured against these baselines")
    lines.append("3. **Model Robustness**: The model with lower baseline accuracy but similar")
    lines.append("   performance on distorted questions demonstrates higher robustness")
    lines.append("")
    
    lines.append("### Expected Distortion Analysis Framework")
    lines.append("")
    lines.append("When analyzing distorted question performance:")
    lines.append("")
    lines.append("| Metric | Formula |")
    lines.append("|--------|---------|")
    lines.append("| Accuracy Degradation | `(Baseline% - Distorted%) / Baseline%` |")
    lines.append("| Robustness Score | `1 - Accuracy Degradation` |")
    lines.append("| Relative Resilience | `Model_Robustness / Max_Robustness` |")
    lines.append("")
    
    lines.append("### Recommendations")
    lines.append("")
    lines.append("1. **Focus Distortion Testing**: Priority should be given to domains where both")
    lines.append("   models perform well at baseline (to measure true robustness)")
    lines.append("2. **MIU Level Correlation**: Analyze how distortion levels (0.2, 0.5, 0.7, 0.9)")
    lines.append("   correlate with accuracy drops from these baselines")
    lines.append("3. **Domain-Specific Vulnerability**: Identify which mathematical domains are")
    lines.append("   most susceptible to distortion for each model")
    lines.append("")
    
    # ==========================================================================
    # DETAILED RESULTS BY DIFFICULTY
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## 7. Detailed Results Tables")
    lines.append("")
    
    for diff in target_difficulties:
        lines.append(f"### Difficulty {diff} - Question by Question")
        lines.append("")
        lines.append("| Q_ID | Domain | GPT-4o | GPT-5-mini | Ground Truth |")
        lines.append("|------|--------|--------|------------|--------------|")
        
        diff_questions = sorted(
            [qid for qid in gpt4o_map.keys() if gpt4o_map[qid].get("difficulty") == diff]
        )
        
        for qid in diff_questions:
            g4 = gpt4o_map.get(qid)
            g5 = gpt5_map.get(qid)
            
            if g4 and g5:
                g4_status = "✅" if g4["is_correct"] else ("⚠️" if g4["match_type"] == "text_answer" else "❌")
                g5_status = "✅" if g5["is_correct"] else ("⚠️" if g5["match_type"] == "text_answer" else "❌")
                domain_short = g4["domain"].split(" -> ")[-1][:20] if g4["domain"] else ""
                gt = g4["ground_truth"][:15] if len(g4["ground_truth"]) > 15 else g4["ground_truth"]
                lines.append(f"| {qid} | {domain_short} | {g4_status} | {g5_status} | {gt} |")
        
        lines.append("")
    
    # ==========================================================================
    # APPENDIX
    # ==========================================================================
    lines.append("---")
    lines.append("")
    lines.append("## Appendix: Data Files")
    lines.append("")
    lines.append("- **GPT-4o Results**: `evaluation/baseline_results/gpt4o_results.json`")
    lines.append("- **GPT-5-mini Results**: `evaluation/baseline_results/gpt5_mini_results.json`")
    lines.append("- **Combined Results**: `evaluation/baseline_results/baseline_results.json`")
    lines.append("- **Statistics**: `evaluation/baseline_results/baseline_statistics.json`")
    lines.append("")
    
    return "\n".join(lines)


def save_all_results(
    gpt4o_results: List[Dict],
    gpt5_results: List[Dict],
    output_dir: Path
) -> None:
    """Save all results and generate reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save individual model results
    gpt4o_file = output_dir / "gpt4o_results.json"
    with open(gpt4o_file, 'w') as f:
        json.dump(gpt4o_results, f, indent=2)
    print(f"   💾 GPT-4o results: {gpt4o_file}")
    
    gpt5_file = output_dir / "gpt5_mini_results.json"
    with open(gpt5_file, 'w') as f:
        json.dump(gpt5_results, f, indent=2)
    print(f"   💾 GPT-5-mini results: {gpt5_file}")
    
    # Save combined results
    combined = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "total_gpt4o_questions": len(gpt4o_results),
            "total_gpt5_questions": len(gpt5_results),
            "models": ["gpt-4o", "gpt-5-mini"]
        },
        "gpt4o": gpt4o_results,
        "gpt5_mini": gpt5_results
    }
    combined_file = output_dir / "baseline_results.json"
    with open(combined_file, 'w') as f:
        json.dump(combined, f, indent=2)
    print(f"   💾 Combined results: {combined_file}")
    
    # Save statistics
    stats = {
        "generated": datetime.now().isoformat(),
        "difficulty_1.0": {
            "gpt4o": calculate_statistics(gpt4o_results, 1.0),
            "gpt5_mini": calculate_statistics(gpt5_results, 1.0)
        },
        "difficulty_1.5": {
            "gpt4o": calculate_statistics(gpt4o_results, 1.5),
            "gpt5_mini": calculate_statistics(gpt5_results, 1.5)
        },
        "combined": {
            "gpt4o": calculate_statistics([r for r in gpt4o_results if r.get("difficulty") in [1.0, 1.5]]),
            "gpt5_mini": calculate_statistics([r for r in gpt5_results if r.get("difficulty") in [1.0, 1.5]])
        }
    }
    stats_file = output_dir / "baseline_statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"   💾 Statistics: {stats_file}")
    
    # Generate comprehensive report
    report = generate_comprehensive_report(gpt4o_results, gpt5_results)
    report_file = output_dir / "BASELINE_ANALYSIS.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"   📄 Analysis report: {report_file}")
    
    # Generate comparison CSV
    comparison_data = []
    gpt4o_map = {r["question_id"]: r for r in gpt4o_results}
    gpt5_map = {r["question_id"]: r for r in gpt5_results}
    
    for qid in sorted(set(gpt4o_map.keys()) | set(gpt5_map.keys())):
        g4 = gpt4o_map.get(qid, {})
        g5 = gpt5_map.get(qid, {})
        
        row = {
            "question_id": qid,
            "difficulty": g4.get("difficulty") or g5.get("difficulty"),
            "domain": g4.get("domain") or g5.get("domain"),
            "ground_truth": g4.get("ground_truth") or g5.get("ground_truth"),
            "gpt4o_answer": g4.get("model_answer", ""),
            "gpt4o_correct": g4.get("is_correct", False),
            "gpt5_answer": g5.get("model_answer", ""),
            "gpt5_correct": g5.get("is_correct", False),
            "agreement": g4.get("is_correct", False) == g5.get("is_correct", False)
        }
        comparison_data.append(row)
    
    # Write CSV
    import csv
    csv_file = output_dir / "baseline_comparison.csv"
    if comparison_data:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=comparison_data[0].keys())
            writer.writeheader()
            writer.writerows(comparison_data)
        print(f"   📊 Comparison CSV: {csv_file}")
    
    # Write comparison JSON
    comparison_json_file = output_dir / "baseline_comparison.json"
    with open(comparison_json_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)
    print(f"   📊 Comparison JSON: {comparison_json_file}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Complete baseline evaluation for difficulty 1.0 and 1.5",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--check", action="store_true",
                        help="Check which questions are remaining (dry run)")
    parser.add_argument("--run", action="store_true",
                        help="Run evaluation on remaining questions")
    parser.add_argument("--difficulty", type=float, choices=[1.0, 1.5],
                        help="Only evaluate specific difficulty level")
    parser.add_argument("--regenerate-report", action="store_true",
                        help="Only regenerate the analysis report from existing results")
    
    args = parser.parse_args()
    
    if not args.check and not args.run and not args.regenerate_report:
        parser.error("Must specify --check, --run, or --regenerate-report")
    
    print("=" * 70)
    print("📊 Complete Baseline Evaluation for Difficulty 1.0 and 1.5")
    print("=" * 70)
    
    # Determine target difficulties
    target_difficulties = [1.0, 1.5]
    if args.difficulty:
        target_difficulties = [args.difficulty]
    
    print(f"\n🎯 Target difficulties: {target_difficulties}")
    
    # Load already evaluated question IDs
    print("\n📂 Loading existing evaluation results...")
    gpt4o_evaluated, gpt5_evaluated = load_evaluated_question_ids()
    print(f"   GPT-4o: {len(gpt4o_evaluated)} questions already evaluated")
    print(f"   GPT-5-mini: {len(gpt5_evaluated)} questions already evaluated")
    
    # For regenerate-report mode
    if args.regenerate_report:
        print("\n📝 Regenerating analysis report from existing results...")
        
        # Load existing results
        gpt4o_file = OUTPUT_DIR / "gpt4o_results.json"
        gpt5_file = OUTPUT_DIR / "gpt5_mini_results.json"
        
        with open(gpt4o_file, 'r') as f:
            gpt4o_results = json.load(f)
        with open(gpt5_file, 'r') as f:
            gpt5_results = json.load(f)
        
        # Filter to target difficulties
        gpt4o_filtered = [r for r in gpt4o_results if r.get("difficulty") in target_difficulties]
        gpt5_filtered = [r for r in gpt5_results if r.get("difficulty") in target_difficulties]
        
        # Save results
        save_all_results(gpt4o_filtered, gpt5_filtered, OUTPUT_DIR)
        
        print("\n✅ Report regenerated successfully!")
        return
    
    # Find unevaluated questions for each difficulty
    all_unevaluated = []
    
    for diff in target_difficulties:
        print(f"\n📊 Difficulty {diff}:")
        
        # Load baseline questions
        baseline_questions = load_baseline_questions_for_difficulty(diff)
        print(f"   Total baseline questions: {len(baseline_questions)}")
        
        # Get questions evaluated by both models
        both_evaluated = gpt4o_evaluated & gpt5_evaluated
        
        # Find unevaluated
        unevaluated = get_unevaluated_questions(diff, both_evaluated)
        print(f"   Already evaluated (both models): {len(baseline_questions) - len(unevaluated)}")
        print(f"   Remaining to evaluate: {len(unevaluated)}")
        
        all_unevaluated.extend(unevaluated)
    
    print(f"\n📋 Total questions to evaluate: {len(all_unevaluated)}")
    
    if args.check:
        print("\n✅ Check complete! Use --run to evaluate remaining questions.")
        return
    
    if not all_unevaluated:
        print("\n✅ All questions already evaluated! Regenerating report...")
        
        # Load existing results
        gpt4o_file = OUTPUT_DIR / "gpt4o_results.json"
        gpt5_file = OUTPUT_DIR / "gpt5_mini_results.json"
        
        with open(gpt4o_file, 'r') as f:
            gpt4o_results = json.load(f)
        with open(gpt5_file, 'r') as f:
            gpt5_results = json.load(f)
        
        # Filter to target difficulties
        gpt4o_filtered = [r for r in gpt4o_results if r.get("difficulty") in target_difficulties]
        gpt5_filtered = [r for r in gpt5_results if r.get("difficulty") in target_difficulties]
        
        # Save results and generate report
        save_all_results(gpt4o_filtered, gpt5_filtered, OUTPUT_DIR)
        
        print("\n✅ Report regenerated successfully!")
        return
    
    # ==========================================================================
    # RUN EVALUATION
    # ==========================================================================
    
    print("\n" + "=" * 70)
    print("🚀 Running Evaluation")
    print("=" * 70)
    
    # Get client
    client = get_client()
    
    # Check model availability
    print("\n🔍 Checking model availability...")
    models = []
    for model in ["gpt-4o", "gpt-5-mini"]:
        if check_model_availability(client, model):
            print(f"   ✅ {model} is available")
            models.append(model)
        else:
            print(f"   ❌ {model} is NOT available")
    
    if not models:
        print("\n❌ No models available!")
        sys.exit(1)
    
    # Estimate time
    total_calls = len(all_unevaluated) * len(models)
    est_time = total_calls * (RATE_LIMIT_DELAY + 0.5) / 60
    
    print(f"\n⏱️  Estimated time: {est_time:.1f} minutes")
    print(f"📊 Total API calls: {total_calls}")
    
    # Run evaluation
    results = run_evaluation(client, all_unevaluated, models)
    
    # Merge with existing results
    print("\n📥 Merging with existing results...")
    
    gpt4o_file = OUTPUT_DIR / "gpt4o_results.json"
    gpt5_file = OUTPUT_DIR / "gpt5_mini_results.json"
    
    gpt4o_merged = merge_results(gpt4o_file, results.get("gpt-4o", []))
    gpt5_merged = merge_results(gpt5_file, results.get("gpt-5-mini", []))
    
    # Filter to target difficulties for the report
    gpt4o_filtered = [r for r in gpt4o_merged if r.get("difficulty") in target_difficulties]
    gpt5_filtered = [r for r in gpt5_merged if r.get("difficulty") in target_difficulties]
    
    # Save all results
    print("\n💾 Saving results...")
    save_all_results(gpt4o_filtered, gpt5_filtered, OUTPUT_DIR)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 EVALUATION COMPLETE")
    print("=" * 70)
    
    for diff in target_difficulties:
        gpt4o_stats = calculate_statistics(gpt4o_filtered, diff)
        gpt5_stats = calculate_statistics(gpt5_filtered, diff)
        
        print(f"\n📈 Difficulty {diff}:")
        print(f"   GPT-4o: {gpt4o_stats['correct']}/{gpt4o_stats['scorable']} ({gpt4o_stats['accuracy']:.1f}%)")
        print(f"   GPT-5-mini: {gpt5_stats['correct']}/{gpt5_stats['scorable']} ({gpt5_stats['accuracy']:.1f}%)")
    
    print("\n✅ All done! Check the analysis report at:")
    print(f"   {OUTPUT_DIR / 'BASELINE_ANALYSIS.md'}")


if __name__ == "__main__":
    main()

