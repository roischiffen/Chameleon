#!/usr/bin/env python3
"""
🦎 Chameleon Framework - Batch Generator for Generator-Validator Workflow
=========================================================================

Generates distortions for new questions in batches of 20.
Outputs JSON format for Validator review.

Usage:
    source ../venv/bin/activate
    python batch_generator.py --difficulty 1.0 --batch 1 --count 20
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.math_distortion_prompts import (
    get_distortion_prompt,
    calculate_temperature,
    get_miu_level_description
)

# Load environment from .env file
from dotenv import load_dotenv
load_dotenv('/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/venv/bin/.env')

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    MODEL = "gpt-4o"
    MIU_LEVELS = [0.2, 0.5, 0.7, 0.9]  # Only these 4 levels
    MAX_TOKENS = 2000
    RATE_LIMIT_DELAY = 0.5
    MAX_RETRIES = 3
    
    # Visual question indicators (auto-reject)
    VISUAL_INDICATORS = [
        "graph", "diagram", "figure", "chart", "shown", "picture",
        "image", "illustration", "shaded", "drawn", "see ", "refer to",
        "displayed", "grid", "table", "plotting", "coordinate plane",
        "depicted", "number line", "spinner"  # Added more indicators
    ]

# =============================================================================
# VISUAL QUESTION DETECTION
# =============================================================================

def is_visual_question(question: str, answer: str) -> bool:
    """Check if question requires visual elements."""
    combined = (question + " " + str(answer)).lower()
    for indicator in Config.VISUAL_INDICATORS:
        if indicator in combined:
            return True
    return False

# =============================================================================
# OPENAI CLIENT
# =============================================================================

def init_openai_client():
    """Initialize OpenAI client."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Check .env file.")
    
    from openai import OpenAI
    return OpenAI(api_key=api_key)

# =============================================================================
# DISTORTION GENERATOR
# =============================================================================

class BatchDistortionGenerator:
    def __init__(self):
        self.client = init_openai_client()
        self.stats = {'total': 0, 'success': 0, 'failed': 0}
    
    def generate_single_distortion(self, question: str, miu: float) -> Optional[str]:
        """Generate a single distortion for a question at a specific MIU level."""
        prompt = get_distortion_prompt(question, miu)
        if not prompt:
            return question  # Baseline
        
        temperature = calculate_temperature(miu)
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=Config.MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=Config.MAX_TOKENS
                )
                
                result = response.choices[0].message.content.strip()
                self.stats['success'] += 1
                return result
                
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt+1} failed: {e}")
                time.sleep(2)
        
        self.stats['failed'] += 1
        return None
    
    def generate_all_distortions(self, question_data: Dict) -> Dict:
        """Generate all 4 MIU distortions for a single question."""
        question_text = question_data.get('question', question_data.get('original_question', ''))
        
        distortions = []
        for miu in Config.MIU_LEVELS:
            print(f"      μ={miu}...", end=" ", flush=True)
            
            distorted = self.generate_single_distortion(question_text, miu)
            self.stats['total'] += 1
            
            if distorted:
                distortions.append({
                    "miu": miu,
                    "miu_description": get_miu_level_description(miu),
                    "distorted_question": distorted
                })
                print("✓")
            else:
                print("✗")
            
            time.sleep(Config.RATE_LIMIT_DELAY)
        
        return {
            "question_id": question_data['question_id'],
            "original_question": question_text,
            "correct_answer": question_data['correct_answer'],
            "difficulty": question_data['difficulty'],
            "domain": question_data.get('domain', ''),
            "subject": question_data.get('subject', []),
            "distortions": distortions
        }


def load_pending_questions(difficulty: float) -> List[Dict]:
    """Load pending questions for a specific difficulty."""
    pending_file = Path(__file__).parent.parent / "data" / "pending_validation" / f"level_{str(difficulty).replace('.', '_')}_pending_20251208_084712.json"
    
    if not pending_file.exists():
        print(f"❌ Pending file not found: {pending_file}")
        return []
    
    with open(pending_file, 'r') as f:
        return json.load(f)


def load_existing_question_ids(difficulty: float) -> set:
    """Load IDs of questions already processed - from BOTH by_difficulty AND global existing_ids."""
    existing = set()
    
    # 1. Load from by_difficulty metadata
    if difficulty == 1.0:
        folder_name = "difficulty_1"
        file_name = "difficulty_1_metadata.json"
    elif difficulty == 1.5:
        folder_name = "difficulty_1.5"
        file_name = "difficulty_1.5_metadata.json"
    else:
        folder_name = f"difficulty_{difficulty}"
        file_name = f"difficulty_{difficulty}_metadata.json"
    
    metadata_file = Path(__file__).parent.parent / "data" / "by_difficulty" / folder_name / file_name
    
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            existing.update(data.get('question_ids', []))
        print(f"    • Loaded {len(existing)} IDs from by_difficulty metadata")
    
    # 2. Load from global existing_question_ids.json (contains ALL processed IDs across all difficulties)
    global_ids_file = Path(__file__).parent.parent / "data" / "existing_question_ids.json"
    if global_ids_file.exists():
        with open(global_ids_file, 'r') as f:
            global_ids = set(json.load(f))
            initial_count = len(existing)
            existing.update(global_ids)
            print(f"    • Added {len(existing) - initial_count} more IDs from global existing_question_ids.json")
    
    return existing


def select_new_questions(pending: List[Dict], existing_ids: set, count: int) -> List[Dict]:
    """Select new questions that are not visual and not already processed."""
    selected = []
    
    for q in pending:
        if len(selected) >= count:
            break
        
        qid = q['question_id']
        question_text = q.get('question', '')
        answer = q.get('correct_answer', '')
        
        # Skip if already exists
        if qid in existing_ids:
            continue
        
        # Skip visual questions
        if is_visual_question(question_text, answer):
            print(f"  ⚠️ Skipping visual question {qid}: {question_text[:50]}...")
            continue
        
        selected.append(q)
    
    return selected


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate distortions for a batch of questions')
    parser.add_argument('--difficulty', type=float, default=1.0, help='Difficulty level (1.0 or 1.5)')
    parser.add_argument('--batch', type=int, default=1, help='Batch number')
    parser.add_argument('--count', type=int, default=20, help='Number of questions to process')
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("  🦎 CHAMELEON - Batch Distortion Generator")
    print("=" * 70)
    print(f"  Difficulty: {args.difficulty}")
    print(f"  Batch: {args.batch}")
    print(f"  Count: {args.count}")
    print(f"  MIU Levels: {Config.MIU_LEVELS}")
    print("=" * 70 + "\n")
    
    # Load data
    print("📂 Loading data...")
    pending = load_pending_questions(args.difficulty)
    existing_ids = load_existing_question_ids(args.difficulty)
    
    print(f"  • Pending questions: {len(pending)}")
    print(f"  • Already processed: {len(existing_ids)}")
    
    # Select new questions
    print("\n🔍 Selecting new questions...")
    selected = select_new_questions(pending, existing_ids, args.count)
    print(f"  • Selected: {len(selected)} questions\n")
    
    if not selected:
        print("❌ No new questions to process!")
        return
    
    # Generate distortions
    generator = BatchDistortionGenerator()
    results = []
    
    for i, q in enumerate(selected, 1):
        print(f"\n[{i}/{len(selected)}] Question {q['question_id']}: {q['question'][:60]}...")
        result = generator.generate_all_distortions(q)
        results.append(result)
    
    # Prepare output
    output = {
        "batch_number": args.batch,
        "difficulty": args.difficulty,
        "total_questions": len(results),
        "total_distortions": len(results) * len(Config.MIU_LEVELS),
        "miu_levels": Config.MIU_LEVELS,
        "timestamp": datetime.now().isoformat(),
        "generator_stats": generator.stats,
        "questions": results
    }
    
    # Save output
    output_dir = Path(__file__).parent.parent / "data" / "generator_output"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"batch_{args.batch}_difficulty_{args.difficulty}_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("  ✅ GENERATION COMPLETE")
    print("=" * 70)
    print(f"\n📊 Statistics:")
    print(f"   • Questions processed: {len(results)}")
    print(f"   • Distortions generated: {generator.stats['success']}")
    print(f"   • Failed: {generator.stats['failed']}")
    print(f"\n💾 Output saved to: {output_file}")
    print("\n📋 Next Step: Send this file to the VALIDATOR for review!")


if __name__ == "__main__":
    main()

