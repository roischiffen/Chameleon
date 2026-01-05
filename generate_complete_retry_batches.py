#!/usr/bin/env python3
"""
Generate complete retry batches for ALL empty answers (baseline + distorted).

This script creates retry batches for all questions that have empty answers,
ensuring complete coverage across all MIU levels.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

# Paths
DATA_DIR = Path(__file__).parent / "data" / "distortion_validation"
RESULTS_DIR = Path(__file__).parent / "data" / "results_verified"
OUTPUT_DIR = Path(__file__).parent / "data" / "retry_batches_complete"
COMPREHENSIVE_REPORT = Path(__file__).parent / "empty_answers_comprehensive_report.json"

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
    """Load original questions for a category."""
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
    """Load distorted questions for a category."""
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
        if question_id in original_questions:
            return original_questions[question_id].get('problem', '')
    else:
        if question_id in distorted_questions:
            distortions = distorted_questions[question_id].get('distortions', {})
            miu_key = f"miu_{miu}"
            if miu_key in distortions:
                return distortions[miu_key].get('distorted_problem', '')
    
    return ''


def create_batch_request(category: int, question_id: str, miu: float,
                        model: str, question_text: str) -> Dict:
    """Create a batch request."""
    custom_id = f"cat{category}_q_{question_id}_miu_{miu}_retry_3000_complete"
    prompt = create_evaluation_prompt(question_text)
    
    model_id = MODELS.get(model, model)
    
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000,
    }
    
    if "gpt-5" in model:
        body["reasoning_effort"] = "medium"
    
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": body
    }


def main():
    print("="*80)
    print("GENERATING COMPLETE RETRY BATCHES FOR ALL EMPTY ANSWERS")
    print("="*80)
    
    # Load comprehensive report
    if not COMPREHENSIVE_REPORT.exists():
        print(f"\n❌ Error: Comprehensive report not found: {COMPREHENSIVE_REPORT}")
        print("   Please run check_all_empty_answers.py first")
        return
    
    with open(COMPREHENSIVE_REPORT, 'r') as f:
        report = json.load(f)
    
    need_retry = report.get('need_retry', {})
    
    print(f"\n📋 Found {report['summary']['need_retry_total']} empty answers that need retry")
    print(f"   Token limit issues: {report['summary']['need_retry_token_limit']}")
    print(f"   Other issues: {report['summary']['need_retry_other']}")
    
    # Load question data
    print("\n📚 Loading question data...")
    question_data = {}
    for category in [1, 2, 3]:
        question_data[category] = {
            'original': load_original_questions(category),
            'distorted': load_distorted_questions(category)
        }
        print(f"   Category {category}: {len(question_data[category]['original'])} original, "
              f"{len(question_data[category]['distorted'])} distorted")
    
    # Generate batch requests
    print("\n📝 Generating batch requests...")
    batch_requests = defaultdict(list)  # {model: [requests]}
    
    missing_text_count = 0
    
    for model, cats in need_retry.items():
        if model not in MODELS:
            continue
        
        for category_str, qids in cats.items():
            category = int(category_str)
            
            for qid, miu_data in qids.items():
                # Remove "_miu" suffix if present
                clean_qid = qid.replace('_miu', '')
                
                for miu_str, details in miu_data.items():
                    miu = float(miu_str)
                    
                    question_text = get_question_text(
                        category, clean_qid, miu,
                        question_data[category]['original'],
                        question_data[category]['distorted']
                    )
                    
                    if question_text:
                        request = create_batch_request(
                            category, clean_qid, miu, model, question_text
                        )
                        batch_requests[model].append(request)
                    else:
                        missing_text_count += 1
                        print(f"   ⚠️  Missing text for Category {category}, QID {clean_qid}, "
                              f"Model {model}, MIU {miu}")
    
    if missing_text_count > 0:
        print(f"\n   ⚠️  {missing_text_count} combinations missing question text")
    
    # Write batch files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n💾 Writing batch files...")
    for model, requests in batch_requests.items():
        filename = f"{model.replace('-', '_')}_complete_retry_3000tokens.jsonl"
        batch_file = OUTPUT_DIR / filename
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
        
        print(f"   ✅ {batch_file.name}: {len(requests)} requests")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_requests = sum(len(reqs) for reqs in batch_requests.values())
    print(f"\n✅ Generated {total_requests} retry requests")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    
    print("\n📊 Breakdown:")
    for model, requests in batch_requests.items():
        print(f"   {model}: {len(requests)} requests")
    
    print("\n📋 Next steps:")
    print("   1. Review batch files in:", OUTPUT_DIR)
    print("   2. Submit to OpenAI Batch API")
    print("   3. This will ensure complete coverage of all empty answers")
    print("="*80)


if __name__ == "__main__":
    main()

