#!/usr/bin/env python3
"""
🦎 Chameleon Framework - OmniMath Distortion Generator
======================================================

Generates distorted versions of OmniMath competition mathematics questions
using GPT-4o for high-quality mathematical paraphrasing.

Features:
- Loads OmniMath problems filtered by difficulty (≤5 for Easy+Medium)
- Applies 10 μ-levels of distortion (0.0-0.9)
- Uses optimized prompts for mathematical preservation
- Outputs to CSV and JSON formats

Usage:
    # Pilot test (5-10 questions)
    python3 omnimath_distortion_generator.py --pilot
    
    # Full generation (200 questions)
    python3 omnimath_distortion_generator.py --full --count 200
    
    # Custom run
    python3 omnimath_distortion_generator.py --count 50 --miu-levels 0.0 0.3 0.6 0.9

Author: Chameleon Framework
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from typing import List, Dict, Any, Optional

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.modules.math_distortion_prompts import (
    get_distortion_prompt,
    calculate_temperature,
    get_miu_level_description,
    get_all_miu_levels
)
from src.modules.omnimath_loader import OmniMathLoader

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Configuration for distortion generation."""
    
    # Model settings
    MODEL = "gpt-4o"  # Best model for mathematical tasks
    
    # Dataset settings
    MAX_DIFFICULTY = 5.0  # Easy + Medium only
    DEFAULT_QUESTION_COUNT = 200
    PILOT_QUESTION_COUNT = 10
    
    # μ-level settings
    ALL_MIU_LEVELS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    PILOT_MIU_LEVELS = [0.0, 0.3, 0.6, 0.9]  # Subset for pilot testing
    
    # Output settings (relative to project root)
    OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "source"
    
    # API settings
    MAX_TOKENS = 2000
    RATE_LIMIT_DELAY = 0.4  # Seconds between API calls
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    # Adaptive rate limiting (Option B)
    COOLDOWN_EVERY_N_QUESTIONS = 10  # Add extra delay after every N questions
    COOLDOWN_DELAY = 2.0  # Extra delay in seconds


# =============================================================================
# GIBBERISH DETECTION
# =============================================================================

import re

def is_gibberish(text: str, original_length: int = 0) -> bool:
    """
    Detect if the generated text is gibberish/garbage.
    
    Checks for:
    1. Excessive random characters
    2. Multiple languages mixed
    3. Code/HTML fragments
    4. Repetitive nonsense patterns
    5. Unusual length ratio
    
    Args:
        text: The generated text to check
        original_length: Length of original question for comparison
        
    Returns:
        True if text appears to be gibberish
    """
    if not text or len(text) < 20:
        return True
    
    # Check 1: Excessive non-ASCII characters (excluding LaTeX and math)
    non_ascii_ratio = len(re.findall(r'[^\x00-\x7F]', text)) / len(text)
    if non_ascii_ratio > 0.15:  # More than 15% non-ASCII is suspicious
        return True
    
    # Check 2: Code/HTML fragments
    code_patterns = [
        r'<[a-zA-Z][^>]*>',  # HTML tags
        r'\{\{[^}]+\}\}',     # Template syntax
        r'\$\{[^}]+\}',       # Template variables
        r'function\s*\(',     # JavaScript
        r'def\s+\w+\s*\(',    # Python
        r'class\s+\w+\s*[:{]', # Class definitions
        r'import\s+\w+',      # Import statements
        r'console\.log',      # JS console
        r'\bNone\b.*\bNone\b.*\bNone\b',  # Repeated None
    ]
    for pattern in code_patterns:
        if re.search(pattern, text):
            return True
    
    # Check 3: Random character sequences (10+ non-space chars with no vowels)
    if re.search(r'\b[bcdfghjklmnpqrstvwxyz]{10,}\b', text.lower()):
        return True
    
    # Check 4: Excessive special characters
    special_chars = re.findall(r'[^\w\s\.,\?\!\-\:\;\(\)\[\]\{\}\$\\\/\^\=\+\<\>\|\_\~\@\#\%\&\*\'\"]', text)
    if len(special_chars) > len(text) * 0.1:
        return True
    
    # Check 5: Text is WAY longer than original (>5x is suspicious)
    if original_length > 0 and len(text) > original_length * 5:
        return True
    
    # Check 6: Multiple script mixing (Latin + Cyrillic + Arabic + CJK etc.)
    scripts = {
        'cyrillic': bool(re.search(r'[\u0400-\u04FF]', text)),
        'arabic': bool(re.search(r'[\u0600-\u06FF]', text)),
        'chinese': bool(re.search(r'[\u4E00-\u9FFF]', text)),
        'hebrew': bool(re.search(r'[\u0590-\u05FF]', text)),
        'thai': bool(re.search(r'[\u0E00-\u0E7F]', text)),
        'japanese': bool(re.search(r'[\u3040-\u30FF]', text)),
    }
    foreign_scripts = sum(scripts.values())
    if foreign_scripts >= 2:  # Multiple foreign scripts = likely garbage
        return True
    
    # Check 7: Repeated patterns (same phrase 3+ times)
    words = text.lower().split()
    if len(words) > 20:
        # Check for word repetition
        from collections import Counter
        word_counts = Counter(words)
        most_common_count = word_counts.most_common(1)[0][1] if word_counts else 0
        if most_common_count > len(words) * 0.2:  # Same word >20% of the time
            return True
    
    # Check 8: No mathematical content at all
    math_indicators = [
        r'\d+',           # Numbers
        r'[xyz]',         # Common variables
        r'[=<>≤≥]',       # Comparison operators
        r'\$',            # LaTeX
        r'\\[a-z]+',      # LaTeX commands
        r'triangle|square|circle|integer|prime|function|equation',
    ]
    has_math = any(re.search(p, text, re.IGNORECASE) for p in math_indicators)
    if not has_math:
        return True
    
    return False


def clean_distorted_output(text: str) -> str:
    """
    Clean up the distorted question output.
    
    Removes common LLM artifacts like explanations, prefixes, etc.
    
    Args:
        text: Raw output from LLM
        
    Returns:
        Cleaned question text
    """
    if not text:
        return text
    
    # Remove common prefixes/suffixes added by LLMs
    prefixes_to_remove = [
        r'^(DISTORTED PROBLEM|Distorted|Here is|Here\'s|The distorted|Output)[:\s]*',
        r'^(Version|Rephrased|Paraphrased|Modified)[:\s]*',
        r'^["\']',  # Opening quotes
    ]
    
    suffixes_to_remove = [
        r'["\']$',  # Closing quotes
        r'\s*\(distorted version\)\s*$',
        r'\s*---+\s*$',
    ]
    
    result = text.strip()
    
    for pattern in prefixes_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    
    for pattern in suffixes_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    
    return result


# =============================================================================
# API SETUP
# =============================================================================

def check_api_key() -> str:
    """Check if OpenAI API key is available."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n" + "=" * 60)
        print("❌ OPENAI_API_KEY not found!")
        print("=" * 60)
        print("\nPlease set your OpenAI API key:")
        print("\n  Option 1 (Terminal):")
        print("    export OPENAI_API_KEY='your-api-key-here'")
        print("\n  Option 2 (Create .env file):")
        print("    echo 'OPENAI_API_KEY=your-api-key-here' > .env")
        print("\nGet your API key at: https://platform.openai.com/api-keys")
        print("=" * 60 + "\n")
        sys.exit(1)
    return api_key


def init_openai_client():
    """Initialize OpenAI client."""
    api_key = check_api_key()
    
    from openai import OpenAI
    return OpenAI(api_key=api_key)


# =============================================================================
# DISTORTION GENERATION
# =============================================================================

class OmniMathDistortionGenerator:
    """
    Generator for creating distorted versions of OmniMath questions.
    """
    
    def __init__(self, 
                 model: str = Config.MODEL,
                 max_difficulty: float = Config.MAX_DIFFICULTY):
        """
        Initialize the generator.
        
        Args:
            model: OpenAI model to use
            max_difficulty: Maximum difficulty for questions
        """
        self.model = model
        self.client = init_openai_client()
        self.loader = OmniMathLoader(max_difficulty=max_difficulty)
        
        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0
        }
    
    def load_questions(self, 
                       count: int,
                       random_seed: Optional[int] = 42,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """
        Load and filter OmniMath questions.
        
        Args:
            count: Number of questions to load
            random_seed: Seed for random sampling
            offset: Skip first N questions (for batched generation)
            
        Returns:
            List of question dictionaries
        """
        # Filter dataset
        self.loader.filter_by_difficulty()
        
        # Get random sample - request count + offset, then slice
        total_needed = count + offset
        all_questions = self.loader.get_random_sample(total_needed, seed=random_seed)
        
        # Apply offset - skip first N questions
        questions = all_questions[offset:offset + count]
        
        if offset > 0:
            print(f"\n📚 Loaded {len(questions)} questions (offset={offset}, difficulty ≤ {self.loader.max_difficulty})")
        else:
            print(f"\n📚 Loaded {len(questions)} questions (difficulty ≤ {self.loader.max_difficulty})")
        
        return questions
    
    def generate_distortion(self, 
                           question: str,
                           miu: float) -> tuple[Optional[str], bool]:
        """
        Generate a single distorted version of a question.
        
        The temperature is ALWAYS kept according to the μ level - this is fundamental
        to the Chameleon framework. If gibberish is detected, we retry at the SAME
        temperature. If it persists, we mark as FAILED (not substitute a different μ).
        
        Args:
            question: Original question text
            miu: Distortion level (0.0-0.9)
            
        Returns:
            Tuple of (distorted_question, is_valid)
            - distorted_question: The distorted text, or original if μ=0.0
            - is_valid: True if generation was successful, False if gibberish detected
        """
        # μ=0.0 means no distortion (baseline)
        if miu == 0.0:
            return question, True
        
        # Get prompt for this μ level
        prompt = get_distortion_prompt(question, miu)
        
        if prompt is None:
            return question, True
        
        # Calculate temperature - ALWAYS use the temperature for this μ level
        temperature = calculate_temperature(miu)
        original_length = len(question)
        
        # Make API call with retries (same temperature each time!)
        for attempt in range(Config.MAX_RETRIES):
            try:
                self.stats['total_requests'] += 1
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,  # ALWAYS the same temperature for this μ
                    max_tokens=Config.MAX_TOKENS
                )
                
                distorted = response.choices[0].message.content.strip()
                
                # Clean up common LLM artifacts
                distorted = clean_distorted_output(distorted)
                
                # Basic validation
                if not distorted or len(distorted) < 10:
                    raise ValueError("Empty or too short response")
                
                # Gibberish detection
                if is_gibberish(distorted, original_length):
                    self.stats['retries'] += 1
                    if attempt < Config.MAX_RETRIES - 1:
                        # Retry at SAME temperature - maybe model will generate better output
                        tqdm.write(f"\n⚠️ Gibberish detected at μ={miu}, retrying (attempt {attempt+2}/{Config.MAX_RETRIES})...")
                        time.sleep(Config.RETRY_DELAY)
                        continue
                    else:
                        # Mark as FAILED - do NOT substitute with different μ level!
                        tqdm.write(f"\n❌ μ={miu} gibberish persisted after {Config.MAX_RETRIES} attempts - marking as FAILED")
                        self.stats['failed'] += 1
                        return distorted, False  # Return the gibberish but mark as invalid
                
                self.stats['successful'] += 1
                return distorted, True
                    
            except Exception as e:
                self.stats['retries'] += 1
                
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY * (attempt + 1))
                else:
                    tqdm.write(f"\n⚠️ API error after {Config.MAX_RETRIES} attempts: {e}")
                    self.stats['failed'] += 1
                    return None, False
        
        return None, False
    
    def generate_all_distortions(self,
                                  questions: List[Dict[str, Any]],
                                  miu_levels: List[float]) -> List[Dict[str, Any]]:
        """
        Generate distortions for all questions at all μ levels.
        
        Each distortion is generated at the EXACT temperature corresponding to its μ level.
        If gibberish is detected, it's marked as invalid (not substituted with different μ).
        
        Args:
            questions: List of question dictionaries
            miu_levels: List of μ levels to apply
            
        Returns:
            List of result dictionaries
        """
        results = []
        gibberish_count = 0
        question_counter = 0  # Track questions processed for adaptive rate limiting
        
        total_operations = len(questions) * len(miu_levels)
        
        print(f"\n🔄 Generating distortions...")
        print(f"   • Questions: {len(questions)}")
        print(f"   • μ levels: {miu_levels}")
        print(f"   • Total operations: {total_operations}")
        print(f"   • Model: {self.model}")
        print(f"   • Rate limiting: {Config.RATE_LIMIT_DELAY}s + {Config.COOLDOWN_DELAY}s cooldown every {Config.COOLDOWN_EVERY_N_QUESTIONS} questions")
        
        # Progress bar
        with tqdm(total=total_operations, desc="Generating") as pbar:
            for q in questions:
                question_counter += 1
                
                # Adaptive cooldown every N questions
                if question_counter > 1 and question_counter % Config.COOLDOWN_EVERY_N_QUESTIONS == 0:
                    tqdm.write(f"   💤 Cooldown after {question_counter} questions...")
                    time.sleep(Config.COOLDOWN_DELAY)
                
                for miu in miu_levels:
                    # Generate distortion - returns (distorted_text, is_valid)
                    distorted, is_valid = self.generate_distortion(q['question'], miu)
                    
                    # Track gibberish occurrences
                    if not is_valid and distorted is not None:
                        gibberish_count += 1
                    
                    # Create result entry
                    result = {
                        'question_id': q['question_id'],
                        'subject': q['subject'],
                        'domain': q['domain'],
                        'original_question': q['question'],
                        'distorted_question': distorted if distorted else q['question'],
                        'correct_answer': q['correct_answer'],
                        'miu': miu,
                        'miu_description': get_miu_level_description(miu),
                        'distortion_index': miu_levels.index(miu),
                        'difficulty': q['difficulty'],
                        'difficulty_category': q['difficulty_category'],
                        'source': 'omnimath',
                        'generation_success': distorted is not None,
                        'is_valid_distortion': is_valid  # New field to track gibberish
                    }
                    
                    results.append(result)
                    pbar.update(1)
                    
                    # Rate limiting
                    if miu > 0:  # Only for actual API calls
                        time.sleep(Config.RATE_LIMIT_DELAY)
        
        # Report gibberish statistics
        if gibberish_count > 0:
            print(f"\n⚠️ Gibberish detected in {gibberish_count} distortions (marked as is_valid_distortion=False)")
        
        return results
    
    def save_results(self,
                     results: List[Dict[str, Any]],
                     output_dir: Path,
                     prefix: str = "omnimath") -> Dict[str, str]:
        """
        Save results to CSV and JSON files.
        
        Args:
            results: List of result dictionaries
            output_dir: Output directory path (base directory for batches)
            prefix: Filename prefix (e.g., "omnimath_batch1")
            
        Returns:
            Dictionary with output file paths
        """
        # Extract batch number from prefix if present (e.g., "omnimath_batch1" -> "batch1")
        batch_match = None
        if "batch" in prefix.lower():
            import re
            match = re.search(r'batch(\d+)', prefix.lower())
            if match:
                batch_match = f"batch{match.group(1)}"
        
        # Create batch-specific directory if batch number found
        if batch_match:
            batch_dir = output_dir / batch_match
        else:
            batch_dir = output_dir
        
        batch_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_path = batch_dir / f"{prefix}_distortions_{timestamp}.csv"
        df = pd.DataFrame(results)
        df.to_csv(csv_path, index=False)
        
        # Save as JSON
        json_path = batch_dir / f"{prefix}_distortions_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save metadata
        metadata = {
            'generation_timestamp': timestamp,
            'model': self.model,
            'total_entries': len(results),
            'unique_questions': len(set(r['question_id'] for r in results)),
            'miu_levels': sorted(list(set(r['miu'] for r in results))),
            'difficulty_range': {
                'min': min(r['difficulty'] for r in results),
                'max': max(r['difficulty'] for r in results)
            },
            'statistics': self.stats
        }
        
        metadata_path = batch_dir / f"{prefix}_metadata_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'csv': str(csv_path),
            'json': str(json_path),
            'metadata': str(metadata_path)
        }


# =============================================================================
# RESULT DISPLAY
# =============================================================================

def display_sample_results(results: List[Dict[str, Any]], count: int = 2):
    """Display sample results for human review."""
    
    print("\n" + "=" * 70)
    print("  📋 SAMPLE DISTORTION RESULTS")
    print("=" * 70)
    
    # Group by question
    by_question = {}
    for r in results:
        qid = r['question_id']
        if qid not in by_question:
            by_question[qid] = []
        by_question[qid].append(r)
    
    # Display first N questions
    for qid in list(by_question.keys())[:count]:
        entries = by_question[qid]
        original = entries[0]['original_question']
        answer = entries[0]['correct_answer']
        difficulty = entries[0]['difficulty']
        
        print(f"\n{'─' * 65}")
        print(f"📌 Question {qid} | Difficulty: {difficulty}")
        print(f"{'─' * 65}")
        
        # Original question (truncated)
        print(f"\n🔹 ORIGINAL:")
        if len(original) > 200:
            print(f"   {original[:200]}...")
        else:
            print(f"   {original}")
        
        # Answer
        answer_str = str(answer)
        if len(answer_str) > 80:
            print(f"\n🎯 ANSWER: {answer_str[:80]}...")
        else:
            print(f"\n🎯 ANSWER: {answer_str}")
        
        # Show distortions
        for entry in entries:
            miu = entry['miu']
            
            if miu == 0.0:
                continue  # Skip baseline
            
            distorted = entry['distorted_question']
            desc = entry['miu_description']
            
            print(f"\n🔸 μ={miu} ({desc}):")
            if len(distorted) > 200:
                print(f"   {distorted[:200]}...")
            else:
                print(f"   {distorted}")


def display_statistics(results: List[Dict[str, Any]], stats: Dict[str, int]):
    """Display generation statistics."""
    
    print("\n" + "=" * 70)
    print("  📊 GENERATION STATISTICS")
    print("=" * 70)
    
    df = pd.DataFrame(results)
    
    print(f"\n📈 Dataset Summary:")
    print(f"   • Total entries: {len(results)}")
    print(f"   • Unique questions: {df['question_id'].nunique()}")
    print(f"   • μ levels: {sorted(df['miu'].unique().tolist())}")
    
    print(f"\n🔄 API Statistics:")
    print(f"   • Total requests: {stats['total_requests']}")
    print(f"   • Successful: {stats['successful']}")
    print(f"   • Failed: {stats['failed']}")
    print(f"   • Retries: {stats['retries']}")
    
    success_rate = (stats['successful'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
    print(f"   • Success rate: {success_rate:.1f}%")
    
    print(f"\n📋 Entries per μ level:")
    for miu in sorted(df['miu'].unique()):
        count = len(df[df['miu'] == miu])
        desc = get_miu_level_description(miu)
        print(f"   • μ={miu} ({desc}): {count}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="🦎 Chameleon - OmniMath Distortion Generator"
    )
    
    parser.add_argument(
        '--pilot', 
        action='store_true',
        help=f"Run pilot test with {Config.PILOT_QUESTION_COUNT} questions"
    )
    
    parser.add_argument(
        '--full',
        action='store_true', 
        help="Run full generation"
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help=f"Number of questions (default: {Config.DEFAULT_QUESTION_COUNT} for full, {Config.PILOT_QUESTION_COUNT} for pilot)"
    )
    
    parser.add_argument(
        '--miu-levels',
        type=float,
        nargs='+',
        default=None,
        help="Specific μ levels to use (default: all 0.0-0.9)"
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    
    parser.add_argument(
        '--offset',
        type=int,
        default=0,
        help="Skip first N questions (for batched generation)"
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=str(Config.OUTPUT_DIR),
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    # Determine settings based on mode
    if args.pilot:
        question_count = args.count or Config.PILOT_QUESTION_COUNT
        miu_levels = args.miu_levels or Config.PILOT_MIU_LEVELS
        mode = "PILOT"
    else:
        question_count = args.count or Config.DEFAULT_QUESTION_COUNT
        miu_levels = args.miu_levels or Config.ALL_MIU_LEVELS
        mode = "FULL" if args.full else "CUSTOM"
    
    # Print header
    print("\n" + "=" * 70)
    print("  🦎 CHAMELEON - OmniMath Distortion Generator")
    print("=" * 70)
    print(f"  Mode: {mode}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model: {Config.MODEL}")
    print(f"  Questions: {question_count}")
    if args.offset > 0:
        print(f"  Offset: {args.offset} (batch mode)")
    print(f"  μ levels: {miu_levels}")
    print(f"  Max difficulty: {Config.MAX_DIFFICULTY}")
    
    # Initialize generator
    generator = OmniMathDistortionGenerator()
    
    # Load questions
    questions = generator.load_questions(question_count, random_seed=args.seed, offset=args.offset)
    
    if not questions:
        print("❌ No questions loaded. Exiting.")
        sys.exit(1)
    
    # Generate distortions
    results = generator.generate_all_distortions(questions, miu_levels)
    
    # Display sample results
    display_sample_results(results, count=2)
    
    # Display statistics
    display_statistics(results, generator.stats)
    
    # Save results
    output_dir = Path(args.output_dir)
    if args.pilot:
        prefix = "pilot"
    elif args.offset > 0:
        # Batch mode: include batch number in filename
        batch_num = (args.offset // question_count) + 1
        prefix = f"omnimath_batch{batch_num}"
    else:
        prefix = "omnimath_batch1"
    saved_files = generator.save_results(results, output_dir, prefix)
    
    print("\n" + "=" * 70)
    print("  ✅ GENERATION COMPLETE")
    print("=" * 70)
    print(f"\n💾 Output files:")
    for file_type, path in saved_files.items():
        print(f"   • {file_type.upper()}: {path}")
    
    print("\n📋 Next Steps:")
    if args.pilot:
        print("  1. Review the generated distortions manually")
        print("  2. Check that mathematical meaning is preserved")
        print("  3. Verify answers remain correct")
        print("  4. If satisfied, run full generation with --full --count 200")
    else:
        print("  1. Review sample distortions for quality")
        print("  2. Run validation script on the dataset")
        print("  3. Dataset is ready for downstream research tasks")
    
    print("\n")


if __name__ == "__main__":
    main()

