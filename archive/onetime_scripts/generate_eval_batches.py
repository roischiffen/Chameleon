#!/usr/bin/env python3
"""
Generate Evaluation Batches Flow

Converts all distortion batch files to JSONL format for OpenAI Batch API.

Usage:
    python omnimath_distortion_workflow/flows/generate_eval_batches.py

Output:
    Creates JSONL files in omnimath_distortion_workflow/evaluation/batches/
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from omnimath_distortion_workflow.modules.batch_converter import (
    convert_all_batches,
    validate_jsonl
)


def main():
    """Main entry point for batch generation."""
    
    print("=" * 60)
    print("OmniMath Evaluation Batch Generator")
    print("=" * 60)
    
    # Define paths
    input_dir = project_root / "omnimath_distortion_workflow" / "data" / "batches"
    output_dir = project_root / "omnimath_distortion_workflow" / "evaluation" / "batches"
    
    print(f"\nInput:  {input_dir}")
    print(f"Output: {output_dir}")
    print()
    
    # Convert all batches
    print("Converting batches to JSONL format...")
    summary = convert_all_batches(input_dir, output_dir)
    
    # Print summary
    print("\n" + "-" * 60)
    print("CONVERSION SUMMARY")
    print("-" * 60)
    
    total_requests = 0
    for batch_name, count in sorted(summary.items()):
        print(f"  {batch_name}: {count:,} requests")
        total_requests += count
    
    print(f"\n  TOTAL: {total_requests:,} requests")
    
    # Validate all generated files
    print("\n" + "-" * 60)
    print("VALIDATION")
    print("-" * 60)
    
    all_valid = True
    for batch_name in sorted(summary.keys()):
        jsonl_file = output_dir / f"eval_{batch_name}.jsonl"
        if jsonl_file.exists():
            validation = validate_jsonl(jsonl_file)
            status = "✅" if validation["valid"] else "❌"
            print(f"  {status} {jsonl_file.name}: {validation['unique_custom_ids']} unique IDs")
            
            if not validation["valid"]:
                all_valid = False
                if validation["duplicate_ids"]:
                    print(f"      Duplicates: {validation['duplicate_ids'][:3]}...")
                if validation["errors"]:
                    print(f"      Errors: {validation['errors'][:3]}...")
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All batches converted and validated successfully!")
    else:
        print("❌ Some validation errors occurred. Review output above.")
    print("=" * 60)
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())

