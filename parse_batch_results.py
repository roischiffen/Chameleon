#!/usr/bin/env python3
"""
Parse batch results and extract model answers.

Usage:
    python parse_batch_results.py
"""

import json
from pathlib import Path
from collections import defaultdict

# Paths
RESULTS_DIR = Path("data/results_verified")
OUTPUT_DIR = Path("data/parsed_results")

def parse_custom_id(custom_id):
    """
    Parse custom_id to extract metadata.
    
    Format: cat{N}_q_{question_id}_miu_{miu}
    Example: cat1_q_582327ed443b_miu_0.0
    """
    parts = custom_id.split('_')
    
    category = int(parts[0].replace('cat', ''))
    question_id = parts[2]
    miu = float(parts[4])
    
    return {
        'category': category,
        'question_id': question_id,
        'miu': miu,
        'distortion_type': 'baseline' if miu == 0.0 else f'distorted_{miu}'
    }

def extract_answer(result_line):
    """Extract answer and metadata from a result line."""
    data = json.loads(result_line)
    
    # Parse custom_id
    custom_id = data['custom_id']
    metadata = parse_custom_id(custom_id)
    
    # Extract answer
    response = data.get('response', {})
    body = response.get('body', {})
    choices = body.get('choices', [])
    
    if choices:
        answer = choices[0]['message']['content']
    else:
        answer = None
    
    # Extract tokens
    usage = body.get('usage', {})
    
    return {
        'custom_id': custom_id,
        'category': metadata['category'],
        'question_id': metadata['question_id'],
        'miu': metadata['miu'],
        'distortion_type': metadata['distortion_type'],
        'model_answer': answer,
        'prompt_tokens': usage.get('prompt_tokens'),
        'completion_tokens': usage.get('completion_tokens'),
        'reasoning_tokens': usage.get('completion_tokens_details', {}).get('reasoning_tokens'),
        'total_tokens': usage.get('total_tokens'),
        'error': data.get('error')
    }

def parse_result_file(result_file):
    """Parse a single result file."""
    print(f"\n📄 Parsing: {result_file.name}")
    
    results = []
    
    with open(result_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    result = extract_answer(line)
                    results.append(result)
                except Exception as e:
                    print(f"   ⚠️  Error parsing line: {e}")
    
    print(f"   ✅ Extracted {len(results)} answers")
    
    return results

def save_parsed_results(results, model_name, output_dir):
    """Save parsed results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full results
    output_file = output_dir / f"{model_name}_parsed.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"   💾 Saved: {output_file}")
    
    # Create summary by miu level
    by_miu = defaultdict(list)
    for r in results:
        by_miu[r['miu']].append(r)
    
    summary_file = output_dir / f"{model_name}_summary.json"
    summary = {
        'model': model_name,
        'total_responses': len(results),
        'by_miu': {
            str(miu): {
                'count': len(responses),
                'sample_answers': [r['model_answer'] for r in responses[:3]]
            }
            for miu, responses in sorted(by_miu.items())
        },
        'by_category': {
            f'category_{cat}': len([r for r in results if r['category'] == cat])
            for cat in [1, 2, 3]
        }
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"   📊 Summary: {summary_file}")

def display_samples(results, model_name):
    """Display sample results."""
    print(f"\n📋 Sample answers from {model_name}:")
    print("─" * 70)
    
    for i, r in enumerate(results[:5], 1):
        print(f"\n{i}. Question: {r['question_id']}")
        print(f"   Category: {r['category']} | μ: {r['miu']}")
        print(f"   Answer: {r['model_answer']}")
        if r['reasoning_tokens']:
            print(f"   Tokens: {r['total_tokens']} (reasoning: {r['reasoning_tokens']})")
        else:
            print(f"   Tokens: {r['total_tokens']}")

def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print("  📊 BATCH RESULTS PARSER")
    print("=" * 70)
    
    # Find result files
    result_files = sorted(RESULTS_DIR.glob("*.jsonl"))
    
    if not result_files:
        print("\n❌ No result files found in data/results_verified/")
        print("   Run: python download_batch_results.py")
        return
    
    print(f"\n📁 Found {len(result_files)} result file(s):")
    for f in result_files:
        print(f"   • {f.name}")
    
    # Parse each file
    all_results = {}
    
    for result_file in result_files:
        # Extract model name from filename
        model_name = result_file.stem.replace('_results', '').replace('_20260105_024527', '').replace('_20260105_024528', '')
        
        # Parse results
        results = parse_result_file(result_file)
        all_results[model_name] = results
        
        # Save parsed results
        save_parsed_results(results, model_name, OUTPUT_DIR)
        
        # Display samples
        display_samples(results, model_name)
    
    # Overall summary
    print("\n" + "=" * 70)
    print("  ✅ PARSING COMPLETE")
    print("=" * 70)
    print(f"\n📊 Total Results:")
    for model, results in all_results.items():
        print(f"   • {model}: {len(results)} responses")
    
    print(f"\n📁 Parsed results saved to: {OUTPUT_DIR}/")
    print("\n📋 Files created:")
    for f in sorted(OUTPUT_DIR.glob("*")):
        print(f"   • {f.name}")

if __name__ == "__main__":
    main()

