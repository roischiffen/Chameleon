#!/usr/bin/env python3
"""
Migrate validated batch to by_difficulty folder.
Handles deduplication and proper merging.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Union


def load_json(path: Path) -> Union[dict, list]:
    """Load JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def save_json(path: Path, data: Union[dict, list], indent: int = 2):
    """Save JSON file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent)


def migrate_batch(batch_file: Path, difficulty: float):
    """Migrate a validated batch to by_difficulty folder."""
    
    # Paths
    base_dir = Path(__file__).parent.parent / "data"
    difficulty_str = str(difficulty).replace('.', '_')
    if difficulty == 1.0:
        difficulty_folder = base_dir / "by_difficulty" / "difficulty_1"
    elif difficulty == 1.5:
        difficulty_folder = base_dir / "by_difficulty" / "difficulty_1.5"
    else:
        difficulty_folder = base_dir / "by_difficulty" / f"difficulty_{difficulty_str}"
    
    # Handle file naming (difficulty_1 vs difficulty_1.5)
    if difficulty == 1.0:
        file_prefix = "difficulty_1"
    elif difficulty == 1.5:
        file_prefix = "difficulty_1.5"
    else:
        file_prefix = f"difficulty_{difficulty}"
    
    distortions_file = difficulty_folder / f"{file_prefix}_distortions.json"
    metadata_file = difficulty_folder / f"{file_prefix}_metadata.json"
    existing_ids_file = base_dir / "existing_question_ids.json"
    
    # Load files
    print(f"Loading batch file: {batch_file}")
    batch_data = load_json(batch_file)
    
    print(f"Loading existing distortions: {distortions_file}")
    existing_distortions = load_json(distortions_file)
    
    print(f"Loading metadata: {metadata_file}")
    metadata = load_json(metadata_file)
    
    print(f"Loading existing question IDs: {existing_ids_file}")
    existing_ids = set(load_json(existing_ids_file))
    
    # Get current question IDs in this difficulty folder
    current_question_ids = set(metadata.get("question_ids", []))
    
    # Process batch questions
    batch_questions = batch_data.get("questions", [])
    new_questions = []
    duplicates = []
    
    for q in batch_questions:
        qid = q["question_id"]
        if qid in current_question_ids:
            duplicates.append(qid)
        else:
            new_questions.append(q)
    
    print(f"\n📊 Batch Analysis:")
    print(f"   Total questions in batch: {len(batch_questions)}")
    print(f"   Already in folder (duplicates): {len(duplicates)} - {duplicates}")
    print(f"   New questions to add: {len(new_questions)}")
    
    if not new_questions:
        print("\n⚠️ No new questions to add. All are duplicates.")
        return
    
    # Add new questions to distortions
    existing_distortions.extend(new_questions)
    
    # Update metadata
    new_ids = [q["question_id"] for q in new_questions]
    metadata["question_ids"].extend(new_ids)
    metadata["question_ids"] = sorted(metadata["question_ids"])
    metadata["unique_questions"] = len(metadata["question_ids"])
    metadata["total_distortions"] = len(metadata["question_ids"]) * 4  # 4 MIU levels per question
    metadata["last_updated"] = datetime.now().isoformat()
    metadata["added_questions"] = metadata.get("added_questions", 0) + len(new_questions)
    
    # Update existing_question_ids.json
    existing_ids.update(new_ids)
    existing_ids_list = sorted(list(existing_ids))
    
    # Save files
    print(f"\n💾 Saving updates...")
    save_json(distortions_file, existing_distortions)
    print(f"   ✅ Updated distortions file ({len(existing_distortions)} questions)")
    
    save_json(metadata_file, metadata)
    print(f"   ✅ Updated metadata (unique_questions: {metadata['unique_questions']})")
    
    save_json(existing_ids_file, existing_ids_list)
    print(f"   ✅ Updated existing_question_ids.json ({len(existing_ids_list)} total IDs)")
    
    # Archive the batch file
    archive_dir = base_dir / "generator_output" / "archived"
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / batch_file.name
    batch_file.rename(archive_path)
    print(f"   ✅ Archived batch file to {archive_path}")
    
    print(f"\n🎉 Migration Complete!")
    print(f"   New questions added: {len(new_questions)}")
    print(f"   Question IDs: {new_ids}")
    print(f"   Current total for difficulty {difficulty}: {metadata['unique_questions']} questions")
    print(f"   Remaining to reach 100: {100 - metadata['unique_questions']} questions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate validated batch to by_difficulty folder")
    parser.add_argument("--batch", type=str, required=True, help="Path to batch file")
    parser.add_argument("--difficulty", type=float, required=True, help="Difficulty level (1.0 or 1.5)")
    
    args = parser.parse_args()
    
    batch_path = Path(args.batch)
    if not batch_path.exists():
        print(f"❌ Error: Batch file not found: {batch_path}")
        exit(1)
    
    migrate_batch(batch_path, args.difficulty)

