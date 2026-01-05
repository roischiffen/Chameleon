#!/usr/bin/env python3
"""
Check for questions that appear more than 5 times (baseline + 4 distortions).
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter

RESULTS_DIR = Path("data/results_verified")

MODELS = ["gpt-5", "gpt-5-mini"]

def parse_question_id(custom_id: str):
    """Extract question identifier from custom_id."""
    # Format: cat{N}_q_{question_id}_miu_{miu}
    match = re.match(r'cat(\d+)_q_([a-f0-9]+)_miu_([\d.]+)', custom_id)
    if match:
        category = int(match.group(1))
        question_id = match.group(2)
        miu = float(match.group(3))
        return category, question_id, miu
    return None, None, None


def check_question_duplicates(model: str):
    """Check for questions appearing more than 5 times."""
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
    
    question_counts = defaultdict(lambda: defaultdict(set))  # category -> question_id -> set of MIUs
    
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
                        question_counts[category][question_id].add(miu)
            except json.JSONDecodeError:
                continue
    
    # Check for duplicates
    duplicates_found = False
    for category in sorted(question_counts.keys()):
        for question_id in sorted(question_counts[category].keys()):
            mius = question_counts[category][question_id]
            if len(mius) > 5:
                duplicates_found = True
                print(f"\n   ⚠️  Question cat{category}_q_{question_id}: appears {len(mius)} times!")
                print(f"      MIU levels: {sorted(mius)}")
    
    if not duplicates_found:
        print(f"   ✅ No questions appear more than 5 times!")
    
    # Summary statistics
    total_questions = sum(len(questions) for questions in question_counts.values())
    questions_with_5_mius = sum(1 for questions in question_counts.values() 
                                 for qid, mius in questions.items() if len(mius) == 5)
    questions_with_less_than_5 = sum(1 for questions in question_counts.values() 
                                      for qid, mius in questions.items() if len(mius) < 5)
    
    print(f"\n   Summary:")
    print(f"      Total unique questions: {total_questions}")
    print(f"      Questions with 5 MIU levels: {questions_with_5_mius}")
    print(f"      Questions with <5 MIU levels: {questions_with_less_than_5}")
    
    return duplicates_found


def main():
    print("="*80)
    print("CHECKING FOR QUESTIONS APPEARING MORE THAN 5 TIMES")
    print("="*80)
    
    all_duplicates = False
    
    for model in MODELS:
        has_duplicates = check_question_duplicates(model)
        if has_duplicates:
            all_duplicates = True
    
    print("\n" + "="*80)
    if all_duplicates:
        print("❌ DUPLICATES FOUND!")
    else:
        print("✅ NO DUPLICATES - No questions appear more than 5 times!")
    print("="*80)


if __name__ == "__main__":
    main()

