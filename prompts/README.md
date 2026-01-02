# Chameleon Research Optimization Prompts

This directory contains execution prompts for Cursor Agent Composer models to bring the Chameleon research project to academic publication standards.

---

## 📁 Prompt Files

### 1. `MAIN_EXECUTION_PLAN_PROMPT.md`
**Purpose**: Complete data remediation and documentation

**Covers Decisions 1-8**:
- ✅ Re-evaluate GPT-5-mini token failures (209 cases)
- ✅ Re-evaluate GPT-5 token failures (13 cases)  
- ✅ Re-evaluate corrected empty answers (12 cases)
- ✅ Complete missing evaluations (8 cases)
- ✅ Standardize distortion file format
- ✅ Re-evaluate baseline empty answers (4 cases)
- ✅ Use 1200 token limit for all
- ✅ Generate complete documentation

**Estimated API Calls**: ~230 evaluations

**Execution Time**: 1-2 hours (depending on API rate limits)

---

### 2. `ANSWER_VALIDATION_TASK_PROMPT.md`
**Purpose**: Validate all "incorrect" answers for false negatives

**Covers Decisions 9-10**:
- ✅ Review all 871 no_match cases
- ✅ Categorize as TRUE_WRONG / FALSE_NEGATIVE / AMBIGUOUS
- ✅ Generate detailed validation report

**Execution Time**: 30-60 minutes

**Note**: This task is ISOLATED and should be run separately from the main execution plan.

---

## 🔄 Recommended Execution Order

### Option A: Sequential (Safest)
1. Run `MAIN_EXECUTION_PLAN_PROMPT.md` first
2. Wait for completion
3. Run `ANSWER_VALIDATION_TASK_PROMPT.md`
4. Integrate validation results

### Option B: Parallel (Faster)
1. Run both prompts simultaneously
2. Main plan modifies GPT-5 and GPT-5-mini results
3. Validation analyzes GPT-4o and Mistral (unmodified)
4. After main plan completes, re-run validation on updated GPT-5/mini results

**Recommendation**: Option A for data integrity

---

## 📊 Expected Outcomes

After executing both prompts:

### Data Improvements
| Metric | Before | After |
|--------|--------|-------|
| GPT-5-mini empty answers | 210 | 0 |
| GPT-5 empty answers | 13 | 0 |
| Missing evaluations | 8 | 0 |
| False positive corrections | 12 | 0 |
| Distortion file format | Mixed | Flat |

### Documentation Generated
- `docs/METHODOLOGY.md`
- `docs/DATA_QUALITY_REPORT.md`
- `output/reports/ADJUSTED_METRICS.md`
- `output/exports/question_analysis.csv`
- `data/validation/VALIDATION_REPORT.md`
- `data/validation/answer_validation_results.json`

---

## ⚠️ Prerequisites

Before running the prompts:

1. **API Access**: Ensure OpenAI/Mistral API keys are configured
2. **Backup**: Consider backing up `data/results/` directory
3. **Dependencies**: Python environment with required packages

---

## 📝 Decision Summary

| # | Decision | Choice |
|---|----------|--------|
| 1 | GPT-5-mini token failures | Re-evaluate failures only |
| 2 | GPT-5 token failures | Re-evaluate 13 cases |
| 3 | Corrected empty answers | Re-evaluate 12 records |
| 4 | Missing records | Evaluate 8 missing |
| 5 | Source file format | Flatten to flat format |
| 6 | Baseline empty answers | Re-evaluate 4 |
| 7 | Token limit | 1200 for both models |
| 8 | Documentation | All components (A+B+C+D) |
| 9 | Answer validation | LLM review ALL no_match (871) |
| 10 | Validation output | Detailed categorization |

---

## 🚀 Quick Start

### For Main Execution Plan:
```
Open Cursor → Agent Composer → Paste contents of MAIN_EXECUTION_PLAN_PROMPT.md
```

### For Answer Validation Task:
```
Open Cursor → Agent Composer → Paste contents of ANSWER_VALIDATION_TASK_PROMPT.md
```

---

*Created: January 2, 2026*

