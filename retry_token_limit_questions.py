#!/usr/bin/env python3
"""
Retry questions that hit token limits with increased token limit (3000).

This script:
1. Loads the token pattern analysis to identify failed questions
2. Loads original and distorted questions
3. Creates batch requests for only the failed MIU levels
4. Uses max_completion_tokens=3000 instead of 1500
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Paths
DATA_DIR = Path(__file__).parent / "data" / "distortion_validation"
RESULTS_DIR = Path(__file__).parent / "data" / "results_verified"
ANALYSIS_FILE = Path(__file__).parent / "question_token_pattern_analysis.json"
OUTPUT_DIR = Path(__file__).parent / "data" / "retry_batches"

MODELS = {
    "gpt-5": "gpt-5-2025-08-07",
    "gpt-5-mini": "gpt-5-mini-2025-08-07",
}

EVALUATION_PROMPT_TEMPLATE = """You are an expert mathematician solving competition-level math problems.

Task: Solve the following problem and provide ONLY the final answer.

Format requirements:
- Give only the numerical answer (or exact mathematical expression if needed)
- No explanations, no work shown, no units unless asked
- For fractions, use the form a/b
- For "yes/no" questions, answer exactly "Yes" or "No"

Problem:
{question}

Final Answer:"""


def create_evaluation_prompt(question: str) -> str:
    """Create evaluation prompt."""
    return EVALUATION_PROMPT_TEMPLATE.format(question=question)


def load_original_questions(category: int) -> Dict[str, Dict]:
    """Load original questions for a category, indexed by question_id."""
    cat_dir = DATA_DIR / f"category_{category}"
    orig_file = cat_dir / "original_questions_and_ground_truth.json"
    
    with open(orig_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return {q.get('question_id'): q for q in data if q.get('question_id')}
    elif isinstance(data, dict) and 'questions' in data:
        return {q.get('question_id'): q for q in data['questions'] if q.get('question_id')}
    else:
        return {}


def load_distorted_questions(category: int) -> Dict[str, Dict]:
    """Load distorted questions for a category, indexed by question_id."""
    cat_dir = DATA_DIR / f"category_{category}"
    
    dist_file = cat_dir / "distorted_questions.json"
    if not dist_file.exists():
        dist_file = cat_dir / "distorted_question.json"
    
    with open(dist_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    distortions_dict = {}
    if isinstance(data, dict) and 'distortions' in data:
        for entry in data['distortions']:
            qid = entry.get('question_id')
            if qid:
                distortions_dict[qid] = entry
    
    return distortions_dict


def get_question_text(category: int, question_id: str, miu: float, 
                     original_questions: Dict, distorted_questions: Dict) -> str:
    """Get the question text for a given MIU level."""
    if miu == 0.0:
        # Baseline - use original question
        if question_id in original_questions:
            return original_questions[question_id].get('problem', '')
    else:
        # Distorted - get from distortions
        if question_id in distorted_questions:
            distortions = distorted_questions[question_id].get('distortions', {})
            miu_key = f"miu_{miu}"
            if miu_key in distortions:
                return distortions[miu_key].get('distorted_problem', '')
    
    return ''


def create_batch_request(category: int, question_id: str, miu: float, 
                        model: str, question_text: str) -> Dict:
    """Create a batch request for OpenAI Batch API."""
    custom_id = f"cat{category}_q_{question_id}_miu_{miu}_retry_3000"
    prompt = create_evaluation_prompt(question_text)
    
    # Determine model ID
    model_id = MODELS.get(model, model)
    
    # For reasoning models, use reasoning_effort
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000,  # Increased from 1500
    }
    
    # Add reasoning effort for reasoning models (matching original batches)
    if "gpt-5" in model:
        body["reasoning_effort"] = "medium"
    
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": body
    }


def load_failed_questions() -> List[Dict]:
    """Load failed questions from analysis file."""
    with open(ANALYSIS_FILE, 'r') as f:
        analysis = json.load(f)
    
    failed_requests = []
    
    # Process all categories
    for category in [1, 2, 3]:
        # Load data
        original_questions = load_original_questions(category)
        distorted_questions = load_distorted_questions(category)
        
        # Check all questions in analysis
        all_questions = (
            analysis.get('only_baseline_affected', []) +
            analysis.get('multiple_miu_affected', []) +
            analysis.get('all_miu_affected', [])
        )
        
        for q_data in all_questions:
            if q_data.get('category') != category:
                continue
            
            question_id = q_data.get('question_id')
            affected_models = q_data.get('affected_models', {})
            
            for model, model_data in affected_models.items():
                # Determine which MIU levels failed
                if isinstance(model_data, list):
                    # All MIU levels affected
                    affected_miu_levels = model_data
                elif isinstance(model_data, dict):
                    # Specific MIU levels affected
                    affected_miu_levels = model_data.get('affected_levels', [])
                else:
                    continue
                
                # Create requests for each failed MIU level
                for miu in affected_miu_levels:
                    question_text = get_question_text(
                        category, question_id, miu,
                        original_questions, distorted_questions
                    )
                    
                    if question_text:
                        request = create_batch_request(
                            category, question_id, miu, model, question_text
                        )
                        failed_requests.append({
                            'category': category,
                            'question_id': question_id,
                            'miu': miu,
                            'model': model,
                            'request': request
                        })
    
    return failed_requests


def prepare_batch_files(failed_requests: List[Dict]) -> Dict[str, Path]:
    """Prepare batch files organized by model."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Group by model
    by_model = defaultdict(list)
    for req_data in failed_requests:
        model = req_data['model']
        by_model[model].append(req_data['request'])
    
    batch_files = {}
    
    for model, requests in by_model.items():
        # Create filename
        filename = f"{model.replace('-', '_')}_retry_3000tokens.jsonl"
        batch_file = OUTPUT_DIR / filename
        
        # Write requests
        with open(batch_file, 'w', encoding='utf-8') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
        
        batch_files[model] = batch_file
        print(f"  ✅ Created {batch_file.name}: {len(requests)} requests")
    
    return batch_files


def main():
    print("="*80)
    print("PREPARING RETRY BATCHES FOR TOKEN LIMIT FAILURES")
    print("="*80)
    
    print("\n📋 Loading failed questions from analysis...")
    failed_requests = load_failed_questions()
    
    print(f"   Found {len(failed_requests)} failed question/MIU/model combinations")
    
    # Summary by model
    by_model = defaultdict(int)
    by_category = defaultdict(int)
    by_miu = defaultdict(int)
    
    for req_data in failed_requests:
        by_model[req_data['model']] += 1
        by_category[req_data['category']] += 1
        by_miu[req_data['miu']] += 1
    
    print("\n📊 Breakdown:")
    print("   By Model:")
    for model, count in sorted(by_model.items()):
        print(f"     {model}: {count}")
    
    print("   By Category:")
    for cat, count in sorted(by_category.items()):
        print(f"     Category {cat}: {count}")
    
    print("   By MIU Level:")
    for miu, count in sorted(by_miu.items()):
        print(f"     MIU {miu}: {count}")
    
    print("\n📝 Creating batch files...")
    batch_files = prepare_batch_files(failed_requests)
    
    print("\n✅ Batch files created successfully!")
    print("\n📁 Output directory:", OUTPUT_DIR)
    print("\n📋 Next steps:")
    print("   1. Review the batch files in:", OUTPUT_DIR)
    print("   2. Upload to OpenAI Batch API using:")
    print("      openai.File.create(file=open('batch_file.jsonl', 'rb'), purpose='batch')")
    print("   3. Create batch job with:")
    print("      openai.Batch.create(input_file_id=file_id, ...)")
    print("="*80)


if __name__ == "__main__":
    main()

