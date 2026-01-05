#!/usr/bin/env python3
"""
Check how many MIU levels each question has - should be exactly 5.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path("data/results_verified")

MODELS = ["gpt-5", "gpt-5-mini"]

def parse_question_id(custom_id: str):
    """Extract question identifier from custom_id."""
    match = re.match(r'cat(\d+)_q_([a-f0-9]+)_miu_([\d.]+)', custom_id)
    if match:
        category = int(match.group(1))
        question_id = match.group(2)
        miu = float(match.group(3))
        return category, question_id, miu
    return None, None, None


def check_miu_levels_per_question(model: str):
    """Check MIU levels per question."""
    model_patterns = {
        "gpt-5": "gpt-5_results_*.jsonl",
        "gpt-5-mini": "gpt-5-mini_results_*.jsonl",
    }
    
    pattern = model_patterns.get(model)
    if not pattern:
        print(f"   ❌ Unknown model: {model}")
        return
    
    result_files = list(RESULTS_DIR.glob(pattern))
    result_files = [f for f in result_files if "backup" not in f.name and "retry" not in f.name]
    
    if not result_files:
        print(f"   ❌ No results file found for {model}")
        return
    
    result_file = result_files[0]
    print(f"\n📁 Checking: {result_file.name}")
    
    question_mius = defaultdict(lambda: defaultdict(set))  # category -> question_id -> set of MIUs
    
    with open(result_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                custom_id = entry.get('custom_id', '')
                if custom_id:
                    category, question_id, miu = parse_question_id(custom_id)
                    if category and question_id and miu is not None:
                        question_mius[category][question_id].add(miu)
            except json.JSONDecodeError:
                continue
    
    # Check for questions with more or less than 5 MIU levels
    issues_found = False
    
    for category in sorted(question_mius.keys()):
        questions_with_issues = []
        for question_id in sorted(question_mius[category].keys()):
            mius = question_mius[category][question_id]
            if len(mius) != 5:
                issues_found = True
                questions_with_issues.append((question_id, len(mius), sorted(mius)))
        
        if questions_with_issues:
            print(f"\n   ⚠️  Category {category} - Questions with issues:")
            for qid, count, mius in questions_with_issues:
                print(f"      cat{category}_q_{qid}: {count} MIU levels - {mius}")
        else:
            print(f"\n   ✅ Category {category}: All 100 questions have exactly 5 MIU levels")
    
    # Summary
    total_questions = sum(len(questions) for questions in question_mius.values())
    questions_with_5 = sum(1 for questions in question_mius.values() 
                           for qid, mius in [(qid, questions[qid]) for qid in questions.keys()]
                           if len(mius) == 5)
    questions_with_more_than_5 = sum(1 for questions in question_mius.values() 
                                     for qid, mius in [(qid, questions[qid]) for qid in questions.keys()]
                                     if len(mius) > 5)
    questions_with_less_than_5 = sum(1 for questions in question_mius.values() 
                                     for qid, mius in [(qid, questions[qid]) for qid in questions.keys()]
                                     if len(mius) < 5)
    
    print(f"\n   Summary:")
    print(f"      Total unique questions: {total_questions}")
    print(f"      Questions with exactly 5 MIU levels: {questions_with_5}")
    print(f"      Questions with >5 MIU levels: {questions_with_more_than_5}")
    print(f"      Questions with <5 MIU levels: {questions_with_less_than_5}")
    
    return issues_found


def main():
    print("="*80)
    print("CHECKING MIU LEVELS PER QUESTION (should be exactly 5)")
    print("="*80)
    
    all_issues = False
    
    for model in MODELS:
        has_issues = check_miu_levels_per_question(model)
        if has_issues:
            all_issues = True
    
    print("\n" + "="*80)
    if all_issues:
        print("❌ ISSUES FOUND - Some questions don't have exactly 5 MIU levels!")
    else:
        print("✅ ALL QUESTIONS HAVE EXACTLY 5 MIU LEVELS!")
    print("="*80)


if __name__ == "__main__":
    main()

