# 🧹 Cleanup Plan & New Research Flow
## Complete Reset for Verified Dataset

**Created:** January 4, 2026  
**Purpose:** Clean separation from problematic data + clear sequential flow

---

## Part 1: What to Remove/Archive

### 1.1 Files to ARCHIVE (Move to `archive/legacy_omnimath/`)

These files contain data from the problematic raw Omni-MATH dataset. We keep them for reference but move out of active directories.

```
TO ARCHIVE:
├── data/source/                          # ALL of it
│   ├── difficulty_1.0/
│   │   ├── difficulty_1_baseline_questions.json
│   │   ├── difficulty_1_distortions.json
│   │   └── difficulty_1_metadata.json
│   └── difficulty_1.5/
│       ├── difficulty_1.5_baseline_questions.json
│       ├── difficulty_1.5_distortions.json
│       └── difficulty_1.5_metadata.json
│
├── data/results/                         # ALL of it
│   ├── baseline/
│   │   ├── gpt_4o_difficulty_1_0/
│   │   ├── gpt_4o_difficulty_1_5/
│   │   ├── gpt_5_difficulty_1_0/
│   │   ├── gpt_5_difficulty_1_5/
│   │   ├── gpt_5_mini_difficulty_1_0/
│   │   ├── gpt_5_mini_difficulty_1_5/
│   │   ├── mistral_large_latest_difficulty_1_0/
│   │   └── mistral_large_latest_difficulty_1_5/
│   └── distortion/
│       └── ... (all model directories)
│
├── data/validation/                      # ALL of it
│   ├── ambiguous_cases.json
│   ├── answer_validation_results.json
│   ├── CORRECTED_DEEP_ANALYSIS.md
│   ├── DEEP_ANALYSIS_UNCLEAR_CASES.md
│   ├── false_negatives_to_correct.json
│   ├── validate_answers.py
│   ├── VALIDATION_ACTION_PLAN.md
│   └── VALIDATION_REPORT.md
│
├── output/                               # ALL of it
│   ├── plots/
│   ├── reports/
│   └── exports/
│
└── DATA_INTEGRITY_ANALYSIS_REPORT.md     # Root level
```

### 1.2 Files to REMOVE (Obsolete)

These are old/one-time scripts no longer needed:

```
TO DELETE (already in archive, verify and clean):
├── archive/onetime_scripts/              # Review, may delete entirely
└── archive/legacy_mmlu_workflow/         # Old workflow, not relevant
```

### 1.3 Files to KEEP (Core Code - Still Valid)

These modules contain reusable logic:

```
KEEP (update as needed):
├── src/
│   ├── modules/
│   │   ├── answer_comparator.py          # Keep + add math-verify
│   │   ├── batch_converter.py            # Keep
│   │   ├── distortion_validator.py       # Keep + enhance
│   │   ├── evaluation_prompt.py          # Keep
│   │   ├── math_distortion_prompts.py    # Keep
│   │   ├── results_parser.py             # Keep + update schema
│   │   ├── bigmath_loader.py             # NEW - already created
│   │   └── omnimath_loader.py            # DEPRECATE (keep for reference)
│   │
│   ├── flows/
│   │   ├── generate_distortions.py       # Keep + update data source
│   │   ├── evaluate_baseline.py          # Keep + update data source
│   │   ├── evaluate_distortions.py       # Keep + update data source
│   │   ├── analyze_results.py            # Keep
│   │   ├── verify_data.py                # Keep + update paths
│   │   └── review_corrections.py         # DEPRECATE
│   │
│   └── analysis/
│       └── run_analysis.py               # Keep
│
├── tests/
│   └── test_answer_comparator.py         # Keep + add new tests
│
├── docs/                                 # Keep all new docs
├── prompts/                              # Keep
├── requirements.txt                      # Keep + add math-verify
└── README.md                             # Update later
```

---

## Part 2: Archive Script

Run this to archive all old data:

```bash
#!/bin/bash
# archive_legacy_data.sh

ARCHIVE_DIR="archive/legacy_omnimath_data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🗂️  Archiving legacy Omni-MATH data..."
echo "    Destination: $ARCHIVE_DIR"

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Archive source data
if [ -d "data/source" ]; then
    echo "    Moving data/source/..."
    mv data/source "$ARCHIVE_DIR/source_$TIMESTAMP"
fi

# Archive results
if [ -d "data/results" ]; then
    echo "    Moving data/results/..."
    mv data/results "$ARCHIVE_DIR/results_$TIMESTAMP"
fi

# Archive validation
if [ -d "data/validation" ]; then
    echo "    Moving data/validation/..."
    mv data/validation "$ARCHIVE_DIR/validation_$TIMESTAMP"
fi

# Archive output
if [ -d "output" ]; then
    echo "    Moving output/..."
    mv output "$ARCHIVE_DIR/output_$TIMESTAMP"
fi

# Archive root-level report
if [ -f "DATA_INTEGRITY_ANALYSIS_REPORT.md" ]; then
    echo "    Moving DATA_INTEGRITY_ANALYSIS_REPORT.md..."
    mv DATA_INTEGRITY_ANALYSIS_REPORT.md "$ARCHIVE_DIR/"
fi

# Create fresh directories
echo "📁 Creating fresh directory structure..."
mkdir -p data/source_verified
mkdir -p data/results_verified/baseline
mkdir -p data/results_verified/distortion
mkdir -p data/distortion_validation
mkdir -p output/plots
mkdir -p output/reports
mkdir -p output/exports

echo "✅ Archive complete!"
echo "   Legacy data: $ARCHIVE_DIR"
echo "   Fresh directories created for new pipeline"
```

---

## Part 3: The New Research Flow (Clear Sequential Phases)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NEW CHAMELEON RESEARCH FLOW                          │
│                     (Verified Dataset Pipeline)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 1: DATASET CREATION                                            ║  │
│  ║  ═══════════════════════════════════════════════════════════════════  ║  │
│  ║                                                                       ║  │
│  ║  INPUT:  Big-Math RL-Verified (HuggingFace)                          ║  │
│  ║                                                                       ║  │
│  ║  STEPS:                                                               ║  │
│  ║    1. Load dataset from SynthLabsAI/Big-Math-RL-Verified             ║  │
│  ║    2. Filter: source == "omni-math"                                  ║  │
│  ║    3. Filter: level in tier range (e.g., T3: 3.0-5.0)               ║  │
│  ║    4. Select N questions (e.g., 100)                                 ║  │
│  ║    5. Export to data/source_verified/tier_T3/baseline_questions.json ║  │
│  ║                                                                       ║  │
│  ║  OUTPUT: Verified baseline questions with clean answers              ║  │
│  ║                                                                       ║  │
│  ║  VALIDATION GATE:                                                     ║  │
│  ║    □ All questions have non-empty problem text                       ║  │
│  ║    □ All questions have closed-form answers                          ║  │
│  ║    □ No references to "diagram", "figure", "options", "following"    ║  │
│  ║    □ Question count matches expected                                 ║  │
│  ║                                                                       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 2: DISTORTION GENERATION                                       ║  │
│  ║  ═══════════════════════════════════════════════════════════════════  ║  │
│  ║                                                                       ║  │
│  ║  INPUT:  Verified baseline questions                                  ║  │
│  ║                                                                       ║  │
│  ║  STEPS:                                                               ║  │
│  ║    1. For each question, generate distortions at μ = 0.2, 0.5, 0.7, 0.9 ║
│  ║    2. Use GPT-4o with temperature calibrated to μ level              ║  │
│  ║    3. Apply gibberish detection (reject garbage outputs)             ║  │
│  ║    4. Save to data/source_verified/tier_T3/distortions_raw.json      ║  │
│  ║                                                                       ║  │
│  ║  OUTPUT: Raw distortions (not yet validated)                         ║  │
│  ║                                                                       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 3: DISTORTION VALIDATION  ⚠️ CRITICAL GATE                    ║  │
│  ║  ═══════════════════════════════════════════════════════════════════  ║  │
│  ║                                                                       ║  │
│  ║  INPUT:  Raw distortions                                              ║  │
│  ║                                                                       ║  │
│  ║  VALIDATION CHECKS (for each distortion):                             ║  │
│  ║                                                                       ║  │
│  ║    ┌─────────────────────────────────────────────────────────────┐   ║  │
│  ║    │ CHECK 1: Mathematical Integrity                             │   ║  │
│  ║    │   • All numbers preserved exactly                           │   ║  │
│  ║    │   • All equations preserved                                 │   ║  │
│  ║    │   • All variables preserved                                 │   ║  │
│  ║    │   • No new constraints added                                │   ║  │
│  ║    │   • No constraints removed                                  │   ║  │
│  ║    └─────────────────────────────────────────────────────────────┘   ║  │
│  ║                                                                       ║  │
│  ║    ┌─────────────────────────────────────────────────────────────┐   ║  │
│  ║    │ CHECK 2: Answer Preservation                                 │   ║  │
│  ║    │   • Distorted question should have SAME answer as original  │   ║  │
│  ║    │   • Test with math-verify if needed                         │   ║  │
│  ║    └─────────────────────────────────────────────────────────────┘   ║  │
│  ║                                                                       ║  │
│  ║    ┌─────────────────────────────────────────────────────────────┐   ║  │
│  ║    │ CHECK 3: No Gibberish/Corruption                            │   ║  │
│  ║    │   • No random characters                                    │   ║  │
│  ║    │   • No code fragments                                       │   ║  │
│  ║    │   • No foreign scripts mixed in                             │   ║  │
│  ║    │   • Reasonable length (not 5x original)                     │   ║  │
│  ║    └─────────────────────────────────────────────────────────────┘   ║  │
│  ║                                                                       ║  │
│  ║    ┌─────────────────────────────────────────────────────────────┐   ║  │
│  ║    │ CHECK 4: Question Completeness                              │   ║  │
│  ║    │   • Has a clear question/goal                               │   ║  │
│  ║    │   • All necessary context present                           │   ║  │
│  ║    │   • No truncated sentences                                  │   ║  │
│  ║    └─────────────────────────────────────────────────────────────┘   ║  │
│  ║                                                                       ║  │
│  ║  ACTIONS:                                                             ║  │
│  ║    • PASS → Add to validated set                                     ║  │
│  ║    • FAIL → Log issue, regenerate, or exclude                        ║  │
│  ║                                                                       ║  │
│  ║  OUTPUT: data/source_verified/tier_T3/distortions_validated.json     ║  │
│  ║          data/distortion_validation/validation_report.json           ║  │
│  ║                                                                       ║  │
│  ║  SUCCESS CRITERIA:                                                    ║  │
│  ║    □ 100% of distortions pass mathematical integrity                 ║  │
│  ║    □ 100% of distortions pass answer preservation                    ║  │
│  ║    □ <5% need regeneration for gibberish                             ║  │
│  ║    □ Validation report shows all green                               ║  │
│  ║                                                                       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                            ┌──────┴──────┐                                  │
│                            │ ALL PASSED? │                                  │
│                            └──────┬──────┘                                  │
│                                   │                                         │
│                    ┌──────────────┼──────────────┐                          │
│                    │              │              │                          │
│                   NO          PARTIAL          YES                          │
│                    │              │              │                          │
│                    ▼              ▼              ▼                          │
│              ┌─────────┐   ┌───────────┐   ┌─────────────────────────────┐  │
│              │ FIX or  │   │ Regenerate│   │ PROCEED TO PHASE 4         │  │
│              │ EXCLUDE │   │ failures  │   │                             │  │
│              └────┬────┘   └─────┬─────┘   └─────────────────────────────┘  │
│                   │              │                                          │
│                   └──────────────┘                                          │
│                          │                                                  │
│                          ▼                                                  │
│                    (Back to validation)                                     │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                    │                                        │
│                                    ▼                                        │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 4: MODEL EVALUATION (API Requests)                             ║  │
│  ║  ═══════════════════════════════════════════════════════════════════  ║  │
│  ║                                                                       ║  │
│  ║  PRECONDITION: Phase 3 validation 100% complete                       ║  │
│  ║                                                                       ║  │
│  ║  INPUT:  Validated distortions + Baseline questions                   ║  │
│  ║                                                                       ║  │
│  ║  STEP 4A: BASELINE EVALUATION                                         ║  │
│  ║    For each model (GPT-4o, GPT-5, GPT-5-mini, Mistral-Large):        ║  │
│  ║      1. Send baseline questions via API                              ║  │
│  ║      2. Collect responses                                            ║  │
│  ║      3. Verify answers with math-verify                              ║  │
│  ║      4. Save to data/results_verified/baseline/{model}_tier_T3/      ║  │
│  ║                                                                       ║  │
│  ║  STEP 4B: DISTORTION EVALUATION                                       ║  │
│  ║    For each model:                                                    ║  │
│  ║      For each μ level (0.2, 0.5, 0.7, 0.9):                          ║  │
│  ║        1. Send distorted questions via API                           ║  │
│  ║        2. Collect responses                                          ║  │
│  ║        3. Verify answers with math-verify                            ║  │
│  ║        4. Save to data/results_verified/distortion/{model}_tier_T3/  ║  │
│  ║                                                                       ║  │
│  ║  OUTPUT: Complete evaluation results for all models                   ║  │
│  ║                                                                       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 5: ANALYSIS & REPORTING                                        ║  │
│  ║  ═══════════════════════════════════════════════════════════════════  ║  │
│  ║                                                                       ║  │
│  ║  INPUT:  All evaluation results                                       ║  │
│  ║                                                                       ║  │
│  ║  STEPS:                                                               ║  │
│  ║    1. Calculate baseline accuracy per model                          ║  │
│  ║    2. Calculate distortion accuracy per model per μ                  ║  │
│  ║    3. Compute degradation delta (baseline - distortion)              ║  │
│  ║    4. Run McNemar's test for statistical significance                ║  │
│  ║    5. Generate visualizations                                        ║  │
│  ║    6. Produce final research report                                  ║  │
│  ║                                                                       ║  │
│  ║  OUTPUT:                                                              ║  │
│  ║    • output/reports/STATISTICAL_ANALYSIS_REPORT.md                   ║  │
│  ║    • output/plots/*.png                                              ║  │
│  ║    • output/reports/analysis_data.json                               ║  │
│  ║                                                                       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: New Directory Structure (After Cleanup)

```
Chameleon/
├── archive/
│   ├── legacy_omnimath_data/           # OLD DATA (archived)
│   │   ├── source_YYYYMMDD/
│   │   ├── results_YYYYMMDD/
│   │   ├── validation_YYYYMMDD/
│   │   └── output_YYYYMMDD/
│   ├── legacy_mmlu_workflow/           # Old scripts
│   └── onetime_scripts/                # Old scripts
│
├── data/
│   ├── source_verified/                # NEW: Verified source data
│   │   └── tier_T3/
│   │       ├── baseline_questions.json
│   │       ├── distortions_raw.json       # Before validation
│   │       ├── distortions_validated.json # After validation
│   │       └── metadata.json
│   │
│   ├── distortion_validation/          # NEW: Validation artifacts
│   │   ├── validation_report.json
│   │   ├── failed_distortions.json
│   │   └── regeneration_log.json
│   │
│   └── results_verified/               # NEW: Evaluation results
│       ├── baseline/
│       │   ├── gpt_4o_tier_T3/
│       │   ├── gpt_5_tier_T3/
│       │   ├── gpt_5_mini_tier_T3/
│       │   └── mistral_large_tier_T3/
│       └── distortion/
│           ├── gpt_4o_tier_T3/
│           ├── gpt_5_tier_T3/
│           ├── gpt_5_mini_tier_T3/
│           └── mistral_large_tier_T3/
│
├── output/
│   ├── plots/
│   ├── reports/
│   └── exports/
│
├── src/
│   ├── modules/
│   │   ├── bigmath_loader.py           # NEW: Primary data loader
│   │   ├── answer_comparator.py        # + math-verify integration
│   │   ├── distortion_validator.py     # Enhanced for Phase 3
│   │   ├── evaluation_prompt.py
│   │   ├── math_distortion_prompts.py
│   │   ├── batch_converter.py
│   │   └── results_parser.py
│   │
│   ├── flows/
│   │   ├── phase1_create_dataset.py    # NEW: Dedicated Phase 1 script
│   │   ├── phase2_generate_distortions.py  # Renamed/updated
│   │   ├── phase3_validate_distortions.py  # NEW: Dedicated validation
│   │   ├── phase4_evaluate_models.py       # Combined baseline + distortion
│   │   ├── phase5_analyze_results.py       # Renamed/updated
│   │   └── run_full_pipeline.py            # NEW: Orchestrator
│   │
│   └── analysis/
│       └── run_analysis.py
│
├── docs/
│   ├── RESEARCH_TRANSITION_PLAN.md
│   ├── PIPELINE_STATUS.md
│   ├── TRANSITION_QUICK_REFERENCE.md
│   └── CLEANUP_AND_NEW_FLOW.md         # This document
│
├── tests/
├── prompts/
├── requirements.txt
└── README.md
```

---

## Part 5: Summary of Actions

### Step 1: Run Archive Script
```bash
# Make executable and run
chmod +x archive_legacy_data.sh
./archive_legacy_data.sh
```

### Step 2: Create New Flow Scripts
Create dedicated scripts for each phase:
- `phase1_create_dataset.py`
- `phase2_generate_distortions.py`
- `phase3_validate_distortions.py`
- `phase4_evaluate_models.py`
- `phase5_analyze_results.py`

### Step 3: Execute Pipeline Sequentially
```bash
# Phase 1: Create verified dataset
python -m src.flows.phase1_create_dataset --tier T3 --count 100

# Phase 2: Generate distortions
python -m src.flows.phase2_generate_distortions --tier T3

# Phase 3: Validate distortions (MUST PASS BEFORE PHASE 4)
python -m src.flows.phase3_validate_distortions --tier T3

# Phase 4: Evaluate models (only after Phase 3 passes)
python -m src.flows.phase4_evaluate_models --tier T3 --model all

# Phase 5: Analyze results
python -m src.flows.phase5_analyze_results --tier T3
```

---

## Part 6: Phase 3 Validation Details

This is the **CRITICAL GATE** you emphasized. Here's what gets validated:

### Validation Checks Matrix

| Check | What It Verifies | How | Fail Action |
|-------|------------------|-----|-------------|
| **Numbers Preserved** | All numerical values identical | Regex extraction + comparison | Regenerate |
| **Variables Preserved** | All variable names present | Variable extraction + check | Regenerate |
| **Equations Preserved** | LaTeX equations unchanged in meaning | Symbolic comparison | Regenerate |
| **No Added Constraints** | Distortion doesn't add new conditions | Semantic analysis | Regenerate |
| **No Removed Constraints** | Distortion doesn't remove conditions | Semantic analysis | Regenerate |
| **Answer Unchanged** | Same answer as original | math-verify | Regenerate |
| **No Gibberish** | Clean readable text | Gibberish detector | Regenerate |
| **Complete Question** | Has clear goal/question | End-sentence check | Flag for review |
| **Reasonable Length** | Not too long/short | Length ratio check | Flag for review |

### Validation Output

```json
// data/distortion_validation/validation_report.json
{
  "tier": "T3",
  "total_distortions": 400,
  "validation_summary": {
    "passed": 385,
    "failed": 10,
    "regenerated": 5,
    "excluded": 0
  },
  "checks": {
    "numbers_preserved": {"passed": 398, "failed": 2},
    "variables_preserved": {"passed": 400, "failed": 0},
    "equations_preserved": {"passed": 397, "failed": 3},
    "no_gibberish": {"passed": 395, "failed": 5},
    "answer_unchanged": {"passed": 400, "failed": 0}
  },
  "failures": [
    {
      "question_id": "omni-math-1234",
      "miu": 0.9,
      "check_failed": "numbers_preserved",
      "original_numbers": ["5", "12", "7"],
      "distorted_numbers": ["5", "12"],
      "action": "regenerated",
      "attempt": 2,
      "final_status": "passed"
    }
  ],
  "ready_for_phase4": true
}
```

---

**This document provides the complete plan for cleanup and the new sequential flow. Should I create the archive script and the new phase scripts?**

