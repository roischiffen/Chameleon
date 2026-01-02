"""
Batch Converter Module for OmniMath GPT-5 Evaluation

Converts distortion JSON files to JSONL format for OpenAI Batch API.
Handles baseline (μ=0.0) and distorted (μ=0.1-0.9) evaluations.

Usage:
    from modules.batch_converter import convert_all_batches
    summary = convert_all_batches(input_dir, output_dir)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Set

# Handle imports for both direct execution and module import
try:
    from src.modules.evaluation_prompt import (
        create_batch_request,
        generate_custom_id
    )
except ModuleNotFoundError:
    # When run directly, add parent to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.modules.evaluation_prompt import (
        create_batch_request,
        generate_custom_id
    )


def load_distortion_batch(batch_path: Path) -> List[dict]:
    """
    Load a distortion JSON file from a batch directory.
    
    Args:
        batch_path: Path to the batch directory (e.g., data/batches/batch1/)
                   OR path to the JSON file directly
        
    Returns:
        List of distortion entries
        
    Raises:
        FileNotFoundError: If no JSON file found in batch directory
        
    Examples:
        >>> distortions = load_distortion_batch(Path("data/batches/batch1/"))
        >>> len(distortions) > 0
        True
    """
    batch_path = Path(batch_path)
    
    # If it's a directory, find the JSON file
    if batch_path.is_dir():
        json_files = list(batch_path.glob("*_distortions_*.json"))
        if not json_files:
            raise FileNotFoundError(f"No distortion JSON file found in {batch_path}")
        json_file = json_files[0]
    else:
        json_file = batch_path
    
    with open(json_file, 'r', encoding='utf-8') as f:
        distortions = json.load(f)
    
    return distortions


def convert_batch_to_jsonl(distortions: List[dict], output_path: Path) -> int:
    """
    Convert distortion entries to JSONL format for OpenAI Batch API.
    
    For each unique question:
    - Creates ONE baseline request (μ=0.0) using original_question
    - Creates distorted requests for each μ level using distorted_question
    
    Args:
        distortions: List of distortion entries from JSON file
        output_path: Path to output JSONL file
        
    Returns:
        Count of requests written
        
    Note:
        Deduplicates baselines - each question_id gets only ONE μ=0.0 entry
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    requests = []
    seen_baselines: Set[int] = set()  # Track which question_ids have baseline
    
    for entry in distortions:
        question_id = entry["question_id"]
        
        # 1. Create BASELINE request (μ=0.0) - only once per question_id
        if question_id not in seen_baselines:
            baseline_request = create_batch_request(
                question_id=question_id,
                miu=0.0,
                question=entry["original_question"]
            )
            requests.append(baseline_request)
            seen_baselines.add(question_id)
        
        # 2. Create DISTORTED request using actual μ level
        distorted_request = create_batch_request(
            question_id=question_id,
            miu=entry["miu"],
            question=entry["distorted_question"]
        )
        requests.append(distorted_request)
    
    # Write to JSONL (one JSON object per line)
    with open(output_path, 'w', encoding='utf-8') as f:
        for request in requests:
            f.write(json.dumps(request) + '\n')
    
    return len(requests)


def convert_all_batches(input_dir: Path, output_dir: Path) -> Dict[str, int]:
    """
    Convert all batch directories to JSONL files.
    
    Args:
        input_dir: Directory containing batch subdirectories (batch1, batch2, etc.)
        output_dir: Directory to write output JSONL files
        
    Returns:
        Summary dict: {batch_name: request_count}
        
    Example:
        >>> summary = convert_all_batches(
        ...     Path("data/batches"),
        ...     Path("evaluation/batches")
        ... )
        >>> "batch1" in summary
        True
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {}
    
    # Find all batch directories
    batch_dirs = sorted([d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("batch")])
    
    if not batch_dirs:
        print(f"Warning: No batch directories found in {input_dir}")
        return summary
    
    for batch_dir in batch_dirs:
        batch_name = batch_dir.name
        
        try:
            # Load distortions
            distortions = load_distortion_batch(batch_dir)
            
            # Output file name
            output_file = output_dir / f"eval_{batch_name}.jsonl"
            
            # Convert to JSONL
            count = convert_batch_to_jsonl(distortions, output_file)
            
            summary[batch_name] = count
            print(f"  ✓ {batch_name}: {count} requests → {output_file.name}")
            
        except Exception as e:
            print(f"  ✗ {batch_name}: Error - {e}")
            summary[batch_name] = 0
    
    return summary


def validate_jsonl(jsonl_path: Path) -> Dict[str, any]:
    """
    Validate a JSONL file for OpenAI Batch API format.
    
    Args:
        jsonl_path: Path to JSONL file
        
    Returns:
        Validation result dict with stats and any errors
    """
    jsonl_path = Path(jsonl_path)
    
    result = {
        "valid": True,
        "total_lines": 0,
        "custom_ids": set(),
        "duplicate_ids": [],
        "errors": [],
        "miu_counts": {}
    }
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            result["total_lines"] += 1
            
            try:
                request = json.loads(line.strip())
                
                # Check required fields
                if "custom_id" not in request:
                    result["errors"].append(f"Line {line_num}: missing custom_id")
                    result["valid"] = False
                else:
                    custom_id = request["custom_id"]
                    if custom_id in result["custom_ids"]:
                        result["duplicate_ids"].append(custom_id)
                        result["valid"] = False
                    result["custom_ids"].add(custom_id)
                    
                    # Extract miu for stats
                    if "_miu_" in custom_id:
                        miu = custom_id.split("_miu_")[1]
                        result["miu_counts"][miu] = result["miu_counts"].get(miu, 0) + 1
                
                if "method" not in request or request["method"] != "POST":
                    result["errors"].append(f"Line {line_num}: invalid method")
                    result["valid"] = False
                    
                if "body" not in request:
                    result["errors"].append(f"Line {line_num}: missing body")
                    result["valid"] = False
                    
            except json.JSONDecodeError as e:
                result["errors"].append(f"Line {line_num}: invalid JSON - {e}")
                result["valid"] = False
    
    # Convert set to count for return
    result["unique_custom_ids"] = len(result["custom_ids"])
    del result["custom_ids"]
    
    return result


# Simple test/demo when executed directly
if __name__ == "__main__":
    import sys
    
    print("Testing Batch Converter Module\n")
    print("=" * 60)
    
    # Define paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    input_dir = project_root / "data" / "source"
    output_dir = project_root / "data" / "results"
    
    print(f"\nInput directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Test 1: Load a single batch
    print("\n1. Testing load_distortion_batch()")
    try:
        batch1_path = input_dir / "batch1"
        distortions = load_distortion_batch(batch1_path)
        print(f"   ✅ Loaded {len(distortions)} distortion entries from batch1")
        
        # Show sample entry
        if distortions:
            sample = distortions[0]
            print(f"   Sample entry:")
            print(f"      question_id: {sample['question_id']}")
            print(f"      miu: {sample['miu']}")
            print(f"      original_question: {sample['original_question'][:50]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)
    
    # Test 2: Convert single batch
    print("\n2. Testing convert_batch_to_jsonl() with batch1")
    try:
        test_output = output_dir / "eval_batch1.jsonl"
        count = convert_batch_to_jsonl(distortions, test_output)
        print(f"   ✅ Wrote {count} requests to {test_output.name}")
        
        # Calculate expected: 50 questions × (1 baseline + 9 distortions) = 500
        unique_questions = len(set(d["question_id"] for d in distortions))
        expected = unique_questions * 10  # 1 baseline + 9 distortions
        print(f"   Unique questions: {unique_questions}")
        print(f"   Expected requests: {expected}")
        print(f"   Actual requests: {count}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)
    
    # Test 3: Validate JSONL
    print("\n3. Testing validate_jsonl()")
    try:
        validation = validate_jsonl(test_output)
        print(f"   Valid: {validation['valid']}")
        print(f"   Total lines: {validation['total_lines']}")
        print(f"   Unique custom_ids: {validation['unique_custom_ids']}")
        print(f"   μ distribution: {validation['miu_counts']}")
        
        if validation["duplicate_ids"]:
            print(f"   ⚠️ Duplicate IDs: {validation['duplicate_ids'][:5]}")
        if validation["errors"]:
            print(f"   ⚠️ Errors: {validation['errors'][:5]}")
            
        if validation["valid"]:
            print("   ✅ JSONL validation passed!")
        else:
            print("   ❌ JSONL validation failed!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Check baseline entries exist
    print("\n4. Checking baseline (μ=0.0) entries")
    baseline_count = validation["miu_counts"].get("0.0", 0)
    print(f"   Baseline entries (μ=0.0): {baseline_count}")
    if baseline_count == unique_questions:
        print(f"   ✅ Correct: {baseline_count} baselines for {unique_questions} questions")
    else:
        print(f"   ❌ Mismatch: expected {unique_questions}, got {baseline_count}")
    
    print("\n" + "=" * 60)
    print("Batch converter tests completed!")

