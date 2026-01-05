#!/usr/bin/env python3
"""
Generate retry batches EXCLUDING items already submitted.

This script:
1. Loads already-submitted retry batches from data/retry_batches/
2. Loads complete retry batches from data/retry_batches_complete/
3. Generates NEW batch files with only items NOT yet submitted
"""

import json
from pathlib import Path
from typing import Dict, List, Set

# Paths
RETRY_BATCH_DIR = Path(__file__).parent / "data" / "retry_batches"
COMPLETE_BATCH_DIR = Path(__file__).parent / "data" / "retry_batches_complete"
OUTPUT_DIR = Path(__file__).parent / "data" / "retry_batches_final"

MODELS = {
    "gpt-5": "gpt-5-2025-08-07",
    "gpt-5-mini": "gpt-5-mini-2025-08-07",
}


def normalize_custom_id(custom_id: str) -> str:
    """
    Normalize custom_id by removing retry suffixes.
    
    Examples:
    - cat2_q_73dbbd0fa393_miu_0.0_retry_3000 -> cat2_q_73dbbd0fa393_miu_0.0
    - cat1_q_ac9ffea90714_miu_0.0_retry_3000_complete -> cat1_q_ac9ffea90714_miu_0.0
    """
    # Remove _retry_3000 suffix
    if custom_id.endswith('_retry_3000'):
        custom_id = custom_id[:-len('_retry_3000')]
    
    # Remove _complete suffix
    if custom_id.endswith('_complete'):
        custom_id = custom_id[:-len('_complete')]
    
    # Remove _retry_3000_complete suffix (if both present)
    if custom_id.endswith('_retry_3000_complete'):
        custom_id = custom_id[:-len('_retry_3000_complete')]
    
    return custom_id


def load_submitted_custom_ids() -> Set[str]:
    """Load custom_ids from already-submitted retry batches."""
    submitted = set()
    
    batch_files = [
        RETRY_BATCH_DIR / "gpt_5_retry_3000tokens.jsonl",
        RETRY_BATCH_DIR / "gpt_5_mini_retry_3000tokens.jsonl",
    ]
    
    for batch_file in batch_files:
        if not batch_file.exists():
            continue
        
        print(f"   Loading submitted batch: {batch_file.name}")
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    custom_id = entry.get('custom_id', '')
                    if custom_id:
                        normalized = normalize_custom_id(custom_id)
                        submitted.add(normalized)
                except json.JSONDecodeError:
                    continue
    
    return submitted


def load_complete_batch_requests() -> Dict[str, List[Dict]]:
    """Load all requests from complete retry batches, organized by model."""
    batch_files = {
        "gpt-5": COMPLETE_BATCH_DIR / "gpt_5_complete_retry_3000tokens.jsonl",
        "gpt-5-mini": COMPLETE_BATCH_DIR / "gpt_5_mini_complete_retry_3000tokens.jsonl",
    }
    
    all_requests = {}
    
    for model, batch_file in batch_files.items():
        if not batch_file.exists():
            print(f"   ⚠️  Complete batch file not found: {batch_file}")
            all_requests[model] = []
            continue
        
        print(f"   Loading complete batch: {batch_file.name}")
        requests = []
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    requests.append(entry)
                except json.JSONDecodeError:
                    continue
        
        all_requests[model] = requests
    
    return all_requests


def main():
    print("="*80)
    print("GENERATING RETRY BATCHES EXCLUDING ALREADY-SUBMITTED ITEMS")
    print("="*80)
    
    # Step 1: Load already-submitted custom_ids
    print("\n📋 Step 1: Loading already-submitted batches...")
    submitted_ids = load_submitted_custom_ids()
    print(f"   ✅ Found {len(submitted_ids)} already-submitted items")
    
    # Step 2: Load complete batch requests
    print("\n📋 Step 2: Loading complete retry batches...")
    complete_requests = load_complete_batch_requests()
    
    total_complete = sum(len(reqs) for reqs in complete_requests.values())
    print(f"   ✅ Found {total_complete} total items in complete batches")
    
    # Step 3: Filter out already-submitted items
    print("\n📋 Step 3: Filtering out already-submitted items...")
    filtered_requests = {}
    
    for model, requests in complete_requests.items():
        filtered = []
        for req in requests:
            custom_id = req.get('custom_id', '')
            normalized = normalize_custom_id(custom_id)
            
            if normalized not in submitted_ids:
                filtered.append(req)
        
        filtered_requests[model] = filtered
        print(f"   {model}: {len(requests)} total → {len(filtered)} remaining "
              f"({len(requests) - len(filtered)} already submitted)")
    
    # Step 4: Write new batch files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n💾 Step 4: Writing filtered batch files...")
    for model, requests in filtered_requests.items():
        filename = f"{model.replace('-', '_')}_final_retry_3000tokens.jsonl"
        batch_file = OUTPUT_DIR / filename
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
        
        print(f"   ✅ {batch_file.name}: {len(requests)} requests")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_submitted = len(submitted_ids)
    total_filtered = sum(len(reqs) for reqs in filtered_requests.values())
    
    print(f"\n📊 Statistics:")
    print(f"   Already submitted: {total_submitted} items")
    print(f"   Total in complete batches: {total_complete} items")
    print(f"   Remaining to submit: {total_filtered} items")
    print(f"   Overlap (already submitted): {total_complete - total_filtered} items")
    
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    
    print("\n📋 Breakdown by model:")
    for model, requests in filtered_requests.items():
        print(f"   {model}: {len(requests)} requests")
    
    print("\n✅ Next steps:")
    print("   1. Review batch files in:", OUTPUT_DIR)
    print("   2. Submit these NEW batches to OpenAI Batch API")
    print("   3. These batches contain ONLY items NOT yet submitted")
    print("="*80)


if __name__ == "__main__":
    main()

