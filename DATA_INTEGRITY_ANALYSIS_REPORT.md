# Chameleon Data Integrity Analysis Report
**Generated:** January 2, 2026

---

## Executive Summary

This report provides a comprehensive analysis of the data integrity for the Chameleon research project, examining source data, evaluation results, and alignment between all components across 4 models (GPT-4o, GPT-5, GPT-5-mini, Mistral Large) and 2 difficulty levels (1.0 and 1.5).

### Overall Status: ⚠️ REQUIRES ATTENTION

While the core data structure is largely intact, several significant issues have been identified that may impact research validity:

| Issue Category | Severity | Status |
|----------------|----------|--------|
| Token Limit Failures | 🔴 HIGH | 219 total empty answers across models |
| Missing Evaluation Records | 🟡 MEDIUM | 8 records missing (398/400, 397/400) |
| Source File Format Inconsistency | 🟡 MEDIUM | Mixed flat/nested formats |
| Corrected Empty Answer Logic | 🔴 HIGH | 12 records marked "correct" despite empty answers |
| Question-ID Alignment | 🟢 OK | All models aligned with source |
| Summary Accuracy Consistency | 🟢 OK | All summaries match computed values |

---

## 1. Source Data Analysis

### 1.1 Baseline Questions
| Difficulty | Total Questions | Status |
|------------|-----------------|--------|
| 1.0 | 100 | ✅ Complete |
| 1.5 | 100 | ✅ Complete |

**Finding:** All 100 unique questions present in both difficulty levels with proper metadata alignment.

### 1.2 Distortion Data
| Difficulty | Flat Records | Nested Records | Total Distortions | Expected | Status |
|------------|--------------|----------------|-------------------|----------|--------|
| 1.0 | 156 | 61 (with 244 nested) | 400 | 400 | ✅ Complete |
| 1.5 | 180 | 55 (with 220 nested) | 400 | 400 | ✅ Complete |

**Finding:** ⚠️ **Mixed Format Inconsistency**
- The distortion files contain TWO different formats:
  1. **Flat format:** Individual records with `miu` field directly in the record
  2. **Nested format:** Records with a `distortions` array containing 4 MIU variants

**Reason:** This appears to be the result of an incremental generation process where distortions were generated in batches at different times. The nested format seems to be from the initial generation, while flat format was added later to complete the 400 distortions.

**Impact:** While the total count is correct (400), this inconsistency could cause issues if evaluation scripts don't handle both formats. The evaluation results indicate the scripts DID correctly flatten both formats.

### 1.3 MIU Level Coverage
| Difficulty | MIU 0.2 | MIU 0.5 | MIU 0.7 | MIU 0.9 |
|------------|---------|---------|---------|---------|
| 1.0 | 100 | 100 | 100 | 100 |
| 1.5 | 100 | 100 | 100 | 100 |

**Status:** ✅ Complete coverage - Each of the 100 questions has all 4 MIU levels.

---

## 2. Baseline Results Analysis

### 2.1 Performance Summary
| Model | Diff 1.0 Accuracy | Diff 1.5 Accuracy | Empty 1.0 | Empty 1.5 |
|-------|-------------------|-------------------|-----------|-----------|
| GPT-4o | **75.0%** | **57.0%** | 0 | 0 |
| GPT-5 | **97.0%** | **90.0%** | 0 | 3 |
| GPT-5-mini | **96.0%** | **89.0%** | 0 | 1 |
| Mistral Large | **69.0%** | **49.0%** | 0 | 0 |

### 2.2 Empty Answer Issues in Baseline

**GPT-5 Difficulty 1.5:** 3 empty answers
- Output tokens for all empty: **1200** (exactly at limit)
- **Reason:** Reasoning token budget exhausted before final answer output

**GPT-5-mini Difficulty 1.5:** 1 empty answer
- Output tokens: **150** (exactly at limit)
- **Reason:** Much smaller token limit caused truncation

**Impact on Research:** These 4 empty baseline answers are counted as INCORRECT, which means:
- GPT-5's "true" accuracy on difficulty 1.5 could be ~92.8% if these had completed
- GPT-5-mini's "true" accuracy on difficulty 1.5 could be ~89.9%

### 2.3 Retry Mechanism Evidence
| Model/Difficulty | Retried | Fixed |
|------------------|---------|-------|
| GPT-5-mini 1.0 | 10 | 2 |
| GPT-5-mini 1.5 | 30 | 4 |
| Mistral Large 1.0 | 0 | 5 |
| Mistral Large 1.5 | 0 | 5 |

**Finding:** A retry/correction mechanism was applied, primarily to GPT-5-mini and Mistral Large. This indicates awareness of evaluation issues during the process.

---

## 3. Distortion Results Analysis

### 3.1 Performance Summary
| Model | Diff 1.0 Acc | Diff 1.5 Acc | Empty 1.0 | Empty 1.5 | Missing 1.0 | Missing 1.5 |
|-------|--------------|--------------|-----------|-----------|-------------|-------------|
| GPT-4o | **74.75%** | **53.75%** | 0 | 0 | 0 | 0 |
| GPT-5 | **95.00%** | **88.19%** | 0 | 10 | 0 | 2 |
| GPT-5-mini | **83.38%** | **64.48%** | 70 | 139 | 3 | 3 |
| Mistral Large | **67.75%** | **43.00%** | 0 | 0 | 0 | 0 |

### 3.2 🔴 CRITICAL: Empty Answer Token Limit Failures

| Model/Difficulty | Empty Answers | Token Limit Hit | Pattern |
|------------------|---------------|-----------------|---------|
| GPT-5 Diff 1.5 | 10 | 1200 tokens | All empty hit exactly 1200 |
| GPT-5-mini Diff 1.0 | 70 | 150 tokens | All empty hit exactly 150 |
| GPT-5-mini Diff 1.5 | 139 | 150 tokens | All empty hit exactly 150 |

**Analysis:**
- **GPT-5-mini is severely impacted** - The 150 token output limit is insufficient for many mathematical reasoning tasks
- Empty answers are **NOT random failures** - they are systematic token limit exhaustions
- The reasoning process consumed all available tokens before outputting the final answer

**True Performance (Excluding Token Limit Failures):**
| Model/Difficulty | Reported Accuracy | Adjusted Accuracy* | Difference |
|------------------|-------------------|-------------------|------------|
| GPT-5 Diff 1.5 | 88.19% | ~90.5% | +2.3% |
| GPT-5-mini Diff 1.0 | 83.38% | ~98.5% | +15.1% |
| GPT-5-mini Diff 1.5 | 64.48% | ~99.2% | +34.7% |

*Accuracy of non-empty answers only

**Impact on Research Conclusions:**
- GPT-5-mini's distortion performance appears much worse than it actually is
- The ~35% accuracy drop for GPT-5-mini Diff 1.5 is **almost entirely due to token limits**, not distortion vulnerability
- Only ~2-4 non-empty incorrect answers exist for GPT-5-mini distortion evaluations

### 3.3 Missing Record Analysis

| Model/Difficulty | Missing Records | Specific Pairs |
|------------------|-----------------|----------------|
| GPT-5 Diff 1.5 | 2 | Q2834@0.7, Q3070@0.7 |
| GPT-5-mini Diff 1.0 | 3 | Q2850@0.5, Q2870@0.5, Q3167@0.5 |
| GPT-5-mini Diff 1.5 | 3 | Q2706@0.5, Q2938@0.5, Q3132@0.9 |

**Reason:** These are likely batch processing failures or API timeouts that weren't retried. The small number (8 out of 3,200 total evaluations = 0.25%) is acceptable but should be documented.

### 3.4 🔴 CRITICAL: Corrected Empty Answer Anomaly

**Found 12 records marked as "correct" despite having empty model answers:**
- GPT-5-mini Diff 1.0: 8 records
- GPT-5-mini Diff 1.5: 4 records

**Match Type:** `corrected_empty_answer`

**Example:**
```
Question ID: 3460
MIU: 0.2
Model answer: ""
Ground truth: "Thursday"
Is correct: True ⚠️
Match type: corrected_empty_answer
```

**Analysis:** This appears to be a correction mechanism that INCORRECTLY marked empty answers as correct. This is a **data integrity violation** - an empty answer cannot logically match "Thursday".

**Impact:** 
- Inflates GPT-5-mini's correct count by 12
- The actual "true positive" count should be reduced by 12
- This affects the accuracy calculations by ~2-3%

---

## 4. Baseline vs Distortion Performance Delta

| Model | Diff 1.0 Delta | Diff 1.5 Delta | Interpretation |
|-------|----------------|----------------|----------------|
| GPT-4o | +0.25% | +3.25% | **Minimal degradation** - Model is distortion-resilient |
| GPT-5 | +2.00% | +1.81% | **Minimal degradation** - Strong resilience |
| GPT-5-mini | +12.62% | +24.52% | **⚠️ MISLEADING** - Primarily token limit issue |
| Mistral Large | +1.25% | +6.00% | **Low degradation** - Reasonable resilience |

**Critical Note on GPT-5-mini Delta:**
The apparent 12-24% degradation is **NOT evidence of distortion vulnerability**. When adjusted for token limit failures:
- GPT-5-mini Diff 1.0 real delta: ~2-3% (similar to other models)
- GPT-5-mini Diff 1.5 real delta: ~5-10% (similar to other models)

---

## 5. Data Quality Score Card

### Source Data
| Component | Status | Score |
|-----------|--------|-------|
| Baseline question count | ✅ 100/100 for both difficulties | 100% |
| Distortion total count | ✅ 400/400 for both difficulties | 100% |
| Question ID alignment | ✅ All match across files | 100% |
| MIU level coverage | ✅ Complete 4-level coverage | 100% |
| Metadata accuracy | ✅ Matches actual data | 100% |
| Format consistency | ⚠️ Mixed flat/nested | 70% |

### Result Data
| Component | Status | Score |
|-----------|--------|-------|
| Baseline record completeness | ✅ 100/100 all models | 100% |
| Distortion record completeness | ⚠️ 8 missing (99.75%) | 99% |
| Summary-to-record consistency | ✅ All match | 100% |
| MIU breakdown accuracy | ✅ All match | 100% |
| Empty answer tracking | ✅ Correctly tracked | 100% |
| Corrected empty logic | 🔴 12 false positives | 60% |

---

## 6. Recommendations Before Continuing Research

### 6.1 CRITICAL Actions Required

1. **Fix GPT-5-mini Token Limit Issue**
   - Re-run GPT-5-mini evaluations with higher token limit (e.g., 500-1000 tokens)
   - This will provide true distortion resilience measurements
   - Current data makes GPT-5-mini appear artificially vulnerable

2. **Remove/Fix `corrected_empty_answer` Records**
   - The 12 records marked correct with empty answers should be:
     - Either re-evaluated with retry
     - Or marked as incorrect
   - Update summary statistics accordingly

3. **Recover 8 Missing Distortion Evaluations**
   - Re-run evaluations for:
     - GPT-5 Diff 1.5: Q2834@0.7, Q3070@0.7
     - GPT-5-mini Diff 1.0: Q2850@0.5, Q2870@0.5, Q3167@0.5
     - GPT-5-mini Diff 1.5: Q2706@0.5, Q2938@0.5, Q3132@0.9

### 6.2 RECOMMENDED Actions

4. **Standardize Distortion File Format**
   - Flatten all nested format records to flat format
   - Or document the parsing logic for both formats

5. **Add Adjusted Accuracy Metrics**
   - Include "accuracy excluding token failures" in summaries
   - This provides fairer model comparison

6. **Document Token Limits Used**
   - Add to metadata: `output_token_limit: 150` for GPT-5-mini
   - Add to metadata: `output_token_limit: 1200` for GPT-5

### 6.3 OPTIONAL Improvements

7. **Re-evaluate GPT-5 Token Limit Cases**
   - 10 cases in distortion + 3 in baseline could be recovered
   - Use higher token limit for these specific questions

8. **Track Questions That Consistently Cause Failures**
   - Q3047 failed on all 4 MIU levels for both GPT-5 and GPT-5-mini
   - Q2910 failed on 3 MIU levels for both models
   - These may require special attention or exclusion

---

## 7. Summary Statistics

### Token Limit Impact Summary
| Metric | Value |
|--------|-------|
| Total distortion evaluations | 3,200 |
| Total empty answers (token limit) | 219 |
| Percentage impacted | 6.8% |
| Models affected | GPT-5, GPT-5-mini |
| Most affected | GPT-5-mini Diff 1.5 (35% of its evaluations) |

### Data Completeness Summary
| Data Type | Expected | Actual | Completeness |
|-----------|----------|--------|--------------|
| Baseline evaluations | 800 | 800 | 100% |
| Distortion evaluations | 3,200 | 3,192 | 99.75% |
| Source questions | 200 | 200 | 100% |
| Source distortions | 800 | 800 | 100% |

---

## 8. Conclusion

The Chameleon dataset is **fundamentally sound** but has **implementation-level issues** that significantly impact the interpretability of results, particularly for GPT-5-mini. 

**Key Takeaway:** Before publishing or drawing conclusions:
1. The GPT-5-mini results are NOT valid measures of distortion resilience
2. The token limit of 150 tokens is inappropriate for complex math reasoning
3. After correction, GPT-5-mini likely has similar resilience to GPT-5

The data integrity is sufficient for GPT-4o and Mistral Large analysis, but GPT-5 and GPT-5-mini require remediation before valid conclusions can be drawn.

---

*Report generated by automated data integrity analysis*

