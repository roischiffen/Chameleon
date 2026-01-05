#!/usr/bin/env python3
"""
Check for duplicate custom_ids (question+MIU combinations) in merged results files.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

RESULTS_DIR = Path("data/results_verified")

MODELS = ["gpt-5", "gpt-5-mini"]

def check_duplicates(model: str):
    """Check for duplicate custom_ids in a model's results file."""
    # Map model names to file patterns
    model_patterns = {
        "gpt-5": "gpt-5_results_*.jsonl",
        "gpt-5-mini": "gpt-5-mini_results_*.jsonl",
    }
    
    pattern = model_patterns.get(model)
    if not pattern:
        print(f"   ❌ Unknown model: {model}")
        return
    
    # Find the main results file (not backup, not retry)
    result_files = list(RESULTS_DIR.glob(pattern))
    result_files = [f for f in result_files if "backup" not in f.name and "retry" not in f.name]
    
    if not result_files:
        print(f"   ❌ No results file found for {model}")
        return
    
    result_file = result_files[0]
    print(f"\n📁 Checking: {result_file.name}")
    
    custom_ids = []
    custom_id_to_lines = defaultdict(list)
    
    with open(result_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                custom_id = entry.get('custom_id', '')
                if custom_id:
                    custom_ids.append(custom_id)
                    custom_id_to_lines[custom_id].append(line_num)
            except json.JSONDecodeError:
                continue
    
    # Count occurrences
    custom_id_counts = Counter(custom_ids)
    duplicates = {cid: count for cid, count in custom_id_counts.items() if count > 1}
    
    print(f"   Total entries: {len(custom_ids)}")
    print(f"   Unique custom_ids: {len(set(custom_ids))}")
    
    if duplicates:
        print(f"\n   ⚠️  FOUND {len(duplicates)} DUPLICATE CUSTOM_IDS:")
        for custom_id, count in sorted(duplicates.items()):
            lines = custom_id_to_lines[custom_id]
            print(f"      {custom_id}: appears {count} times (lines: {lines})")
    else:
        print(f"   ✅ No duplicates found!")
    
    return duplicates


def main():
    print("="*80)
    print("CHECKING FOR DUPLICATE CUSTOM_IDS IN MERGED RESULTS")
    print("="*80)
    
    all_duplicates = {}
    
    for model in MODELS:
        duplicates = check_duplicates(model)
        if duplicates:
            all_duplicates[model] = duplicates
    
    print("\n" + "="*80)
    if all_duplicates:
        print("❌ DUPLICATES FOUND!")
        total_duplicates = sum(len(d) for d in all_duplicates.values())
        print(f"   Total duplicate custom_ids across all models: {total_duplicates}")
    else:
        print("✅ NO DUPLICATES FOUND - All custom_ids are unique!")
    print("="*80)


if __name__ == "__main__":
    main()

