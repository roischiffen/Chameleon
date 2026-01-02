# Answer Validation Task Prompt
## For Cursor Agent Composer Model

---

## 🎯 TASK OBJECTIVE

You are tasked with validating **871 answer comparisons** from a mathematical reasoning evaluation study. The automated answer matching system marked these as "incorrect" (`no_match`), but some may be **false negatives** - answers that are mathematically equivalent but formatted differently.

Your job is to categorize each case into one of three categories:
- **TRUE_WRONG**: The model's answer is genuinely incorrect
- **FALSE_NEGATIVE**: The model's answer is correct but was missed by automated matching
- **AMBIGUOUS**: Cannot determine correctness without seeing the original question

---

## 📁 PROJECT CONTEXT

### Project Location
```
/Users/schiffen/RESEARCH-PROJECT-REPO/Chameleon/
```

### What This Research Studies
This is the **Chameleon** project studying how well AI models handle "distorted" math questions - questions reformulated in different ways while preserving the same mathematical content.

### Data Structure
- **4 Models Evaluated**: GPT-4o, GPT-5, GPT-5-mini, Mistral Large
- **2 Difficulty Levels**: 1.0 (easier) and 1.5 (harder)
- **Question Types**: Mathematical reasoning (algebra, calculus, geometry, etc.)
- **Answer Format**: Usually numeric, fractions, expressions, or short text

---

## 📊 INPUT DATA LOCATIONS

### Baseline Results (JSON format)
```
data/results/baseline/{model}_difficulty_{diff}/results.json
```
Models: `gpt_4o`, `gpt_5`, `gpt_5_mini`, `mistral_large_latest`
Difficulties: `1_0`, `1_5`

### Distortion Results (JSONL format)
```
data/results/distortion/{model}_difficulty_{diff}/results.jsonl
```

### Record Structure
Each record contains:
```json
{
  "question_id": 2676,
  "miu": 0.5,
  "ground_truth": "16",
  "model_answer": "16.0",
  "is_correct": false,
  "match_type": "no_match",
  "domain": "Mathematics -> Algebra -> ..."
}
```

---

## 🔍 RECORDS TO VALIDATE

You must process ALL records where `match_type == "no_match"` AND `model_answer` is not empty.

### Expected Counts by Source
| Model | Difficulty | Baseline no_match | Distortion no_match |
|-------|------------|-------------------|---------------------|
| gpt_4o | 1.0 | 23 | 99 |
| gpt_4o | 1.5 | 43 | 185 |
| gpt_5 | 1.0 | 3 | 17 |
| gpt_5 | 1.5 | 10 | 47 |
| gpt_5_mini | 1.0 | 3 | 65 |
| gpt_5_mini | 1.5 | 11 | 141 |
| mistral_large_latest | 1.0 | 29 | 129 |
| mistral_large_latest | 1.5 | 51 | 226 |

**Total: ~871 cases** (excluding empty model_answer)

---

## 📋 VALIDATION CATEGORIES

### Category 1: TRUE_WRONG
The model's answer is definitively incorrect.

**Examples:**
| Ground Truth | Model Answer | Why TRUE_WRONG |
|--------------|--------------|----------------|
| `14` | `46` | Different numeric value |
| `-5` | `-9` | Different numeric value |
| `x^2 + 1` | `x^2 - 1` | Different mathematical expression |
| `Monday` | `Tuesday` | Different day |

### Category 2: FALSE_NEGATIVE
The model's answer is mathematically/semantically equivalent to the ground truth.

**Examples:**
| Ground Truth | Model Answer | Why FALSE_NEGATIVE |
|--------------|--------------|---------------------|
| `\frac{4}{3}` | `4/3` | Same fraction, different notation |
| `0.5` | `1/2` | Decimal = fraction equivalent |
| `x+y` | `x + y` | Same expression, spacing difference |
| `\frac{4}{3}` | `\(\frac{4}{3}\)` | Same LaTeX, extra delimiters |
| `25` | `25.0` | Integer = float equivalent |
| `2x + 1` | `1 + 2x` | Same expression, different order |
| `{1, 2, 3}` | `{3, 2, 1}` | Same set, different order |
| `π` | `pi` | Same constant, different notation |
| `√2` | `sqrt(2)` | Same expression, different notation |

### Category 3: AMBIGUOUS
Cannot determine without the original question context.

**Examples:**
| Ground Truth | Model Answer | Why AMBIGUOUS |
|--------------|--------------|---------------|
| `x > 2` | `3, 4, 5, 6` | Could be equivalent if question asks for specific values |
| `2t + 1` | `2x + 1` | Variable renaming - depends on question context |
| `42` | `42 units` | Depends if units were required |

---

## 🛠️ IMPLEMENTATION REQUIREMENTS

### Step 1: Extract All no_match Records

Create a script that:
1. Reads all baseline and distortion result files
2. Filters for `match_type == "no_match"` AND non-empty `model_answer`
3. Outputs to a working file for validation

### Step 2: Validate Each Record

For each record, determine the category based on:
1. **Numeric equivalence**: `0.5 == 1/2 == 0.500`
2. **Expression equivalence**: `x+y == y+x == x + y`
3. **Notation equivalence**: `\frac{a}{b} == a/b`
4. **LaTeX normalization**: Remove `\(`, `\)`, `$`, extra spaces
5. **Set equivalence**: Order doesn't matter for sets
6. **Unit handling**: Numbers with/without units

### Step 3: Generate Output

Create a validation results file with this structure:

**Output File**: `data/validation/answer_validation_results.json`

```json
{
  "validation_metadata": {
    "total_validated": 871,
    "validated_at": "2026-01-02T...",
    "validator": "cursor_agent"
  },
  "summary": {
    "TRUE_WRONG": 820,
    "FALSE_NEGATIVE": 35,
    "AMBIGUOUS": 16
  },
  "results": [
    {
      "source_file": "data/results/distortion/gpt_4o_difficulty_1_0/results.jsonl",
      "record_index": 45,
      "question_id": 3088,
      "miu": 0.5,
      "ground_truth": "\\frac{4}{3}",
      "model_answer": "4/3",
      "original_match_type": "no_match",
      "validation_category": "FALSE_NEGATIVE",
      "validation_reason": "Equivalent fraction notation: LaTeX \\frac{4}{3} equals plain 4/3",
      "confidence": "HIGH"
    },
    ...
  ]
}
```

### Step 4: Generate Summary Report

Create: `data/validation/VALIDATION_REPORT.md`

Include:
1. Total counts by category
2. Breakdown by model and difficulty
3. Common patterns found in FALSE_NEGATIVE cases
4. List of AMBIGUOUS cases that may need human review
5. Recommended corrections to the matching algorithm

---

## ⚠️ IMPORTANT GUIDELINES

### DO:
- Use mathematical equivalence checking (sympy or similar if needed)
- Normalize LaTeX before comparison
- Consider commutativity (a+b = b+a)
- Consider associativity ((a+b)+c = a+(b+c))
- Handle floating point tolerance (0.333... ≈ 1/3)
- Document your reasoning for each categorization

### DO NOT:
- Guess when uncertain - use AMBIGUOUS
- Assume variable names matter (x vs t) without context
- Over-correct - when in doubt, keep as TRUE_WRONG
- Modify the original result files (create new validation file)

### CONFIDENCE LEVELS
Assign confidence to each validation:
- **HIGH**: Clear-cut case (numeric equivalence, obvious format difference)
- **MEDIUM**: Requires interpretation but likely correct
- **LOW**: Edge case, could go either way

---

## 📤 EXPECTED DELIVERABLES

1. **`data/validation/answer_validation_results.json`**
   - Complete validation results for all 871 cases

2. **`data/validation/VALIDATION_REPORT.md`**
   - Human-readable summary report

3. **`data/validation/false_negatives_to_correct.json`**
   - List of records that should have `is_correct` changed to `true`
   - Format: `[{source_file, record_identifier, ground_truth, model_answer, reason}]`

4. **`data/validation/ambiguous_cases.json`**
   - Cases needing human review with original questions
   - Format includes question text for context

---

## 🚀 EXECUTION STEPS

1. **Create validation directory**: `mkdir -p data/validation`

2. **Extract no_match records**: 
   - Read all result files
   - Filter for validation candidates
   - Save to working file

3. **Process each record**:
   - Apply equivalence checks
   - Categorize as TRUE_WRONG / FALSE_NEGATIVE / AMBIGUOUS
   - Record reasoning

4. **Generate outputs**:
   - Main results JSON
   - Summary report MD
   - Correction list JSON
   - Ambiguous cases JSON

5. **Validate outputs**:
   - Ensure all 871 cases are categorized
   - Check JSON validity
   - Verify counts match

---

## 📝 NOTES FOR THE AGENT

- This task is **isolated** from other data corrections being done in the project
- Do NOT modify existing result files - only create new validation files
- The validation output will be used later to update accuracy calculations
- If you need to see original questions for AMBIGUOUS cases, they are in:
  - `data/source/difficulty_1.0/difficulty_1_baseline_questions.json`
  - `data/source/difficulty_1.5/difficulty_1.5_baseline_questions.json`

---

**BEGIN VALIDATION TASK**

