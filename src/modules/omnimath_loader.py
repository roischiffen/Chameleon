"""
🦎 Chameleon Framework - OmniMath Dataset Loader
================================================

Loads and filters OmniMath competition mathematics problems from HuggingFace.
Filters for Easy and Medium difficulty levels (difficulty ≤ 5).

Author: Chameleon Framework
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class OmniMathLoader:
    """
    Loader for OmniMath dataset from HuggingFace.
    
    OmniMath is a competition mathematics benchmark with problems
    ranging from easy (difficulty ~1) to very hard (difficulty ~10).
    
    For this project, we focus on Easy + Medium difficulty (≤5).
    """
    
    DATASET_ID = "KbsdJames/Omni-MATH"
    
    # Difficulty thresholds
    EASY_MAX = 3.0       # Easy: difficulty ≤ 3
    MEDIUM_MAX = 5.0     # Medium: 3 < difficulty ≤ 5
    HARD_MIN = 5.0       # Hard: difficulty > 5 (excluded)
    
    def __init__(self, max_difficulty: float = 5.0):
        """
        Initialize the OmniMath loader.
        
        Args:
            max_difficulty: Maximum difficulty to include (default 5.0 for Easy+Medium)
        """
        self.max_difficulty = max_difficulty
        self.dataset = None
        self.filtered_questions = []
        
    def load_dataset(self) -> bool:
        """
        Load OmniMath dataset from HuggingFace.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from datasets import load_dataset
            
            logger.info(f"📚 Loading OmniMath dataset from HuggingFace ({self.DATASET_ID})...")
            
            # Load the test split (OmniMath has test split with problems)
            self.dataset = load_dataset(self.DATASET_ID, split="test")
            
            logger.info(f"✅ Loaded {len(self.dataset)} total problems from OmniMath")
            
            return True
            
        except ImportError:
            logger.error("❌ 'datasets' library not installed. Install with: pip install datasets")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load OmniMath: {e}")
            return False
    
    def filter_by_difficulty(self, max_difficulty: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Filter questions by difficulty level.
        
        Args:
            max_difficulty: Maximum difficulty (default: self.max_difficulty)
            
        Returns:
            List of filtered question dictionaries
        """
        if self.dataset is None:
            if not self.load_dataset():
                return []
        
        max_diff = max_difficulty or self.max_difficulty
        
        logger.info(f"🔍 Filtering for difficulty ≤ {max_diff}...")
        
        filtered = []
        difficulty_distribution = {"easy": 0, "medium": 0}
        domain_distribution = {}
        
        for idx, item in enumerate(self.dataset):
            difficulty = item.get('difficulty', 10.0)
            
            # Skip if difficulty exceeds threshold
            if difficulty > max_diff:
                continue
            
            # Categorize difficulty
            if difficulty <= self.EASY_MAX:
                diff_category = "easy"
                difficulty_distribution["easy"] += 1
            else:
                diff_category = "medium"
                difficulty_distribution["medium"] += 1
            
            # Extract domain/subject
            domain = item.get('domain', item.get('subject', 'Unknown'))
            if isinstance(domain, list):
                domain_str = domain[0] if domain else 'Unknown'
            else:
                domain_str = str(domain)
            
            # Track domain distribution
            domain_distribution[domain_str] = domain_distribution.get(domain_str, 0) + 1
            
            # Create question entry
            question_entry = {
                'question_id': idx + 1,
                'question': item.get('problem', item.get('question', '')),
                'correct_answer': item.get('answer', item.get('solution', '')),
                'subject': domain if isinstance(domain, list) else [domain],
                'domain': domain_str,
                'difficulty': difficulty,
                'difficulty_category': diff_category,
                'source': 'omnimath'
            }
            
            filtered.append(question_entry)
        
        self.filtered_questions = filtered
        
        # Log statistics
        logger.info(f"✅ Filtered to {len(filtered)} questions (difficulty ≤ {max_diff})")
        logger.info(f"   📊 Difficulty distribution:")
        logger.info(f"      • Easy (≤{self.EASY_MAX}): {difficulty_distribution['easy']}")
        logger.info(f"      • Medium ({self.EASY_MAX}-{self.MEDIUM_MAX}): {difficulty_distribution['medium']}")
        logger.info(f"   📊 Domain distribution (top 5):")
        
        sorted_domains = sorted(domain_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
        for domain, count in sorted_domains:
            logger.info(f"      • {domain}: {count}")
        
        return filtered
    
    def get_questions(self, 
                      count: Optional[int] = None,
                      difficulty_category: Optional[str] = None,
                      domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get filtered questions with optional additional filters.
        
        Args:
            count: Maximum number of questions to return
            difficulty_category: Filter by 'easy' or 'medium'
            domain_filter: Filter by domain (partial match)
            
        Returns:
            List of question dictionaries
        """
        if not self.filtered_questions:
            self.filter_by_difficulty()
        
        questions = self.filtered_questions.copy()
        
        # Apply difficulty category filter
        if difficulty_category:
            questions = [q for q in questions if q['difficulty_category'] == difficulty_category.lower()]
        
        # Apply domain filter
        if domain_filter:
            questions = [q for q in questions 
                        if domain_filter.lower() in q['domain'].lower()]
        
        # Limit count
        if count and len(questions) > count:
            questions = questions[:count]
        
        logger.info(f"📋 Returning {len(questions)} questions")
        
        return questions
    
    def get_random_sample(self, 
                          count: int,
                          seed: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get a random sample of filtered questions.
        
        Args:
            count: Number of questions to sample
            seed: Random seed for reproducibility
            
        Returns:
            List of sampled question dictionaries
        """
        import random
        
        if not self.filtered_questions:
            self.filter_by_difficulty()
        
        if seed is not None:
            random.seed(seed)
        
        if count >= len(self.filtered_questions):
            logger.warning(f"Requested {count} questions but only {len(self.filtered_questions)} available")
            return self.filtered_questions.copy()
        
        sampled = random.sample(self.filtered_questions, count)
        
        logger.info(f"🎲 Sampled {len(sampled)} questions (seed={seed})")
        
        return sampled
    
    def save_filtered_questions(self, 
                                 output_path: str,
                                 questions: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Save filtered questions to JSON file.
        
        Args:
            output_path: Path to save JSON file
            questions: Questions to save (default: self.filtered_questions)
            
        Returns:
            Path to saved file
        """
        questions = questions or self.filtered_questions
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(questions)} questions to {output_file}")
        
        return str(output_file)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the filtered dataset.
        
        Returns:
            Dictionary with dataset statistics
        """
        if not self.filtered_questions:
            self.filter_by_difficulty()
        
        questions = self.filtered_questions
        
        # Calculate statistics
        difficulties = [q['difficulty'] for q in questions]
        domains = [q['domain'] for q in questions]
        
        stats = {
            'total_questions': len(questions),
            'difficulty': {
                'min': min(difficulties) if difficulties else 0,
                'max': max(difficulties) if difficulties else 0,
                'mean': sum(difficulties) / len(difficulties) if difficulties else 0,
                'easy_count': sum(1 for d in difficulties if d <= self.EASY_MAX),
                'medium_count': sum(1 for d in difficulties if d > self.EASY_MAX)
            },
            'domains': {},
            'question_length': {
                'min': min(len(q['question']) for q in questions) if questions else 0,
                'max': max(len(q['question']) for q in questions) if questions else 0,
                'mean': sum(len(q['question']) for q in questions) / len(questions) if questions else 0
            }
        }
        
        # Domain distribution
        for domain in domains:
            stats['domains'][domain] = stats['domains'].get(domain, 0) + 1
        
        return stats
    
    def display_sample(self, count: int = 3):
        """
        Display sample questions for human review.
        
        Args:
            count: Number of questions to display
        """
        if not self.filtered_questions:
            self.filter_by_difficulty()
        
        print("\n" + "=" * 70)
        print("  📋 SAMPLE OMNIMATH QUESTIONS")
        print("=" * 70)
        
        for i, q in enumerate(self.filtered_questions[:count]):
            print(f"\n{'─' * 60}")
            print(f"Question {q['question_id']} | Difficulty: {q['difficulty']:.1f} ({q['difficulty_category']})")
            print(f"Domain: {q['domain']}")
            print(f"{'─' * 60}")
            
            # Display question (truncated if long)
            question = q['question']
            if len(question) > 300:
                print(f"Question: {question[:300]}...")
            else:
                print(f"Question: {question}")
            
            # Display answer (truncated if long)
            answer = str(q['correct_answer'])
            if len(answer) > 100:
                print(f"Answer: {answer[:100]}...")
            else:
                print(f"Answer: {answer}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main function to test the loader."""
    print("\n" + "=" * 70)
    print("  🦎 CHAMELEON - OmniMath Loader Test")
    print("=" * 70)
    
    # Initialize loader with max difficulty 5 (Easy + Medium)
    loader = OmniMathLoader(max_difficulty=5.0)
    
    # Load and filter dataset
    questions = loader.filter_by_difficulty()
    
    if not questions:
        print("❌ No questions loaded")
        return
    
    # Display statistics
    stats = loader.get_statistics()
    print("\n📊 Dataset Statistics:")
    print(f"   • Total questions: {stats['total_questions']}")
    print(f"   • Difficulty range: {stats['difficulty']['min']:.1f} - {stats['difficulty']['max']:.1f}")
    print(f"   • Mean difficulty: {stats['difficulty']['mean']:.2f}")
    print(f"   • Easy questions: {stats['difficulty']['easy_count']}")
    print(f"   • Medium questions: {stats['difficulty']['medium_count']}")
    
    # Display sample
    loader.display_sample(3)
    
    print("\n" + "=" * 70)
    print("  ✅ OmniMath Loader Test Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

