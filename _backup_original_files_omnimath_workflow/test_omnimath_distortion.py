#!/usr/bin/env python3
"""
🦎 Chameleon Framework - OmniMath Distortion Test
==================================================

Test script to validate the distortion approach with OmniMath dataset.
Creates distorted versions of math questions and outputs to CSV.

Usage:
    python3 test_omnimath_distortion.py

Requirements:
    - OpenAI API key set as environment variable
    - pip install openai pandas tqdm

Author: Chameleon Framework - Dataset Generation
"""

import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# ============================================================================
# CONFIGURATION
# ============================================================================

NUM_QUESTIONS = 5           # Number of questions to test
MIU_LEVELS = [0.0, 0.3, 0.6, 0.9]  # Distortion levels to test
DISTORTIONS_PER_MIU = 3     # How many distortions per μ level
MODEL = "gpt-4o-mini"       # Model to use for distortions
OUTPUT_DIR = Path("test_omnimath_results")

# ============================================================================
# API SETUP
# ============================================================================

def check_api_key():
    """Check if OpenAI API key is available"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n" + "="*60)
        print("❌ OPENAI_API_KEY not found!")
        print("="*60)
        print("\nPlease set your OpenAI API key:")
        print("\n  Option 1 (Terminal):")
        print("    export OPENAI_API_KEY='your-api-key-here'")
        print("\n  Option 2 (Create .env file in project root):")
        print("    echo 'OPENAI_API_KEY=your-api-key-here' > .env")
        print("\nGet your API key at: https://platform.openai.com/api-keys")
        print("="*60 + "\n")
        sys.exit(1)
    return api_key

API_KEY = check_api_key()

from openai import OpenAI
client = OpenAI(api_key=API_KEY)

# ============================================================================
# DATA LOADING
# ============================================================================

def load_omnimath_questions(num_questions=5):
    """
    Load questions from OmniMath dataset.
    Falls back to sample questions if dataset loading fails.
    
    Returns:
        list: List of question dictionaries
    """
    print("\n📚 Loading OmniMath Questions...")
    
    try:
        # Try loading from HuggingFace
        from datasets import load_dataset
        
        # OmniMath dataset ID
        dataset = load_dataset("KbsdJames/Omni-MATH", split="test")
        
        questions = []
        for i, item in enumerate(dataset):
            if i >= num_questions:
                break
            
            # Extract subject - handle list or string format
            subject = item.get('domain', item.get('subject', 'math'))
            if isinstance(subject, list):
                subject = subject[0] if subject else 'math'
            
            questions.append({
                'id': i + 1,
                'question': item.get('problem', item.get('question', '')),
                'correct_answer': item.get('answer', item.get('solution', '')),
                'subject': subject,
                'difficulty': item.get('difficulty', 'medium')
            })
        
        print(f"✅ Loaded {len(questions)} questions from OmniMath (HuggingFace)")
        
        # Display loaded questions
        for q in questions:
            print(f"\n  Question {q['id']}:")
            q_display = q['question'][:100] + "..." if len(q['question']) > 100 else q['question']
            print(f"    \"{q_display}\"")
            ans_display = str(q['correct_answer'])[:50] + "..." if len(str(q['correct_answer'])) > 50 else q['correct_answer']
            print(f"    Answer: {ans_display}")
        
        return questions
        
    except Exception as e:
        print(f"⚠️  Could not load OmniMath from HuggingFace: {e}")
        print("\n📝 Using sample competition math questions for testing...")
        
        # Fallback: Sample competition-style math questions
        fallback_questions = [
            {
                'id': 1,
                'question': "Find all integers n such that n² + 2n + 2 is divisible by n + 4.",
                'correct_answer': "n ∈ {-14, -6, -5, -3, -2, 6}",
                'subject': 'number_theory',
                'difficulty': 'medium'
            },
            {
                'id': 2,
                'question': "In triangle ABC, the angle bisector from A meets BC at D. If AB = 6, AC = 8, and BC = 10, find the length of AD.",
                'correct_answer': "AD = 48/7",
                'subject': 'geometry',
                'difficulty': 'medium'
            },
            {
                'id': 3,
                'question': "How many 4-digit positive integers have digits that form an arithmetic progression when read from left to right?",
                'correct_answer': "57",
                'subject': 'combinatorics',
                'difficulty': 'medium'
            },
            {
                'id': 4,
                'question': "Find the sum of all positive integers n less than 100 such that n and n+50 are both perfect squares.",
                'correct_answer': "There are no such integers",
                'subject': 'number_theory',
                'difficulty': 'easy'
            },
            {
                'id': 5,
                'question': "A circle is inscribed in a right triangle with legs of length 5 and 12. What is the radius of the inscribed circle?",
                'correct_answer': "2",
                'subject': 'geometry',
                'difficulty': 'easy'
            }
        ]
        
        print(f"✅ Using {len(fallback_questions)} fallback questions\n")
        
        for q in fallback_questions:
            print(f"  Question {q['id']} ({q['subject']}):")
            q_display = q['question'][:80] + "..." if len(q['question']) > 80 else q['question']
            print(f"    \"{q_display}\"")
            print(f"    Answer: {q['correct_answer']}")
        
        return fallback_questions

# ============================================================================
# DISTORTION PROMPT (Based on Mistral Server RLHF approach)
# ============================================================================

def get_distortion_prompt(question: str, miu: float, num_distortions: int = 1) -> str:
    """
    Create a distortion prompt based on μ level.
    Follows the same approach as the Mistral server RLHF prompt.
    
    Args:
        question: Original question text
        miu: Distortion level (0.0 to 1.0)
        num_distortions: Number of unique distortions to generate
        
    Returns:
        Formatted prompt string, or None if miu is 0.0
    """
    if miu == 0.0:
        return None  # No distortion needed
    
    # μ → Distortion level mapping (from original Mistral server prompt)
    if miu <= 0.2:
        level = "Minimal Lexical"
        rules = """- Make only 1-2 word substitutions using simple synonyms
- Preserve EXACT sentence structure and word order
- Minimal changes, focus on precision
- Use simple synonyms only"""
    elif miu <= 0.4:
        level = "Moderate Lexical"
        rules = """- 3-4 word substitutions allowed
- More extensive synonym replacements
- Some phrase restructuring permitted
- Maintain question type and core structure"""
    elif miu <= 0.6:
        level = "Light Mixed"
        rules = """- Combine lexical and structural changes
- Moderate sentence restructuring
- Can change question word placement
- Begin introducing structural variety"""
    elif miu <= 0.8:
        level = "Heavy Mixed"
        rules = """- Major restructuring allowed
- Different grammatical constructions
- Can change passive/active voice
- Significant surface-level changes"""
    else:
        level = "Full Paraphrase"
        rules = """- Complete sentence reconstruction
- Maximum syntactic variation
- Different approaches to asking same question
- Maximum creativity while preserving meaning"""

    prompt = f"""You are a mathematical question paraphrasing expert.

## Task
Create {num_distortions} UNIQUE distortion(s) of the following math question at the "{level}" level (μ={miu}).

## Distortion Rules for μ={miu}:
{rules}

## Critical Requirements:
1. The CORRECT ANSWER must remain exactly the same
2. Preserve ALL numerical values, variables, and mathematical expressions EXACTLY
3. Each distortion must be COMPLETELY UNIQUE (no duplicates)
4. Maintain mathematical accuracy and answerability
5. Keep the question type and domain the same
6. Do NOT solve the problem - only rephrase the question

## Original Question:
{question}

## Output Format:
Return exactly {num_distortions} distorted question(s), one per line.
Use this EXACT format with numbered lines:

1. [first distorted question]
2. [second distorted question]
3. [third distorted question]

Do NOT include any explanation, reasoning, or additional text. Just the numbered distortions."""

    return prompt

# ============================================================================
# RESPONSE PARSING
# ============================================================================

def parse_numbered_response(response_text: str, expected_count: int) -> list:
    """
    Parse a numbered list response from the LLM.
    Handles LaTeX content that would break JSON parsing.
    
    Args:
        response_text: Raw response from LLM
        expected_count: Expected number of distortions
        
    Returns:
        List of distortion strings
    """
    import re
    
    distortions = []
    
    # Try to extract numbered items (1. xxx, 2. xxx, etc.)
    # Pattern matches: number followed by . or ) then the content
    lines = response_text.split('\n')
    current_item = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line starts with a number (new item)
        match = re.match(r'^(\d+)[.\)]\s*(.*)$', line)
        if match:
            # Save previous item if exists
            if current_item:
                distortions.append(current_item.strip())
            # Start new item
            current_item = match.group(2)
        else:
            # Continuation of current item
            if current_item:
                current_item += " " + line
            else:
                current_item = line
    
    # Don't forget the last item
    if current_item:
        distortions.append(current_item.strip())
    
    # If numbered parsing didn't work, try splitting by double newlines
    if len(distortions) == 0:
        distortions = [d.strip() for d in response_text.split('\n\n') if d.strip()]
    
    # If still nothing, treat whole response as single distortion
    if len(distortions) == 0:
        distortions = [response_text.strip()]
    
    # Clean up: remove any leading/trailing quotes
    cleaned = []
    for d in distortions:
        d = d.strip()
        if d.startswith('"') and d.endswith('"'):
            d = d[1:-1]
        if d.startswith("'") and d.endswith("'"):
            d = d[1:-1]
        # Remove [bracketed] markers if present
        d = re.sub(r'^\[.*?\]\s*', '', d)
        if d:
            cleaned.append(d)
    
    return cleaned[:expected_count]  # Return only expected count


# ============================================================================
# DISTORTION GENERATION
# ============================================================================

def generate_distortions(questions: list, miu_levels: list, distortions_per_miu: int):
    """
    Generate distorted versions of questions using OpenAI API.
    
    Args:
        questions: List of question dictionaries
        miu_levels: List of μ values to use
        distortions_per_miu: Number of distortions per μ level
        
    Returns:
        List of result dictionaries
    """
    print("\n" + "="*70)
    print("  🔄 GENERATING DISTORTIONS")
    print("="*70)
    
    print(f"\n📊 Settings:")
    print(f"   • Questions: {len(questions)}")
    print(f"   • μ levels: {miu_levels}")
    print(f"   • Distortions per μ: {distortions_per_miu}")
    print(f"   • Model: {MODEL}")
    total = len(questions) * sum(distortions_per_miu if miu > 0 else 1 for miu in miu_levels)
    print(f"   • Expected total entries: ~{total}")
    
    all_results = []
    
    for q in tqdm(questions, desc="Processing questions"):
        for miu in miu_levels:
            
            if miu == 0.0:
                # Baseline - no distortion, keep original
                all_results.append({
                    'question_id': q['id'],
                    'subject': q['subject'],
                    'original_question': q['question'],
                    'distorted_question': q['question'],  # Same as original
                    'correct_answer': q['correct_answer'],
                    'miu': miu,
                    'distortion_index': 0,
                    'difficulty': q['difficulty']
                })
            else:
                # Generate distortions via API
                prompt = get_distortion_prompt(q['question'], miu, distortions_per_miu)
                
                try:
                    # Calculate temperature based on μ (from original formula)
                    # temperature = 0.3 + (μ^1.5 × 1.2)
                    temperature = 0.3 + (miu ** 1.5) * 1.2
                    temperature = min(temperature, 1.5)  # Cap at 1.5 for stability
                    
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=1500
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                    # Parse numbered list response (handles LaTeX content better than JSON)
                    distortions = parse_numbered_response(response_text, distortions_per_miu)
                    
                    # If we got fewer distortions than expected, log it
                    if len(distortions) < distortions_per_miu:
                        print(f"\n⚠️  Q{q['id']} μ={miu}: Got {len(distortions)}/{distortions_per_miu} distortions")
                    
                    # If no distortions parsed, use original as fallback
                    if len(distortions) == 0:
                        distortions = [q['question']]
                    
                    # Add each distortion to results
                    for idx, distortion in enumerate(distortions[:distortions_per_miu]):
                        all_results.append({
                            'question_id': q['id'],
                            'subject': q['subject'],
                            'original_question': q['question'],
                            'distorted_question': distortion if isinstance(distortion, str) else str(distortion),
                            'correct_answer': q['correct_answer'],
                            'miu': miu,
                            'distortion_index': idx + 1,
                            'difficulty': q['difficulty']
                        })
                        
                except Exception as e:
                    print(f"\n❌ Error for Q{q['id']} μ={miu}: {e}")
                    # Fallback to original question on error
                    all_results.append({
                        'question_id': q['id'],
                        'subject': q['subject'],
                        'original_question': q['question'],
                        'distorted_question': q['question'],
                        'correct_answer': q['correct_answer'],
                        'miu': miu,
                        'distortion_index': 1,
                        'difficulty': q['difficulty'],
                        'error': str(e)
                    })
                
                time.sleep(0.3)  # Rate limiting to avoid API throttling
    
    return all_results

# ============================================================================
# OUTPUT AND DISPLAY
# ============================================================================

def display_results(results: list):
    """Display sample results for human review"""
    print("\n" + "="*70)
    print("  📋 SAMPLE DISTORTION RESULTS")
    print("="*70)
    
    # Group by question
    by_question = {}
    for r in results:
        qid = r['question_id']
        if qid not in by_question:
            by_question[qid] = []
        by_question[qid].append(r)
    
    # Show first 2 questions with their distortions
    for qid in list(by_question.keys())[:2]:
        entries = by_question[qid]
        original = entries[0]['original_question']
        answer = entries[0]['correct_answer']
        
        print(f"\n{'─'*60}")
        print(f"📌 Question {qid}:")
        print(f"{'─'*60}")
        print(f"\n   ORIGINAL:")
        print(f"   {original[:150]}{'...' if len(original) > 150 else ''}")
        print(f"\n   ANSWER: {answer}")
        
        for entry in entries:
            miu = entry['miu']
            idx = entry['distortion_index']
            distorted = entry['distorted_question']
            
            if miu == 0.0:
                continue  # Skip baseline display
            
            print(f"\n   μ={miu} [distortion {idx}]:")
            print(f"   {distorted[:150]}{'...' if len(distorted) > 150 else ''}")


def save_results(results: list, output_dir: Path):
    """Save results to CSV and JSON files"""
    output_dir.mkdir(exist_ok=True)
    
    # Save as CSV (main output format)
    df = pd.DataFrame(results)
    csv_path = output_dir / "omnimath_distortions.csv"
    df.to_csv(csv_path, index=False)
    
    # Save as JSON (for programmatic access)
    json_path = output_dir / "omnimath_distortions.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_dir}/:")
    print(f"   • CSV:  {csv_path.name}")
    print(f"   • JSON: {json_path.name}")
    
    # Print summary statistics
    print(f"\n📊 Dataset Summary:")
    print(f"   • Total entries: {len(results)}")
    print(f"   • Unique questions: {df['question_id'].nunique()}")
    print(f"   • μ levels used: {sorted(df['miu'].unique().tolist())}")
    
    # Handle subject field (may be list or string depending on dataset)
    try:
        subjects = df['subject'].apply(lambda x: x[0] if isinstance(x, list) else x).unique().tolist()
        print(f"   • Subjects: {subjects}")
    except:
        print(f"   • Subjects: (mixed format)")
    
    # Count by μ level
    print(f"\n   Entries per μ level:")
    for miu in sorted(df['miu'].unique()):
        count = len(df[df['miu'] == miu])
        print(f"      μ={miu}: {count} entries")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution flow"""
    print("\n" + "="*70)
    print("  🦎 CHAMELEON - OmniMath Distortion Test")
    print("="*70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Configuration:")
    print(f"    • Questions: {NUM_QUESTIONS}")
    print(f"    • μ levels: {MIU_LEVELS}")
    print(f"    • Distortions per μ: {DISTORTIONS_PER_MIU}")
    
    # Step 1: Load questions
    questions = load_omnimath_questions(NUM_QUESTIONS)
    
    # Step 2: Generate distortions
    results = generate_distortions(questions, MIU_LEVELS, DISTORTIONS_PER_MIU)
    
    # Step 3: Display sample results for review
    display_results(results)
    
    # Step 4: Save results
    save_results(results, OUTPUT_DIR)
    
    print("\n" + "="*70)
    print("  ✅ TEST COMPLETE")
    print("="*70)
    print("\n📋 Next Steps:")
    print("  1. Review generated distortions in test_omnimath_results/")
    print("  2. Verify distortions preserve mathematical meaning and answers")
    print("  3. Adjust μ levels or prompt rules as needed")
    print("  4. Pass to validation team for quality assessment")
    print("  5. Scale up to full dataset once validated")
    print("\n")


if __name__ == "__main__":
    main()
