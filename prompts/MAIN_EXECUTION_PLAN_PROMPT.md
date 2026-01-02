# Chameleon Research Data Remediation - Main Execution Plan
## For Cursor Agent Composer Model

---

## 🎯 MISSION OBJECTIVE

Execute a comprehensive data remediation plan to bring the Chameleon research project to academic publication standards. This involves re-evaluating failed model responses, fixing data inconsistencies, standardizing file formats, and generating complete documentation.

---

## 📁 PROJECT CONTEXT

### Project Location
```
/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/
```

### What This Research Studies
The **Chameleon** project evaluates AI model resilience to mathematical question distortions. It measures how well models perform when questions are reformulated (changed notation, wording, format) while preserving mathematical meaning.

### Current Data State Issues
1. **Token limit failures**: 222 evaluations produced empty answers due to output token limits
2. **Missing evaluations**: 8 question-MIU pairs were never evaluated
3. **Data integrity issue**: 12 records incorrectly marked as correct despite empty answers
4. **Format inconsistency**: Source distortion files mix two formats
5. **Incomplete documentation**: Missing methodology documentation

---

## 📊 DATA STRUCTURE OVERVIEW

### Source Data
```
data/source/
├── difficulty_1.0/
│   ├── difficulty_1_baseline_questions.json    (100 questions)
│   ├── difficulty_1_distortions.json           (400 distortions, mixed format)
│   └── difficulty_1_metadata.json
└── difficulty_1.5/
    ├── difficulty_1.5_baseline_questions.json  (100 questions)
    ├── difficulty_1.5_distortions.json         (400 distortions, mixed format)
    └── difficulty_1.5_metadata.json
```

### Results Data
```
data/results/
├── baseline/
│   └── {model}_difficulty_{diff}/
│       ├── results.json
│       └── summary.json
└── distortion/
    └── {model}_difficulty_{diff}/
        ├── results.jsonl
        └── summary.json
```

Models: `gpt_4o`, `gpt_5`, `gpt_5_mini`, `mistral_large_latest`
Difficulties: `1_0`, `1_5`

---

## 📋 EXECUTION PHASES

Execute these phases IN ORDER. Each phase depends on the previous.

---

# PHASE 1: Source Data Standardization

## Task 1.1: Flatten Distortion Files

### Objective
Convert all distortion records to flat format (one record per distortion).

### Current State
The distortion files have TWO formats mixed together:

**Format A (Flat)**: Individual distortion records
```json
{
  "question_id": 2690,
  "miu": 0.2,
  "miu_description": "Synonym Substitution",
  "distorted_question": "...",
  "correct_answer": "72",
  ...
}
```

**Format B (Nested)**: Parent record with distortions array
```json
{
  "question_id": 2676,
  "original_question": "...",
  "correct_answer": "16",
  "distortions": [
    {"miu": 0.2, "miu_description": "...", "distorted_question": "..."},
    {"miu": 0.5, "miu_description": "...", "distorted_question": "..."},
    {"miu": 0.7, "miu_description": "...", "distorted_question": "..."},
    {"miu": 0.9, "miu_description": "...", "distorted_question": "..."}
  ]
}
```

### Target State
ALL records in flat format:
```json
[
  {"question_id": 2676, "miu": 0.2, "distorted_question": "...", "correct_answer": "16", ...},
  {"question_id": 2676, "miu": 0.5, "distorted_question": "...", "correct_answer": "16", ...},
  ...
]
```

### Implementation

```python
import json
from datetime import datetime

def flatten_distortions(input_path, output_path):
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    flattened = []
    
    for record in data:
        if 'distortions' in record and isinstance(record['distortions'], list):
            # Nested format - expand
            base_fields = {k: v for k, v in record.items() if k != 'distortions'}
            for dist in record['distortions']:
                flat_record = {**base_fields, **dist}
                flattened.append(flat_record)
        else:
            # Already flat format
            flattened.append(record)
    
    # Sort by question_id and miu for consistency
    flattened.sort(key=lambda x: (x.get('question_id', 0), x.get('miu', 0)))
    
    with open(output_path, 'w') as f:
        json.dump(flattened, f, indent=2)
    
    return len(flattened)

# Execute for both difficulties
for diff in ['1.0', '1.5']:
    prefix = 'difficulty_1' if diff == '1.0' else 'difficulty_1.5'
    input_path = f'data/source/difficulty_{diff}/{prefix}_distortions.json'
    
    # Backup original
    backup_path = f'data/source/difficulty_{diff}/{prefix}_distortions.backup.json'
    # ... copy to backup ...
    
    count = flatten_distortions(input_path, input_path)
    print(f'Flattened {diff}: {count} records')
```

### Validation
- Difficulty 1.0: Must have exactly 400 records
- Difficulty 1.5: Must have exactly 400 records
- Each record must have: question_id, miu, distorted_question, correct_answer

---

# PHASE 2: Re-evaluation Preparation

## Task 2.1: Extract Records Requiring Re-evaluation

### Records to Re-evaluate

| Category | Source | Count | Details |
|----------|--------|-------|---------|
| GPT-5 token failures (distortion) | gpt_5_difficulty_1_5 | 10 | Empty answers hitting 1200 token limit |
| GPT-5 token failures (baseline) | gpt_5_difficulty_1_5 | 3 | Empty answers hitting 1200 token limit |
| GPT-5-mini token failures (distortion 1.0) | gpt_5_mini_difficulty_1_0 | 70 | Empty answers hitting 150 token limit |
| GPT-5-mini token failures (distortion 1.5) | gpt_5_mini_difficulty_1_5 | 139 | Empty answers hitting 150 token limit |
| GPT-5-mini token failures (baseline) | gpt_5_mini_difficulty_1_5 | 1 | Empty answers |
| GPT-5 missing records | gpt_5_difficulty_1_5 | 2 | Q2834@0.7, Q3070@0.7 |
| GPT-5-mini missing records (1.0) | gpt_5_mini_difficulty_1_0 | 3 | Q2850@0.5, Q2870@0.5, Q3167@0.5 |
| GPT-5-mini missing records (1.5) | gpt_5_mini_difficulty_1_5 | 3 | Q2706@0.5, Q2938@0.5, Q3132@0.9 |
| Corrected empty (included in above) | gpt_5_mini | 12 | match_type="corrected_empty_answer" |

**Total unique re-evaluations needed: ~230**

### Implementation

Create extraction script: `scripts/extract_reevaluation_targets.py`

```python
import json
from pathlib import Path

def extract_reeval_targets():
    targets = {
        'gpt_5': {'baseline': [], 'distortion': []},
        'gpt_5_mini': {'baseline': [], 'distortion': []}
    }
    
    # GPT-5 distortion empty answers
    with open('data/results/distortion/gpt_5_difficulty_1_5/results.jsonl') as f:
        for line in f:
            r = json.loads(line)
            if r.get('model_answer', '') == '':
                targets['gpt_5']['distortion'].append({
                    'question_id': r['question_id'],
                    'miu': r['miu'],
                    'source': 'empty_answer'
                })
    
    # GPT-5 baseline empty answers
    with open('data/results/baseline/gpt_5_difficulty_1_5/results.json') as f:
        data = json.load(f)
        for r in (data if isinstance(data, list) else data.get('results', [])):
            if r.get('model_answer', '') == '':
                targets['gpt_5']['baseline'].append({
                    'question_id': r['question_id'],
                    'source': 'empty_answer'
                })
    
    # GPT-5-mini distortion empty answers (both difficulties)
    for diff in ['1_0', '1_5']:
        with open(f'data/results/distortion/gpt_5_mini_difficulty_{diff}/results.jsonl') as f:
            for line in f:
                r = json.loads(line)
                if r.get('model_answer', '') == '':
                    targets['gpt_5_mini']['distortion'].append({
                        'question_id': r['question_id'],
                        'miu': r['miu'],
                        'difficulty': diff,
                        'source': 'empty_answer'
                    })
    
    # GPT-5-mini baseline empty answers
    with open('data/results/baseline/gpt_5_mini_difficulty_1_5/results.json') as f:
        data = json.load(f)
        for r in (data if isinstance(data, list) else data.get('results', [])):
            if r.get('model_answer', '') == '':
                targets['gpt_5_mini']['baseline'].append({
                    'question_id': r['question_id'],
                    'source': 'empty_answer'
                })
    
    # Add missing records
    targets['gpt_5']['distortion'].extend([
        {'question_id': 2834, 'miu': 0.7, 'source': 'missing'},
        {'question_id': 3070, 'miu': 0.7, 'source': 'missing'}
    ])
    
    targets['gpt_5_mini']['distortion'].extend([
        {'question_id': 2850, 'miu': 0.5, 'difficulty': '1_0', 'source': 'missing'},
        {'question_id': 2870, 'miu': 0.5, 'difficulty': '1_0', 'source': 'missing'},
        {'question_id': 3167, 'miu': 0.5, 'difficulty': '1_0', 'source': 'missing'},
        {'question_id': 2706, 'miu': 0.5, 'difficulty': '1_5', 'source': 'missing'},
        {'question_id': 2938, 'miu': 0.5, 'difficulty': '1_5', 'source': 'missing'},
        {'question_id': 3132, 'miu': 0.9, 'difficulty': '1_5', 'source': 'missing'}
    ])
    
    # Save targets
    Path('data/reevaluation').mkdir(exist_ok=True)
    with open('data/reevaluation/targets.json', 'w') as f:
        json.dump(targets, f, indent=2)
    
    # Print summary
    print(f"GPT-5 baseline: {len(targets['gpt_5']['baseline'])}")
    print(f"GPT-5 distortion: {len(targets['gpt_5']['distortion'])}")
    print(f"GPT-5-mini baseline: {len(targets['gpt_5_mini']['baseline'])}")
    print(f"GPT-5-mini distortion: {len(targets['gpt_5_mini']['distortion'])}")

if __name__ == '__main__':
    extract_reeval_targets()
```

---

## Task 2.2: Prepare Re-evaluation Questions

For each target, extract the question text from source files.

### For Baseline Re-evaluations
Get question from: `data/source/difficulty_{diff}/{prefix}_baseline_questions.json`

### For Distortion Re-evaluations
Get distorted question from: `data/source/difficulty_{diff}/{prefix}_distortions.json`

### Output Format
Create: `data/reevaluation/questions_to_evaluate.json`

```json
{
  "gpt_5": {
    "baseline": [
      {
        "question_id": 2754,
        "difficulty": "1.5",
        "question": "If x + √81 = 25, what is the value of x?",
        "correct_answer": "16"
      }
    ],
    "distortion": [
      {
        "question_id": 2834,
        "miu": 0.7,
        "difficulty": "1.5",
        "distorted_question": "...",
        "correct_answer": "..."
      }
    ]
  },
  "gpt_5_mini": {
    ...
  }
}
```

---

# PHASE 3: API Re-evaluation

## Task 3.1: Re-evaluate with Higher Token Limit

### Configuration

```python
REEVAL_CONFIG = {
    'gpt_5': {
        'model': 'gpt-5',  # Or actual model name
        'max_tokens': 1200,  # Keep same limit
        'temperature': 0  # Deterministic
    },
    'gpt_5_mini': {
        'model': 'gpt-5-mini',  # Or actual model name  
        'max_tokens': 1200,  # INCREASED from 150
        'temperature': 0
    }
}
```

### Evaluation Prompt Template
Use the same prompt template as original evaluations. Check existing evaluation code in:
- `src/flows/evaluate_baseline.py`
- `src/flows/evaluate_distortions.py`
- `src/modules/evaluation_prompt.py`

### Output Storage
Save re-evaluation results to:
- `data/reevaluation/results/gpt_5_baseline.json`
- `data/reevaluation/results/gpt_5_distortion.jsonl`
- `data/reevaluation/results/gpt_5_mini_baseline.json`
- `data/reevaluation/results/gpt_5_mini_distortion.jsonl`

---

## Task 3.2: Answer Comparison

Apply the same answer comparison logic used in original evaluation.

Check: `src/modules/answer_comparator.py`

For each re-evaluated answer:
1. Compare with ground truth
2. Assign match_type
3. Determine is_correct

---

# PHASE 4: Result Integration

## Task 4.1: Merge Re-evaluation Results

### For Baseline Results
Update the existing results.json files:
1. Load original results
2. For each re-evaluated record, find by question_id and replace
3. Save updated results

### For Distortion Results
Update the existing results.jsonl files:
1. Load all records
2. For each re-evaluated record, find by (question_id, miu) and replace
3. For missing records, append new records
4. Save updated results

### Implementation

```python
def merge_baseline_results(original_path, reeval_path, output_path):
    with open(original_path) as f:
        original = json.load(f)
    with open(reeval_path) as f:
        reeval = json.load(f)
    
    records = original if isinstance(original, list) else original.get('results', [])
    reeval_by_qid = {r['question_id']: r for r in reeval}
    
    updated = []
    for r in records:
        qid = r['question_id']
        if qid in reeval_by_qid:
            # Merge: keep original fields, update with new evaluation
            merged = {**r, **reeval_by_qid[qid]}
            merged['reevaluated'] = True
            merged['reevaluation_reason'] = 'token_limit_failure'
            updated.append(merged)
        else:
            updated.append(r)
    
    with open(output_path, 'w') as f:
        json.dump(updated, f, indent=2)

def merge_distortion_results(original_path, reeval_path, output_path):
    with open(original_path) as f:
        original = [json.loads(l) for l in f if l.strip()]
    with open(reeval_path) as f:
        reeval = [json.loads(l) for l in f if l.strip()]
    
    reeval_by_key = {(r['question_id'], r['miu']): r for r in reeval}
    original_keys = set((r['question_id'], r['miu']) for r in original)
    
    updated = []
    for r in original:
        key = (r['question_id'], r['miu'])
        if key in reeval_by_key:
            merged = {**r, **reeval_by_key[key]}
            merged['reevaluated'] = True
            updated.append(merged)
        else:
            updated.append(r)
    
    # Add any new records (missing evaluations)
    for key, r in reeval_by_key.items():
        if key not in original_keys:
            r['reevaluated'] = True
            r['reevaluation_reason'] = 'missing_evaluation'
            updated.append(r)
    
    # Sort by question_id and miu
    updated.sort(key=lambda x: (x['question_id'], x['miu']))
    
    with open(output_path, 'w') as f:
        for r in updated:
            f.write(json.dumps(r) + '\n')
```

---

## Task 4.2: Regenerate Summary Statistics

After merging, regenerate all summary.json files:

```python
def regenerate_summary(results_path, summary_path, is_distortion=False):
    if is_distortion:
        with open(results_path) as f:
            records = [json.loads(l) for l in f if l.strip()]
    else:
        with open(results_path) as f:
            data = json.load(f)
            records = data if isinstance(data, list) else data.get('results', [])
    
    total = len(records)
    correct = sum(1 for r in records if r.get('is_correct', False))
    empty = sum(1 for r in records if r.get('model_answer', '') == '')
    
    summary = {
        'total_questions': total,
        'correct': correct,
        'incorrect': total - correct,
        'accuracy': round((correct / total) * 100, 2) if total > 0 else 0,
        'empty_answers': empty,
        'reevaluated_count': sum(1 for r in records if r.get('reevaluated', False)),
        'verified_at': datetime.now().isoformat()
    }
    
    if is_distortion:
        # Add by_miu breakdown
        by_miu = {}
        for r in records:
            miu = str(r.get('miu'))
            if miu not in by_miu:
                by_miu[miu] = {'correct': 0, 'total': 0, 'empty': 0}
            by_miu[miu]['total'] += 1
            if r.get('is_correct', False):
                by_miu[miu]['correct'] += 1
            if r.get('model_answer', '') == '':
                by_miu[miu]['empty'] += 1
        
        for miu in by_miu:
            by_miu[miu]['accuracy'] = round(
                (by_miu[miu]['correct'] / by_miu[miu]['total']) * 100, 2
            )
        
        summary['by_miu'] = by_miu
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
```

---

# PHASE 5: Documentation Generation

## Task 5.1: Methodology Documentation

Create: `docs/METHODOLOGY.md`

Include:
1. **Data Collection**
   - Source of questions (OmniMath dataset)
   - Question selection criteria
   - Difficulty level definitions

2. **Distortion Generation**
   - MIU levels (0.2, 0.5, 0.7, 0.9) and their meanings
   - Distortion generation process

3. **Evaluation Procedure**
   - Models evaluated and versions
   - API parameters used
   - Token limits: Original (150 for mini, 1200 for others) → Remediated (1200 for all)
   - Answer comparison methodology

4. **Data Remediation**
   - Token limit failures identified and re-evaluated
   - Missing evaluations completed
   - Data integrity issues fixed

---

## Task 5.2: Data Quality Report

Create: `docs/DATA_QUALITY_REPORT.md`

Include:
1. **Completeness Metrics**
   - Baseline: 100% (800/800)
   - Distortion: After remediation (3200/3200)

2. **Accuracy Calculation Methodology**
   - Empty answers counted as incorrect
   - Adjusted accuracy available excluding token failures

3. **Known Limitations**
   - Any remaining data issues
   - Scope of validation performed

---

## Task 5.3: Adjusted Metrics Report

Create: `output/reports/ADJUSTED_METRICS.md`

For each model/difficulty combination, report:
- **Reported Accuracy**: Standard calculation
- **Adjusted Accuracy**: Excluding token limit failures
- **Confidence Interval**: If applicable

---

## Task 5.4: Question-Level Analysis Export

Create: `output/exports/question_analysis.csv`

Columns:
- question_id
- difficulty
- domain
- baseline_correct (per model)
- distortion_correct_rate (per model, per MIU)
- failure_reason (if any)

---

# PHASE 6: Validation and Finalization

## Task 6.1: Full Data Validation

Run comprehensive validation:

```python
def validate_all():
    errors = []
    
    # Check source data
    for diff in ['1.0', '1.5']:
        # Verify 400 distortions
        # Verify 100 baseline questions
        # Verify all question_ids match
        pass
    
    # Check result data
    for model in ['gpt_4o', 'gpt_5', 'gpt_5_mini', 'mistral_large_latest']:
        for diff in ['1_0', '1_5']:
            # Verify record counts
            # Verify summary matches records
            # Verify no empty answers (after remediation)
            pass
    
    return errors
```

## Task 6.2: Generate Final Integrity Report

Update: `DATA_INTEGRITY_ANALYSIS_REPORT.md`

Mark all issues as RESOLVED with timestamps and details.

---

# EXECUTION CHECKLIST

- [ ] **Phase 1**: Source Data Standardization
  - [ ] 1.1: Flatten distortion files
  - [ ] Validate: 400 records per difficulty

- [ ] **Phase 2**: Re-evaluation Preparation
  - [ ] 2.1: Extract 230 re-evaluation targets
  - [ ] 2.2: Prepare question files

- [ ] **Phase 3**: API Re-evaluation
  - [ ] 3.1: Re-evaluate all targets with 1200 token limit
  - [ ] 3.2: Compare answers and assign correctness

- [ ] **Phase 4**: Result Integration
  - [ ] 4.1: Merge re-evaluation results
  - [ ] 4.2: Regenerate all summaries

- [ ] **Phase 5**: Documentation
  - [ ] 5.1: Create METHODOLOGY.md
  - [ ] 5.2: Create DATA_QUALITY_REPORT.md
  - [ ] 5.3: Create ADJUSTED_METRICS.md
  - [ ] 5.4: Export question analysis

- [ ] **Phase 6**: Validation
  - [ ] 6.1: Run full validation
  - [ ] 6.2: Update integrity report

---

## ⚠️ IMPORTANT NOTES

1. **Backup First**: Before modifying any file, create a backup in a `backups/` directory with timestamp

2. **API Costs**: Re-evaluating ~230 questions will incur API costs. Estimate:
   - GPT-5: ~13 calls
   - GPT-5-mini: ~217 calls

3. **Separate from Validation Task**: The answer validation task (reviewing 871 no_match cases) is handled by a SEPARATE agent. Do not include that in this execution.

4. **Order Matters**: Execute phases in order. Phase 4 depends on Phase 3 results.

5. **Token Limit**: Use 1200 max_tokens for ALL re-evaluations (both GPT-5 and GPT-5-mini)

---

**BEGIN EXECUTION**

