#!/usr/bin/env python3
"""
Fix duplicate entries in merged results files by removing entries with _retry_3000 suffix
that duplicate normalized entries.
"""

import json
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path("data/results_verified")

MODELS = {
    "gpt-5": "gpt-5_results_20260105_024528.jsonl",
    "gpt-5-mini": "gpt-5-mini_results_20260105_024524.jsonl",
}


def normalize_custom_id(custom_id: str) -> str:
    """Normalize custom_id by removing retry suffixes."""
    if custom_id.endswith('_retry_3000_complete'):
        return custom_id[:-len('_retry_3000_complete')]
    if custom_id.endswith('_retry_3000'):
        return custom_id[:-len('_retry_3000')]
    if custom_id.endswith('_complete'):
        return custom_id[:-len('_complete')]
    return custom_id


def fix_duplicates(model: str, filename: str):
    """Remove duplicate entries with _retry_3000 suffix."""
    result_file = RESULTS_DIR / filename
    
    print(f"\n📁 Processing: {filename}")
    
    # Load all entries
    entries = []
    normalized_seen = set()
    duplicates_removed = 0
    
    with open(result_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                custom_id = entry.get('custom_id', '')
                if not custom_id:
                    entries.append(entry)
                    continue
                
                normalized = normalize_custom_id(custom_id)
                
                # If normalized version already seen, skip this entry (it's a duplicate)
                if normalized in normalized_seen:
                    duplicates_removed += 1
                    print(f"   Removing duplicate: {custom_id} (normalized: {normalized})")
                    continue
                
                # Mark as seen and add entry with normalized custom_id
                normalized_seen.add(normalized)
                entry['custom_id'] = normalized  # Normalize the custom_id
                entries.append(entry)
                
            except json.JSONDecodeError as e:
                print(f"   ⚠️  Error parsing line {line_num}: {e}")
                continue
    
    # Write back
    backup_file = result_file.with_suffix('.jsonl.backup2')
    result_file.rename(backup_file)
    print(f"   📦 Created backup: {backup_file.name}")
    
    with open(result_file, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"   ✅ Fixed: Removed {duplicates_removed} duplicates")
    print(f"   ✅ Final count: {len(entries)} entries (expected: 1500)")
    
    return duplicates_removed, len(entries)


def main():
    print("="*80)
    print("FIXING DUPLICATE ENTRIES IN MERGED RESULTS")
    print("="*80)
    
    total_removed = 0
    
    for model, filename in MODELS.items():
        removed, final_count = fix_duplicates(model, filename)
        total_removed += removed
    
    print("\n" + "="*80)
    print(f"✅ COMPLETE: Removed {total_removed} duplicate entries total")
    print("="*80)


if __name__ == "__main__":
    main()

