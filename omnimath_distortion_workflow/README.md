# 🦎 Chameleon - OmniMath Distortion Workflow

## Overview

This workflow generates semantically equivalent paraphrased versions (distortions) of mathematical questions from the OmniMath dataset to test LLM robustness to surface-level linguistic variations.

---

## 📁 Data Structure

```
omnimath_distortion_workflow/
├── data/
│   └── by_difficulty/
│       ├── difficulty_1/                    # Easy questions (100 total)
│       │   ├── difficulty_1_baseline_questions.json   # Original questions only
│       │   ├── difficulty_1_distortions.json          # All distortions (4 per question)
│       │   └── difficulty_1_metadata.json             # Statistics & question IDs
│       │
│       └── difficulty_1.5/                  # Slightly harder questions (100 total)
│           ├── difficulty_1.5_baseline_questions.json
│           ├── difficulty_1.5_distortions.json
│           └── difficulty_1.5_metadata.json
│
├── evaluation/                              # LLM evaluation results
│   └── baseline_results/                    # GPT-4o and GPT-5-mini results
│
├── flows/                                   # Python scripts
│   ├── batch_generator.py                   # Generate distortions
│   ├── migrate_batch.py                     # Move validated batches
│   ├── evaluate_baseline.py                 # Run LLM evaluations
│   └── ...
│
├── modules/                                 # Shared code modules
│   ├── math_distortion_prompts.py           # MIU-level prompts
│   ├── distortion_validator.py              # Validation logic
│   └── ...
│
└── tests/                                   # Unit tests
```

---

## 📊 Data Files Explained

### 1. `*_baseline_questions.json`

**Purpose:** Original questions WITHOUT any distortions. Use this for baseline LLM testing.

**Structure:**
```json
[
  {
    "question_id": 2676,
    "original_question": "If $x+\\sqrt{81}=25$, what is the value of $x$?",
    "correct_answer": "16",
    "difficulty": 1.0,
    "difficulty_category": "easy",
    "domain": "Mathematics -> Algebra -> Prealgebra -> Simple Equations",
    "subject": ["Mathematics -> Algebra -> Prealgebra -> Simple Equations"],
    "source": "omnimath"
  },
  ...
]
```

**Count:** 100 questions per difficulty level

---

### 2. `*_distortions.json`

**Purpose:** All distorted versions of questions. Each question has 4 distortions at different MIU (Meaning-Invariant Utterance) levels.

**Structure:**
```json
[
  {
    "question_id": 2676,
    "original_question": "If $x+\\sqrt{81}=25$...",
    "distorted_question": "Assuming $x+\\sqrt{81}=25$, determine the value of $x$.",
    "correct_answer": "16",
    "miu": 0.2,
    "miu_description": "Synonym Substitution",
    "difficulty": 1.0,
    ...
  },
  ...
]
```

**Count:** 400 distortions per difficulty (100 questions × 4 MIU levels)

---

### 3. `*_metadata.json`

**Purpose:** Statistics and tracking information.

**Structure:**
```json
{
  "difficulty": 1.0,
  "unique_questions": 100,
  "total_distortions": 400,
  "question_ids": [2676, 2678, ...],
  "miu_levels": [0.2, 0.5, 0.7, 0.9],
  "last_updated": "2025-12-10T..."
}
```

---

## 🎯 MIU (Distortion) Levels

| MIU | Name | Description |
|-----|------|-------------|
| **0.2** | Synonym Substitution | Replace verbs/phrases with synonyms |
| **0.5** | Notation Variation | Convert between symbolic and verbal forms |
| **0.7** | Format Conversion | Change to structured bullet-point format |
| **0.9** | Maximum Distortion | Aggressive vocabulary transformation |

---

## 📈 Dataset Statistics

| Difficulty | Questions | Distortions | MIU Levels |
|------------|-----------|-------------|------------|
| 1.0 (Easy) | 100 | 400 | 0.2, 0.5, 0.7, 0.9 |
| 1.5 (Easy+) | 100 | 400 | 0.2, 0.5, 0.7, 0.9 |
| **Total** | **200** | **800** | - |

---

## 🚀 Usage

### Load Baseline Questions
```python
import json

with open('data/by_difficulty/difficulty_1/difficulty_1_baseline_questions.json') as f:
    questions = json.load(f)

for q in questions:
    print(f"Q{q['question_id']}: {q['original_question']}")
    print(f"Answer: {q['correct_answer']}\n")
```

### Load Distortions
```python
with open('data/by_difficulty/difficulty_1/difficulty_1_distortions.json') as f:
    distortions = json.load(f)

# Filter by MIU level
miu_02 = [d for d in distortions if d['miu'] == 0.2]
```

---

## 🔧 Key Scripts

| Script | Purpose |
|--------|---------|
| `batch_generator.py` | Generate new distortions for questions |
| `migrate_batch.py` | Move validated batches to final location |
| `evaluate_baseline.py` | Run LLM evaluations on questions |
| `score_results.py` | Score and analyze evaluation results |

---

## 📝 Notes

- All questions are **text-only** (no visual/diagram requirements)
- Questions are from the **OmniMath** benchmark dataset
- Distortions preserve mathematical meaning and answer
- Higher difficulty (2.0+) questions were excluded due to low LLM accuracy
