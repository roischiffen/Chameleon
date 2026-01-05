#!/usr/bin/env python3
"""
Reorganize model results from model-centric to category-centric structure.
New structure: data/category_X/model_name_results.json
Each file contains questions with baseline + 4 distortions grouped together.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any


def load_jsonl(filepath: str) -> List[Dict]:
    """Load JSONL file."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def load_json(filepath: str) -> Any:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, filepath: str):
    """Save JSON file with pretty printing."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_custom_id(custom_id: str) -> Dict[str, str]:
    """Parse custom_id to extract category, question_id, and miu_level.
    Format: cat{category}_q_{question_id}_miu_{miu_level}
    """
    parts = custom_id.split('_')
    category = parts[0].replace('cat', '')
    question_id = parts[2]
    miu_level = parts[4]
    return {
        'category': category,
        'question_id': question_id,
        'miu_level': miu_level
    }


def get_model_answer(result_entry: Dict) -> Dict[str, Any]:
    """Extract model answer and metadata from result entry."""
    try:
        content = result_entry['response']['body']['choices'][0]['message']['content']
        answer = content if content else None
        
        return {
            'answer': answer,
            'finish_reason': result_entry['response']['body']['choices'][0].get('finish_reason'),
            'tokens': result_entry['response']['body'].get('usage', {})
        }
    except (KeyError, IndexError):
        return {
            'answer': None,
            'finish_reason': 'error',
            'tokens': {}
        }


def organize_results_by_category_and_question(results: List[Dict]) -> Dict[str, Dict[str, Dict]]:
    """
    Organize results by category -> question_id -> miu_level.
    Returns: {category: {question_id: {baseline: {}, distortions: {}}}}
    """
    organized = defaultdict(lambda: defaultdict(lambda: {'baseline': None, 'distortions': {}}))
    
    for result in results:
        custom_id = result['custom_id']
        parsed = parse_custom_id(custom_id)
        
        category = parsed['category']
        question_id = parsed['question_id']
        miu_level = parsed['miu_level']
        
        answer_data = get_model_answer(result)
        
        if miu_level == '0.0':
            organized[category][question_id]['baseline'] = answer_data
        else:
            organized[category][question_id]['distortions'][f'miu_{miu_level}'] = answer_data
    
    return organized


def load_ground_truth_for_category(category: str) -> Dict[str, Dict]:
    """Load ground truth data for a specific category."""
    base_path = Path("/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/data/distortion_validation")
    cat_path = base_path / f"category_{category}"
    
    ground_truth = {}
    
    # Load original questions and ground truth
    original_file = cat_path / "original_questions_and_ground_truth.json"
    if original_file.exists():
        original_data = load_json(str(original_file))
        for item in original_data:
            question_id = item['question_id']
            ground_truth[question_id] = {
                'question_id': question_id,
                'original_problem': item['problem'],
                'ground_truth_answer': item['answer'],
                'source': item.get('source', 'N/A'),
                'domain': item.get('domain', []),
                'llama8b_solve_rate': item.get('llama8b_solve_rate')
            }
    
    # Load distorted questions
    distorted_file = cat_path / ("distorted_question.json" if category == "2" else "distorted_questions.json")
    if distorted_file.exists():
        distorted_data = load_json(str(distorted_file))
        for item in distorted_data.get('distortions', []):
            question_id = item['question_id']
            if question_id in ground_truth:
                ground_truth[question_id]['distorted_problems'] = {}
                for miu_key, miu_data in item['distortions'].items():
                    ground_truth[question_id]['distorted_problems'][miu_key] = {
                        'distorted_problem': miu_data['distorted_problem'],
                        'miu': miu_data['miu'],
                        'miu_description': miu_data['miu_description'],
                        'temperature': miu_data.get('temperature')
                    }
    
    return ground_truth


def create_category_results(model_name: str, category: str, 
                           organized_results: Dict[str, Dict],
                           ground_truth: Dict[str, Dict]) -> List[Dict]:
    """Create results structure for a category."""
    category_results = []
    
    for question_id in sorted(organized_results.keys()):
        if question_id not in ground_truth:
            continue
        
        question_data = {
            'question_id': question_id,
            'original_problem': ground_truth[question_id]['original_problem'],
            'ground_truth_answer': ground_truth[question_id]['ground_truth_answer'],
            'source': ground_truth[question_id]['source'],
            'domain': ground_truth[question_id]['domain'],
            'llama8b_solve_rate': ground_truth[question_id].get('llama8b_solve_rate'),
            'model_answers': {
                'baseline': {
                    'problem': ground_truth[question_id]['original_problem'],
                    'miu': 0.0,
                    'answer': organized_results[question_id]['baseline']['answer'] if organized_results[question_id]['baseline'] else None,
                    'metadata': organized_results[question_id]['baseline'] if organized_results[question_id]['baseline'] else {}
                },
                'distortions': {}
            }
        }
        
        # Add distortions
        for miu_key in ['miu_0.2', 'miu_0.5', 'miu_0.7', 'miu_0.9']:
            if miu_key in ground_truth[question_id].get('distorted_problems', {}):
                distortion_info = ground_truth[question_id]['distorted_problems'][miu_key]
                model_answer_data = organized_results[question_id]['distortions'].get(miu_key, {})
                
                question_data['model_answers']['distortions'][miu_key] = {
                    'problem': distortion_info['distorted_problem'],
                    'miu': distortion_info['miu'],
                    'miu_description': distortion_info['miu_description'],
                    'answer': model_answer_data.get('answer'),
                    'metadata': model_answer_data
                }
        
        category_results.append(question_data)
    
    return category_results


def process_model_file(model_file: Path, model_name: str, output_base_path: Path):
    """Process a single model results file and reorganize by category."""
    print(f"\nProcessing {model_name}...")
    
    # Load results
    results = load_jsonl(str(model_file))
    print(f"  Loaded {len(results)} results")
    
    # Organize by category
    organized = organize_results_by_category_and_question(results)
    print(f"  Found {len(organized)} categories")
    
    # Process each category
    for category, questions in organized.items():
        print(f"  Category {category}: {len(questions)} questions")
        
        # Create category directory
        category_path = output_base_path / f"category_{category}"
        category_path.mkdir(parents=True, exist_ok=True)
        
        # Load ground truth for this category
        ground_truth = load_ground_truth_for_category(category)
        
        # Create category results
        category_results = create_category_results(model_name, category, questions, ground_truth)
        
        # Save to category directory
        output_file = category_path / f"{model_name}_results.json"
        save_json(category_results, str(output_file))
        print(f"    ✓ Saved to {output_file}")


def main():
    """Main function to reorganize all model results."""
    
    # Configuration
    results_dir = Path("/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/data/results_verified")
    output_base = Path("/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/data/results_by_category")
    
    # Model files mapping
    model_files = {
        'gpt_4_1': 'gpt-4_1_results_20260105_024527.jsonl',
        'gpt_4': 'gpt-4_results_20260105_024526.jsonl',
        'gpt_5': 'gpt-5_results_20260105_024528.jsonl',
        'gpt_5_mini': 'gpt-5-mini_results_20260105_024524.jsonl',
    }
    
    # Also check for other model files
    print("Scanning for all model result files...")
    for file in results_dir.glob("*.jsonl"):
        if file.stem not in [f.replace('.jsonl', '') for f in model_files.values()]:
            # Extract model name from filename
            model_name = file.stem.replace('_results_20260105_024524', '').replace('_results_20260105_024526', '').replace('_results_20260105_024527', '').replace('_results_20260105_024528', '')
            if model_name and 'retry' not in model_name.lower():
                model_files[model_name] = file.name
    
    print(f"\nFound {len(model_files)} model files to process:")
    for model_name, filename in model_files.items():
        print(f"  - {model_name}: {filename}")
    
    # Create output directory
    output_base.mkdir(parents=True, exist_ok=True)
    
    # Process each model
    for model_name, filename in model_files.items():
        model_file = results_dir / filename
        if model_file.exists():
            process_model_file(model_file, model_name, output_base)
        else:
            print(f"  ⚠ File not found: {model_file}")
    
    print("\n" + "="*60)
    print("REORGANIZATION COMPLETE!")
    print("="*60)
    print(f"New structure created in: {output_base}")
    print("\nStructure:")
    print("  data/results_by_category/")
    print("    category_1/")
    print("      gpt_4_1_results.json")
    print("      gpt_4_results.json")
    print("      gpt_5_results.json")
    print("      gpt_5_mini_results.json")
    print("    category_2/")
    print("      ...")
    print("    category_3/")
    print("      ...")
    print("\nEach model results file contains:")
    print("  - Original problem + ground truth")
    print("  - Baseline (miu 0.0) question + model answer")
    print("  - 4 distorted questions + model answers")
    print("="*60)
    print("\nFILES THAT CAN BE REMOVED AFTER VALIDATION:")
    print("  - data/results_verified/*.jsonl (original model result files)")
    print("  - validation_for_claude_gpt41_batch*.md (temporary validation files)")
    print("  - Any other temporary/intermediate files")
    print("="*60)


if __name__ == "__main__":
    main()

