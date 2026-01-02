#!/usr/bin/env python3
"""
Filter MIU Levels for Difficulty 1.0 and 1.5
============================================

This script filters the distortion data to keep only the chosen μ-levels:
  CHOSEN: μ = {0.2, 0.5, 0.7, 0.9}
  
The unchosen μ-levels (0.1, 0.3, 0.4, 0.6, 0.8) are moved to a separate archive folder.

Author: Chameleon Framework
Date: December 2024
"""

import json
import csv
import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
CHOSEN_MIU_LEVELS = [0.2, 0.5, 0.7, 0.9]
UNCHOSEN_MIU_LEVELS = [0.1, 0.3, 0.4, 0.6, 0.8]
TARGET_DIFFICULTIES = [1.0, 1.5]

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "by_difficulty"
ARCHIVE_DIR = DATA_DIR / "UNCHOSEN_MIU_LEVELS"


def create_archive_structure():
    """Create the archive folder structure for unchosen μ-levels."""
    print("\n" + "=" * 60)
    print("Creating UNCHOSEN_MIU_LEVELS archive structure...")
    print("=" * 60)
    
    # Create main archive folder
    ARCHIVE_DIR.mkdir(exist_ok=True)
    
    # Create subfolders for each difficulty
    for diff in TARGET_DIFFICULTIES:
        diff_str = str(diff).replace(".", "_")
        archive_diff_dir = ARCHIVE_DIR / f"difficulty_{diff_str}"
        archive_diff_dir.mkdir(exist_ok=True)
        print(f"  ✓ Created: {archive_diff_dir}")
    
    # Create README in archive folder
    readme_content = f"""# UNCHOSEN_MIU_LEVELS Archive

This folder contains distortions with μ-levels that were NOT selected for the main evaluation.

## Chosen μ-levels (in main data): {CHOSEN_MIU_LEVELS}
## Archived μ-levels (in this folder): {UNCHOSEN_MIU_LEVELS}

## Rationale

The 4 chosen μ-levels were selected to maximize qualitative differentiation:
- μ=0.2 (Synonym Substitution): Light surface changes
- μ=0.5 (Notation Variation): Mathematical notation changes
- μ=0.7 (Format Conversion): Structural format changes
- μ=0.9 (Maximum Distortion): Aggressive transformation

The archived levels (0.1, 0.3, 0.4, 0.6, 0.8) showed significant overlap with adjacent levels
and were filtered out to improve statistical power per level.

## Contents

- difficulty_1_0/: Archived distortions for difficulty 1.0
- difficulty_1_5/: Archived distortions for difficulty 1.5

## Date Archived: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    readme_path = ARCHIVE_DIR / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"  ✓ Created README: {readme_path}")


def get_difficulty_folder_name(difficulty: float) -> str:
    """Get the folder/file name format for a difficulty level."""
    # Handle cases like 1.0 -> "1", 1.5 -> "1.5", 2.0 -> "2"
    if difficulty == int(difficulty):
        return str(int(difficulty))
    else:
        return str(difficulty)


def filter_difficulty_level(difficulty: float):
    """Filter a single difficulty level, keeping only chosen μ-levels."""
    
    diff_str = get_difficulty_folder_name(difficulty)
    diff_str_underscore = str(difficulty).replace(".", "_")
    
    # Paths
    source_dir = DATA_DIR / f"difficulty_{diff_str}"
    archive_dir = ARCHIVE_DIR / f"difficulty_{diff_str_underscore}"
    
    json_file = source_dir / f"difficulty_{diff_str}_distortions.json"
    csv_file = source_dir / f"difficulty_{diff_str}_distortions.csv"
    metadata_file = source_dir / f"difficulty_{diff_str}_metadata.json"
    
    print(f"\n{'=' * 60}")
    print(f"Processing Difficulty {difficulty}")
    print(f"{'=' * 60}")
    
    # Load current data
    print(f"\n  Loading {json_file.name}...")
    with open(json_file, 'r') as f:
        all_distortions = json.load(f)
    
    print(f"  Total distortions before filter: {len(all_distortions)}")
    
    # Split into chosen and unchosen
    chosen_distortions = [d for d in all_distortions if d["miu"] in CHOSEN_MIU_LEVELS]
    unchosen_distortions = [d for d in all_distortions if d["miu"] in UNCHOSEN_MIU_LEVELS]
    
    print(f"  Chosen (μ in {CHOSEN_MIU_LEVELS}): {len(chosen_distortions)}")
    print(f"  Unchosen (μ in {UNCHOSEN_MIU_LEVELS}): {len(unchosen_distortions)}")
    
    # Archive unchosen distortions
    print(f"\n  Archiving unchosen distortions to {archive_dir}...")
    
    # Save unchosen JSON
    unchosen_json_path = archive_dir / f"difficulty_{diff_str}_unchosen_distortions.json"
    with open(unchosen_json_path, 'w') as f:
        json.dump(unchosen_distortions, f, indent=2)
    print(f"  ✓ Saved: {unchosen_json_path.name}")
    
    # Save unchosen CSV
    unchosen_csv_path = archive_dir / f"difficulty_{diff_str}_unchosen_distortions.csv"
    if unchosen_distortions:
        # Get all unique fieldnames from all distortions
        all_fieldnames = set()
        for d in unchosen_distortions:
            all_fieldnames.update(d.keys())
        fieldnames = sorted(all_fieldnames)
        
        with open(unchosen_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(unchosen_distortions)
        print(f"  ✓ Saved: {unchosen_csv_path.name}")
    
    # Save unchosen metadata
    unchosen_metadata = {
        "difficulty_level": difficulty,
        "total_distortions": len(unchosen_distortions),
        "unique_questions": len(set(d["question_id"] for d in unchosen_distortions)),
        "miu_levels": UNCHOSEN_MIU_LEVELS,
        "archived_timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
        "reason": "Not selected for main evaluation - these μ-levels showed overlap with adjacent levels"
    }
    unchosen_metadata_path = archive_dir / f"difficulty_{diff_str}_unchosen_metadata.json"
    with open(unchosen_metadata_path, 'w') as f:
        json.dump(unchosen_metadata, f, indent=2)
    print(f"  ✓ Saved: {unchosen_metadata_path.name}")
    
    # Update main data with only chosen distortions
    print(f"\n  Updating main data files with chosen distortions only...")
    
    # Backup original files
    backup_dir = source_dir / "_backup_before_filter"
    backup_dir.mkdir(exist_ok=True)
    
    for file in [json_file, csv_file, metadata_file]:
        if file.exists():
            backup_path = backup_dir / file.name
            shutil.copy2(file, backup_path)
    print(f"  ✓ Backed up original files to {backup_dir}")
    
    # Save filtered JSON
    with open(json_file, 'w') as f:
        json.dump(chosen_distortions, f, indent=2)
    print(f"  ✓ Updated: {json_file.name} ({len(chosen_distortions)} distortions)")
    
    # Save filtered CSV
    if chosen_distortions:
        # Get all unique fieldnames from all distortions
        all_fieldnames = set()
        for d in chosen_distortions:
            all_fieldnames.update(d.keys())
        fieldnames = sorted(all_fieldnames)
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(chosen_distortions)
        print(f"  ✓ Updated: {csv_file.name}")
    
    # Update metadata
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    metadata["total_distortions"] = len(chosen_distortions)
    metadata["miu_levels"] = CHOSEN_MIU_LEVELS
    metadata["filter_applied"] = True
    metadata["filter_timestamp"] = datetime.now().strftime('%Y%m%d_%H%M%S')
    metadata["unchosen_miu_levels_archived"] = UNCHOSEN_MIU_LEVELS
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ Updated: {metadata_file.name}")
    
    return {
        "difficulty": difficulty,
        "original_count": len(all_distortions),
        "chosen_count": len(chosen_distortions),
        "archived_count": len(unchosen_distortions)
    }


def main():
    """Main function to filter μ-levels."""
    print("\n" + "=" * 60)
    print("🦎 CHAMELEON - MIU LEVEL FILTERING")
    print("=" * 60)
    print(f"\nChosen μ-levels to KEEP: {CHOSEN_MIU_LEVELS}")
    print(f"Unchosen μ-levels to ARCHIVE: {UNCHOSEN_MIU_LEVELS}")
    print(f"Target difficulties: {TARGET_DIFFICULTIES}")
    
    # Create archive structure
    create_archive_structure()
    
    # Process each difficulty level
    results = []
    for diff in TARGET_DIFFICULTIES:
        result = filter_difficulty_level(diff)
        results.append(result)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 FILTERING SUMMARY")
    print("=" * 60)
    print(f"\n{'Difficulty':<12} {'Original':<12} {'Kept':<12} {'Archived':<12}")
    print("-" * 48)
    
    total_original = 0
    total_kept = 0
    total_archived = 0
    
    for r in results:
        print(f"{r['difficulty']:<12} {r['original_count']:<12} {r['chosen_count']:<12} {r['archived_count']:<12}")
        total_original += r['original_count']
        total_kept += r['chosen_count']
        total_archived += r['archived_count']
    
    print("-" * 48)
    print(f"{'TOTAL':<12} {total_original:<12} {total_kept:<12} {total_archived:<12}")
    
    print(f"\n✅ Filtering complete!")
    print(f"   - Main data now contains only μ = {CHOSEN_MIU_LEVELS}")
    print(f"   - Archived data saved to: {ARCHIVE_DIR}")
    print(f"   - Original files backed up in each difficulty folder")


if __name__ == "__main__":
    main()

