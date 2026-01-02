#!/usr/bin/env python3
"""
Direct API Retry for Token-Limit Failures

Makes synchronous API calls for questions that failed due to token limits,
with progressively higher token limits.

Usage:
    # Test mode - try 3 questions first with 2000 tokens
    python direct_api_retry.py --test --tokens 2000
    
    # Full retry for difficulty 1.5
    python direct_api_retry.py --difficulty 1.5 --tokens 2000
    
    # Retry with higher tokens if still failing
    python direct_api_retry.py --difficulty 1.5 --tokens 3500
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_paths = [
        project_root / ".env",
        project_root / "venv" / "bin" / ".env",
        Path.home() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

try:
    import openai
except ImportError:
    print("❌ Error: openai package not installed")
    sys.exit(1)

from omnimath_distortion_workflow.modules.evaluation_prompt import (
    create_evaluation_prompt,
    generate_custom_id,
    parse_custom_id
)
from omnimath_distortion_workflow.modules.answer_comparator import compare_answers

# Paths
EVAL_DIR = project_root / "omnimath_distortion_workflow" / "evaluation"
DISTORTION_RESULTS_DIR = EVAL_DIR / "distortion_results"
BASELINE_RESULTS_DIR = EVAL_DIR / "baseline_results"
DATA_DIR = project_root / "omnimath_distortion_workflow" / "data" / "by_difficulty"


def get_client() -> openai.OpenAI:
    """Get OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        sys.exit(1)
    return openai.OpenAI(api_key=api_key)


def find_token_limit_failures(difficulty: float, include_baseline: bool = True) -> List[Dict]:
    """Find all questions that failed due to token limits (empty answer + high reasoning tokens)."""
    failures = []
    diff_str = str(difficulty).replace(".", "_")
    
    # Check distortion results
    results_file = DISTORTION_RESULTS_DIR / f"gpt_5_difficulty_{diff_str}" / "results.jsonl"
    if results_file.exists():
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    if not r.get("model_answer", "").strip():
                        reasoning = r.get("reasoning_tokens", 0) or 0
                        output = r.get("output_tokens", 0) or 0
                        # Empty answer with high token usage = token limit hit
                        if reasoning >= 350 or output >= 350:
                            r["source"] = "distortion"
                            r["source_file"] = str(results_file)
                            failures.append(r)
    
    # Check baseline results
    if include_baseline:
        baseline_file = BASELINE_RESULTS_DIR / f"gpt5_baseline_difficulty_{diff_str}.json"
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
                for r in baseline_data:
                    if not r.get("model_answer", "").strip():
                        reasoning = r.get("reasoning_tokens", 0) or 0
                        output = r.get("output_tokens", 0) or 0
                        if reasoning >= 350 or output >= 350:
                            r["source"] = "baseline"
                            r["source_file"] = str(baseline_file)
                            failures.append(r)
    
    return failures


def load_question_text(difficulty: float, question_id: int, miu: float) -> str:
    """Load the question text for a given question."""
    if difficulty == int(difficulty):
        diff_str = f"difficulty_{int(difficulty)}"
    else:
        diff_str = f"difficulty_{difficulty}"
    
    # If baseline (miu=0.0), get from baseline file
    if miu == 0.0:
        baseline_file = DATA_DIR / diff_str / f"{diff_str}_baseline_questions.json"
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                questions = json.load(f)
                for q in questions:
                    if q.get("question_id") == question_id:
                        return q.get("original_question", "")
    else:
        # Get from distortions file
        distortions_file = DATA_DIR / diff_str / f"{diff_str}_distortions.json"
        if distortions_file.exists():
            with open(distortions_file, 'r') as f:
                data = json.load(f)
                for entry in data:
                    if entry.get("question_id") == question_id:
                        # Check if flat format
                        if entry.get("miu") == miu:
                            return entry.get("distorted_question", "")
                        # Check nested format
                        if "distortions" in entry:
                            for d in entry["distortions"]:
                                if d.get("miu") == miu:
                                    return d.get("distorted_question", "")
    return ""


def call_gpt5_direct(client: openai.OpenAI, question: str, max_tokens: int) -> Dict:
    """Make a direct API call to GPT-5."""
    prompt = create_evaluation_prompt(question)
    
    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_tokens,
            reasoning_effort="low",
        )
        
        choice = response.choices[0]
        answer = choice.message.content.strip() if choice.message.content else ""
        
        # Clean answer
        for pattern in [r'^the\s+answer\s+is\s*:?\s*', r'^answer\s*:?\s*', r'^=\s*']:
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE)
        answer = answer.strip().rstrip('.')
        
        usage = response.usage
        
        return {
            "model_answer": answer,
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
            "reasoning_tokens": usage.completion_tokens_details.reasoning_tokens if usage and usage.completion_tokens_details else 0,
            "finish_reason": choice.finish_reason,
            "success": True,
        }
    except Exception as e:
        return {
            "model_answer": "",
            "error": str(e),
            "success": False,
        }


def retry_failures(client: openai.OpenAI, failures: List[Dict], max_tokens: int, 
                   difficulty: float, test_mode: bool = False) -> Tuple[int, int]:
    """Retry failed questions with direct API calls."""
    
    if test_mode:
        failures = failures[:3]  # Only test first 3
    
    print(f"\n🔄 Retrying {len(failures)} questions with {max_tokens} max tokens...")
    print("=" * 60)
    
    success_count = 0
    still_failing = 0
    results_to_update = []
    
    for i, failure in enumerate(failures, 1):
        custom_id = failure.get("custom_id")
        question_id, miu = parse_custom_id(custom_id)
        ground_truth = failure.get("ground_truth", "")
        source = failure.get("source", "unknown")
        
        # Load question text
        question_text = load_question_text(difficulty, question_id, miu)
        if not question_text:
            print(f"   ⚠️  [{i}/{len(failures)}] {custom_id}: Could not find question text")
            continue
        
        print(f"\n   [{i}/{len(failures)}] {custom_id} (ground_truth: {ground_truth})")
        print(f"       Question: {question_text[:80]}...")
        
        # Make API call
        result = call_gpt5_direct(client, question_text, max_tokens)
        
        if result["success"]:
            answer = result["model_answer"]
            reasoning_tokens = result["reasoning_tokens"]
            output_tokens = result["output_tokens"]
            
            if answer:
                is_correct, match_type = compare_answers(answer, ground_truth)
                status = "✅" if is_correct else "❌"
                print(f"       Answer: {answer} {status}")
                print(f"       Tokens: output={output_tokens}, reasoning={reasoning_tokens}")
                success_count += 1
                
                # Prepare updated result
                updated = {
                    "custom_id": custom_id,
                    "question_id": question_id,
                    "miu": miu,
                    "miu_description": failure.get("miu_description", ""),
                    "domain": failure.get("domain", ""),
                    "difficulty": difficulty,
                    "difficulty_category": failure.get("difficulty_category", ""),
                    "ground_truth": ground_truth,
                    "model_answer": answer,
                    "is_correct": is_correct,
                    "match_type": match_type,
                    "input_tokens": result["input_tokens"],
                    "output_tokens": output_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "model": "gpt-5",
                    "timestamp": datetime.now().isoformat(),
                    "retry_tokens": max_tokens,
                    "source": source,
                }
                results_to_update.append(updated)
            else:
                print(f"       ⚠️  Still no answer! (reasoning={reasoning_tokens})")
                still_failing += 1
        else:
            print(f"       ❌ Error: {result.get('error', 'Unknown')}")
            still_failing += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Summary:")
    print(f"   Attempted: {len(failures)}")
    print(f"   Got answers: {success_count}")
    print(f"   Still failing: {still_failing}")
    
    return success_count, still_failing, results_to_update


def update_results_files(results: List[Dict], difficulty: float):
    """Update the results files with new answers."""
    diff_str = str(difficulty).replace(".", "_")
    
    # Separate distortion and baseline results
    distortion_updates = [r for r in results if r.get("source") == "distortion"]
    baseline_updates = [r for r in results if r.get("source") == "baseline"]
    
    # Update distortion results
    if distortion_updates:
        results_file = DISTORTION_RESULTS_DIR / f"gpt_5_difficulty_{diff_str}" / "results.jsonl"
        if results_file.exists():
            # Load existing
            existing = []
            with open(results_file, 'r') as f:
                for line in f:
                    if line.strip():
                        existing.append(json.loads(line))
            
            # Create map
            existing_map = {r.get("custom_id"): r for r in existing}
            
            # Update
            for update in distortion_updates:
                cid = update.get("custom_id")
                # Remove source field before saving
                update_clean = {k: v for k, v in update.items() if k != "source"}
                existing_map[cid] = update_clean
            
            # Write back
            with open(results_file, 'w') as f:
                for r in existing_map.values():
                    f.write(json.dumps(r) + '\n')
            
            print(f"\n   ✅ Updated {len(distortion_updates)} entries in {results_file}")
    
    # Update baseline results
    if baseline_updates:
        baseline_file = BASELINE_RESULTS_DIR / f"gpt5_baseline_difficulty_{diff_str}.json"
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                existing = json.load(f)
            
            existing_map = {r.get("custom_id"): r for r in existing}
            
            for update in baseline_updates:
                cid = update.get("custom_id")
                update_clean = {k: v for k, v in update.items() if k != "source"}
                existing_map[cid] = update_clean
            
            with open(baseline_file, 'w') as f:
                json.dump(list(existing_map.values()), f, indent=2)
            
            print(f"   ✅ Updated {len(baseline_updates)} entries in {baseline_file}")


def main():
    parser = argparse.ArgumentParser(description="Direct API retry for token-limit failures")
    parser.add_argument("--difficulty", type=float, default=1.5, choices=[1.0, 1.5])
    parser.add_argument("--tokens", type=int, default=2000, help="Max completion tokens")
    parser.add_argument("--test", action="store_true", help="Test mode - only try 3 questions")
    parser.add_argument("--apply", action="store_true", help="Apply results to files (otherwise dry-run)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Direct API Retry for Token-Limit Failures")
    print("=" * 60)
    print(f"Difficulty: {args.difficulty}")
    print(f"Max tokens: {args.tokens}")
    print(f"Mode: {'TEST (3 questions)' if args.test else 'FULL'}")
    print(f"Apply: {'YES' if args.apply else 'NO (dry-run)'}")
    
    # Find failures
    failures = find_token_limit_failures(args.difficulty)
    print(f"\n📋 Found {len(failures)} token-limit failures")
    
    if not failures:
        print("   Nothing to retry!")
        return
    
    # Show what we found
    print("\n   Failures by source:")
    distortion_count = sum(1 for f in failures if f.get("source") == "distortion")
    baseline_count = sum(1 for f in failures if f.get("source") == "baseline")
    print(f"   - Distortion: {distortion_count}")
    print(f"   - Baseline: {baseline_count}")
    
    client = get_client()
    
    # Retry
    success, still_failing, results = retry_failures(
        client, failures, args.tokens, args.difficulty, test_mode=args.test
    )
    
    # Apply if requested and not test mode
    if args.apply and results and not args.test:
        print("\n📝 Applying results to files...")
        update_results_files(results, args.difficulty)
    elif results and not args.apply:
        print("\n⚠️  Dry-run mode. Use --apply to save results.")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()





