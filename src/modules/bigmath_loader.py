"""
🦎 Chameleon Framework - Big-Math RL-Verified Dataset Loader
=============================================================

Loads and filters mathematically verified problems from the Big-Math
RL-Verified dataset on HuggingFace.

This loader replaces omnimath_loader.py and provides:
- Access to verified, solvable mathematical problems
- Closed-form answers suitable for deterministic verification
- Difficulty tier system (T0-T4)
- Filtering for Omni-MATH source problems

Dataset: SynthLabsAI/Big-Math-RL-Verified
Documentation: docs/RESEARCH_TRANSITION_PLAN.md

Author: Chameleon Framework
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class BigMathLoader:
    """
    Loader for Big-Math RL-Verified dataset from HuggingFace.
    
    This dataset contains mathematically verified problems with:
    - Guaranteed solvability (all problems are self-contained)
    - Closed-form answers (deterministically verifiable)
    - Quality-controlled content (no missing diagrams, truncated text)
    
    The loader focuses on the Omni-MATH subset for compatibility with
    existing Chameleon research.
    """
    
    DATASET_ID = "SynthLabsAI/Big-Math-RL-Verified"
    
    # Difficulty tier thresholds (level ranges)
    TIER_MAP: Dict[str, Tuple[float, float]] = {
        "T4": (1.0, 3.0),    # Introductory: AMC 8, Fermat (low)
        "T3": (3.0, 5.0),    # Transitional: AMC 10, Fermat (high)
        "T2": (5.0, 7.5),    # Intermediate: AIME, AMC 12
        "T1": (7.5, 9.0),    # National: USAMO, National Olympiads
        "T0": (9.0, 10.0),   # Worldwide: IMO, Putnam
    }
    
    # Tier descriptions
    TIER_DESCRIPTIONS = {
        "T4": "Introductory (AMC 8, Fermat)",
        "T3": "Transitional (AMC 10)",
        "T2": "Intermediate (AIME, AMC 12)",
        "T1": "National (USAMO)",
        "T0": "Worldwide (IMO, Putnam)",
    }
    
    def __init__(
        self, 
        tier: str = "T4",
        source_filter: str = "omnimath",
        include_reformulated: bool = True
    ):
        """
        Initialize the Big-Math loader.
        
        Args:
            tier: Difficulty tier (T0-T4). Default T4 for introductory.
            source_filter: Filter by source dataset. Default "omni-math".
            include_reformulated: Include problems converted from MC to open-ended.
        """
        if tier not in self.TIER_MAP:
            raise ValueError(f"Invalid tier '{tier}'. Must be one of: {list(self.TIER_MAP.keys())}")
        
        self.tier = tier
        self.source_filter = source_filter
        self.include_reformulated = include_reformulated
        
        self.dataset = None
        self.filtered_questions: List[Dict[str, Any]] = []
        
        # Statistics
        self.stats = {
            "total_loaded": 0,
            "after_source_filter": 0,
            "after_tier_filter": 0,
            "reformulated_count": 0,
        }
    
    def load_dataset(self) -> bool:
        """
        Load Big-Math RL-Verified dataset from HuggingFace.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from datasets import load_dataset
            import os
            
            logger.info(f"📚 Loading Big-Math RL-Verified from HuggingFace...")
            logger.info(f"   Dataset: {self.DATASET_ID}")
            
            # Get token from environment or HuggingFace cache
            token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
            
            # Load the dataset (typically 'train' split for RL datasets)
            # Pass token explicitly to ensure authentication
            if token:
                self.dataset = load_dataset(self.DATASET_ID, split="train", token=token)
            else:
                self.dataset = load_dataset(self.DATASET_ID, split="train")
            
            self.stats["total_loaded"] = len(self.dataset)
            logger.info(f"✅ Loaded {self.stats['total_loaded']} total problems")
            
            return True
            
        except ImportError:
            logger.error("❌ 'datasets' library not installed. Install with: pip install datasets")
            return False
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to load Big-Math: {e}")
            
            # Check for specific permission errors
            if "public gated repositories" in error_msg.lower() or "403" in error_msg:
                logger.error("\n💡 Token Permission Issue:")
                logger.error("   Your token needs 'public gated repositories' access enabled.")
                logger.error("   Update token at: https://huggingface.co/settings/tokens")
                logger.error("   Enable: 'Read access to public gated repositories'")
            
            return False
    
    def filter_by_source(self) -> List[Dict[str, Any]]:
        """
        Filter dataset by source (e.g., 'omni-math').
        
        Returns:
            List of filtered problem dictionaries
        """
        if self.dataset is None:
            if not self.load_dataset():
                return []
        
        logger.info(f"🔍 Filtering for source='{self.source_filter}'...")
        
        filtered = []
        for item in self.dataset:
            source = item.get("source", "")
            if source.lower() == self.source_filter.lower():
                filtered.append(item)
        
        self.stats["after_source_filter"] = len(filtered)
        logger.info(f"   Found {len(filtered)} problems from '{self.source_filter}'")
        
        return filtered
    
    def filter_by_tier(
        self, 
        problems: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter problems by difficulty tier.
        
        Args:
            problems: List of problems to filter. If None, filters from source-filtered set.
            
        Returns:
            List of tier-filtered problems
        """
        if problems is None:
            problems = self.filter_by_source()
        
        min_level, max_level = self.TIER_MAP[self.tier]
        
        logger.info(f"🔍 Filtering for tier {self.tier} (level {min_level}-{max_level})...")
        
        # Check if level field exists
        has_level_field = problems and "level" in problems[0] if problems else False
        if not has_level_field:
            logger.warning("⚠️  Dataset doesn't have 'level' field - tier filtering will be skipped")
        
        filtered = []
        reformulated = 0
        
        for item in problems:
            level = item.get("level", None)
            
            # If level field doesn't exist, include all items (tier filtering skipped)
            if level is None:
                # Check reformulated filter
                is_reformulated = item.get("is_reformulated", False)
                if is_reformulated:
                    reformulated += 1
                    if not self.include_reformulated:
                        continue
                
                filtered.append(item)
            # Check if within tier range
            elif min_level <= level < max_level:
                # Check reformulated filter
                is_reformulated = item.get("is_reformulated", False)
                if is_reformulated:
                    reformulated += 1
                    if not self.include_reformulated:
                        continue
                
                filtered.append(item)
        
        self.stats["after_tier_filter"] = len(filtered)
        self.stats["reformulated_count"] = reformulated
        
        logger.info(f"   Found {len(filtered)} problems in tier {self.tier}")
        if reformulated > 0:
            logger.info(f"   ({reformulated} were reformulated from MC to open-ended)")
        
        return filtered
    
    def get_verified_questions(
        self,
        count: Optional[int] = None,
        random_sample: bool = False,
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Get verified questions with standardized schema.
        
        Args:
            count: Maximum number of questions to return (None = all)
            random_sample: If True, randomly sample. If False, take first N.
            seed: Random seed for reproducibility
            
        Returns:
            List of question dictionaries in standardized format
        """
        # Apply filters
        tier_filtered = self.filter_by_tier()
        
        if not tier_filtered:
            logger.warning("⚠️ No questions found after filtering")
            return []
        
        # Convert to standardized schema
        questions = []
        for item in tier_filtered:
            question = self._standardize_schema(item)
            questions.append(question)
        
        # Sort by question_id for consistency
        questions.sort(key=lambda x: x["question_id"])
        
        # Apply count limit
        if count is not None and count < len(questions):
            if random_sample:
                import random
                random.seed(seed)
                questions = random.sample(questions, count)
                logger.info(f"🎲 Randomly sampled {count} questions (seed={seed})")
            else:
                questions = questions[:count]
                logger.info(f"📋 Selected first {count} questions")
        
        self.filtered_questions = questions
        
        logger.info(f"✅ Returning {len(questions)} verified questions")
        
        return questions
    
    def _standardize_schema(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw dataset item to standardized Chameleon schema.
        
        Args:
            item: Raw item from Big-Math dataset
            
        Returns:
            Standardized question dictionary
        """
        # Extract fields with fallbacks
        # Try to generate a unique ID from problem text hash if no ID exists
        question_id = item.get("id") or item.get("problem_id")
        if not question_id:
            import hashlib
            problem_text = str(item.get("problem", ""))
            question_id = hashlib.md5(problem_text.encode()).hexdigest()[:12]
        level = item.get("level", None)
        
        # Map level to tier (if level exists)
        if level is not None:
            tier = self._level_to_tier(level)
        else:
            tier = self.tier  # Use current tier if level not available
        
        # Build standardized record
        return {
            # Core fields
            "question_id": question_id,
            "problem": item.get("problem", item.get("question", "")),
            "answer": item.get("answer", item.get("solution", "")),
            
            # Difficulty (may not exist in dataset)
            "level": item.get("level", None),
            "tier": tier,
            "tier_description": self.TIER_DESCRIPTIONS.get(tier, "Unknown"),
            
            # Metadata
            "domain": item.get("domain", item.get("category", "")),
            "subject": item.get("subject", []),
            "source": item.get("source", "omni-math"),
            
            # Verification status
            "is_verified": True,  # All Big-Math problems are verified
            "is_reformulated": item.get("is_reformulated", False),
            "verification_method": item.get("verification_method", "symbolic"),
            
            # Dataset provenance
            "source_dataset": "big-math-rl-verified",
            
            # Legacy compatibility (map to old schema)
            "original_question": item.get("problem", item.get("question", "")),
            "correct_answer": item.get("answer", item.get("solution", "")),
            "difficulty": level if level is not None else None,
            "difficulty_category": self._level_to_category(level),
        }
    
    def _level_to_tier(self, level: float) -> str:
        """Map numeric level to tier code."""
        for tier_code, (min_l, max_l) in self.TIER_MAP.items():
            if min_l <= level < max_l:
                return tier_code
        return "T4"  # Default to introductory
    
    def _level_to_category(self, level: Optional[float]) -> str:
        """Map numeric level to difficulty category (legacy compatibility)."""
        if level is None:
            return "unknown"  # Default when level not available
        if level < 3.0:
            return "easy"
        elif level < 5.0:
            return "medium"
        elif level < 7.5:
            return "hard"
        else:
            return "expert"
    
    def save_to_json(
        self, 
        output_path: str,
        questions: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Save filtered questions to JSON file.
        
        Args:
            output_path: Path to output JSON file
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
        Get statistics about the loaded/filtered dataset.
        
        Returns:
            Dictionary with dataset statistics
        """
        questions = self.filtered_questions
        
        if not questions:
            return {"error": "No questions loaded. Call get_verified_questions() first."}
        
        levels = [q["level"] for q in questions if q.get("level") is not None]
        domains = []
        for q in questions:
            domain = q.get("domain", "Unknown")
            # Handle domain as list or string
            if isinstance(domain, list):
                domains.extend(domain if domain else ["Unknown"])
            else:
                domains.append(str(domain) if domain else "Unknown")
        
        # Domain distribution
        domain_counts = {}
        for d in domains:
            domain_counts[d] = domain_counts.get(d, 0) + 1
        
        return {
            "total_questions": len(questions),
            "tier": self.tier,
            "tier_description": self.TIER_DESCRIPTIONS[self.tier],
            "level_range": {
                "min": min(levels) if levels else None,
                "max": max(levels) if levels else None,
                "mean": sum(levels) / len(levels) if levels else None,
            },
            "reformulated_count": self.stats.get("reformulated_count", 0),
            "domains": dict(sorted(domain_counts.items(), key=lambda x: -x[1])[:10]),
            "source_filter": self.source_filter,
            "include_reformulated": self.include_reformulated,
            "all_verified": True,
        }
    
    def display_sample(self, count: int = 3):
        """
        Display sample questions for human review.
        
        Args:
            count: Number of questions to display
        """
        if not self.filtered_questions:
            print("❌ No questions loaded. Call get_verified_questions() first.")
            return
        
        print("\n" + "=" * 70)
        print(f"  📋 SAMPLE VERIFIED QUESTIONS (Tier {self.tier})")
        print("=" * 70)
        
        for q in self.filtered_questions[:count]:
            print(f"\n{'─' * 65}")
            print(f"ID: {q['question_id']} | Level: {q['level']:.1f} | Tier: {q['tier']}")
            print(f"Domain: {q.get('domain', 'N/A')}")
            if q.get('is_reformulated'):
                print("⚠️ Reformulated from Multiple Choice")
            print(f"{'─' * 65}")
            
            # Display problem (truncated if long)
            problem = q['problem']
            if len(problem) > 300:
                print(f"Problem: {problem[:300]}...")
            else:
                print(f"Problem: {problem}")
            
            # Display answer
            answer = str(q['answer'])
            if len(answer) > 100:
                print(f"Answer: {answer[:100]}...")
            else:
                print(f"Answer: {answer}")
        
        print("\n" + "=" * 70)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def load_tier_questions(
    tier: str = "T4",
    count: Optional[int] = None,
    source: str = "omni-math"
) -> List[Dict[str, Any]]:
    """
    Convenience function to load questions for a specific tier.
    
    Args:
        tier: Difficulty tier (T0-T4)
        count: Number of questions (None = all)
        source: Source dataset filter
        
    Returns:
        List of verified question dictionaries
    """
    loader = BigMathLoader(tier=tier, source_filter=source)
    return loader.get_verified_questions(count=count)


def export_tier_to_chameleon_format(
    tier: str = "T4",
    output_dir: str = "data/source_verified",
    count: Optional[int] = 100
) -> Dict[str, str]:
    """
    Export a tier to Chameleon's expected directory structure.
    
    Creates:
    - {output_dir}/tier_{tier}/baseline_questions.json
    - {output_dir}/tier_{tier}/metadata.json
    
    Args:
        tier: Difficulty tier
        output_dir: Base output directory
        count: Number of questions to export
        
    Returns:
        Dictionary with paths to created files
    """
    loader = BigMathLoader(tier=tier, source_filter="omni-math")
    questions = loader.get_verified_questions(count=count)
    
    if not questions:
        logger.error(f"No questions found for tier {tier}")
        return {}
    
    tier_dir = Path(output_dir) / f"tier_{tier}"
    tier_dir.mkdir(parents=True, exist_ok=True)
    
    # Save baseline questions
    baseline_path = tier_dir / "baseline_questions.json"
    with open(baseline_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    # Save metadata
    stats = loader.get_statistics()
    metadata = {
        "tier": tier,
        "tier_description": loader.TIER_DESCRIPTIONS[tier],
        "total_questions": len(questions),
        "question_ids": [q["question_id"] for q in questions],
        "miu_levels": [0.2, 0.5, 0.7, 0.9],
        "source_dataset": "big-math-rl-verified",
        "source_filter": "omni-math",
        "level_range": stats["level_range"],
        "domains": stats["domains"],
        "all_verified": True,
    }
    
    metadata_path = tier_dir / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✅ Exported tier {tier} to {tier_dir}")
    
    return {
        "baseline": str(baseline_path),
        "metadata": str(metadata_path),
    }


# =============================================================================
# MAIN (for testing)
# =============================================================================

def main():
    """Main function to test the loader."""
    print("\n" + "=" * 70)
    print("  🦎 CHAMELEON - Big-Math RL-Verified Loader Test")
    print("=" * 70)
    
    # Test loading tier T4 (introductory)
    loader = BigMathLoader(tier="T4", source_filter="omni-math")
    
    # Get 10 sample questions
    questions = loader.get_verified_questions(count=10)
    
    if not questions:
        print("❌ No questions loaded")
        return
    
    # Display statistics
    stats = loader.get_statistics()
    print("\n📊 Dataset Statistics:")
    print(f"   • Total questions: {stats['total_questions']}")
    print(f"   • Tier: {stats['tier']} ({stats['tier_description']})")
    print(f"   • Level range: {stats['level_range']['min']:.1f} - {stats['level_range']['max']:.1f}")
    print(f"   • Reformulated (MC→Open): {stats['reformulated_count']}")
    
    # Display sample
    loader.display_sample(3)
    
    print("\n" + "=" * 70)
    print("  ✅ Big-Math Loader Test Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

