# Evaluation Results Summary

**Last Updated:** December 12, 2025  
**String Matching Corrections Applied:** Yes

---

## Folder Structure

All results are organized by `{model}_difficulty_{level}/` with consistent file naming:

```
evaluation/
├── baseline_results/
│   ├── gpt_4o_difficulty_1_0/
│   │   ├── results.json
│   │   └── summary.json
│   ├── gpt_4o_difficulty_1_5/
│   │   ├── results.json
│   │   └── summary.json
│   ├── gpt_5_difficulty_1_5/
│   │   ├── results.json
│   │   └── summary.json
│   ├── gpt_5_mini_difficulty_1_0/
│   │   ├── results.json
│   │   └── summary.json
│   └── gpt_5_mini_difficulty_1_5/
│       ├── results.json
│       └── summary.json
│
└── distortion_results/
    ├── gemini_2_5_flash_difficulty_1_0/   (partial - 5 questions only)
    ├── gpt_4o_difficulty_1_0/
    ├── gpt_4o_difficulty_1_5/             (FAILED - token limit exceeded)
    ├── gpt_5_difficulty_1_0/
    ├── gpt_5_difficulty_1_5/
    ├── gpt_5_mini_difficulty_1_0/
    ├── gpt_5_mini_difficulty_1_5/
    ├── mistral_large_latest_difficulty_1_0/
    ├── mistral_large_latest_difficulty_1_5/
    └── mistral_large_latest_all_difficulties/  (prepared, not submitted)
```

---

## Baseline Results (Original Questions)

| Model | Difficulty | Questions | Correct | Accuracy |
|-------|------------|-----------|---------|----------|
| GPT-5 | 1.5 | 100 | 90 | **90.0%** |
| GPT-5-mini | 1.0 | 100 | 89 | **89.0%** |
| GPT-5-mini | 1.5 | 100 | 67 | **67.0%** |
| GPT-4o | 1.0 | 100 | 73 | **73.0%** |
| GPT-4o | 1.5 | 100 | 57 | **57.0%** |

> **Note:** GPT-5 difficulty 1.0 baseline is embedded in distortion results (miu=0.0 entries)

---

## Distortion Results (MIU Levels: 0.2, 0.5, 0.7, 0.9)

| Model | Difficulty | Questions | Correct | Accuracy | Status |
|-------|------------|-----------|---------|----------|--------|
| GPT-5 | 1.5 | 398 | 346 | **86.9%** | ✅ Complete |
| GPT-5 | 1.0 | 400 | 341 | **85.3%** | ✅ Complete |
| GPT-5-mini | 1.0 | 397 | 307 | **77.3%** | ✅ Complete |
| GPT-5-mini | 1.5 | 397 | 224 | **56.4%** | ✅ Complete |
| GPT-4o | 1.0 | 400 | 267 | **66.8%** | ✅ Complete |
| GPT-4o | 1.5 | - | - | - | ❌ Failed (token limit) |
| Mistral-Large | 1.0 | 400 | 244 | **61.0%** | ✅ Complete |
| Mistral-Large | 1.5 | 400 | 146 | **36.5%** | ✅ Complete |
| Gemini-2.5-Flash | 1.0 | 26 | 22 | 84.6% | ⚠️ Partial (4 API errors) |

---

## Accuracy by MIU Level (Distorted Questions)

### GPT-5 (Difficulty 1.0)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 87.0% |
| 0.5 | 84.0% |
| 0.7 | 86.0% |
| 0.9 | 84.0% |

### GPT-5 (Difficulty 1.5)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 89.0% |
| 0.5 | 88.0% |
| 0.7 | 86.7% |
| 0.9 | 84.0% |

### GPT-5-mini (Difficulty 1.0)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 78.0% |
| 0.5 | 76.3% |
| 0.7 | 81.0% |
| 0.9 | 74.0% |

### GPT-5-mini (Difficulty 1.5)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 60.0% |
| 0.5 | 56.1% |
| 0.7 | 58.0% |
| 0.9 | 51.5% |

### GPT-4o (Difficulty 1.0)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 69.0% |
| 0.5 | 61.0% |
| 0.7 | 72.0% |
| 0.9 | 65.0% |

### Mistral-Large (Difficulty 1.0)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 65.0% |
| 0.5 | 58.0% |
| 0.7 | 60.0% |
| 0.9 | 61.0% |

### Mistral-Large (Difficulty 1.5)
| MIU | Accuracy |
|-----|----------|
| 0.2 | 42.0% |
| 0.5 | 37.0% |
| 0.7 | 38.0% |
| 0.9 | 29.0% |

---

## File Contents

### Each folder contains:

**Baseline Results:**
- `results.json` - Full evaluation results with all question details
- `summary.json` - Statistics summary

**Distortion Results:**
- `results.jsonl` - Full evaluation results (JSONL format)
- `summary.json` - Statistics summary with by-MIU breakdown
- `batch_requests.jsonl` - Original API batch requests (optional)
- `checkpoint.json` - Processing checkpoint/status (optional)

---

## String Matching Corrections Applied

All files have been corrected for false negatives due to string matching issues:

- **Units:** `20 km` → `20` (correct)
- **LaTeX:** `18\%` → `18%` (correct)
- **Fractions:** `\frac{4}{3}` → `4/3` (correct)
- **Currency:** `$30` → `30` (correct)
- **Spacing:** `y = 3x - 1` → `y=3x-1` (correct)
- **Variable names:** `2x+1` → `2t+1` (mathematically equivalent)

Total corrections applied: **209 entries** across all files.

---

## Missing/Incomplete Data

| Model | Difficulty | Status | Notes |
|-------|------------|--------|-------|
| GPT-5 | 1.0 | ❌ Missing Baseline | Use miu=0.0 from distortion results |
| GPT-4o | 1.5 | ❌ Failed | Token limit exceeded during batch |
| Gemini-2.5-Flash | 1.0 | ⚠️ Partial | Only 5 questions processed |
| Gemini-2.5-Flash | 1.5 | ❌ Missing | Not yet processed |
| Mistral-Large | All | ⚠️ Prepared | `mistral_large_latest_all_difficulties/` not submitted |

