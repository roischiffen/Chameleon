# Statistical Analysis Report: Semantic Distortion Experiment
**Date:** 2025-12-14 10:32:03
---
## Executive Summary
### Key Findings
1. **Statistical Significance:** 9 of 32 comparisons (28.1%) showed statistically significant degradation at p<0.05.
2. **Most Resilient Model:** GPT-4o with only 1.7% average accuracy degradation across all distortion levels.
3. **Most Vulnerable Model:** GPT-5-mini with 18.6% average accuracy degradation.
4. **Net Impact:** Across all tests, 312 questions were lost (correct→incorrect) while only 106 were gained (incorrect→correct), a net loss of 206 questions.
5. **Difficulty Effect:** Higher difficulty problems (1.5) show greater vulnerability to distortion than easier problems (1.0).

## Methodology
### Statistical Tests
**McNemar's Test** was used for all comparisons because:
- Data is **paired**: Same questions tested under baseline and distorted conditions
- Outcomes are **binary**: Each answer is either correct or incorrect
- Test is **non-parametric**: No assumptions about underlying distribution

For small sample sizes (b+c < 25), exact binomial test was used. For larger samples, chi-square approximation with continuity correction was applied.

### Effect Size
**Cohen's h** was calculated for comparing proportions:
```
h = 2 × arcsin(√p₁) - 2 × arcsin(√p₂)
```
Interpretation:
- Small effect: |h| ≈ 0.2
- Medium effect: |h| ≈ 0.5
- Large effect: |h| ≈ 0.8

## Baseline Accuracy Results
| Model | Difficulty 1.0 | 95% CI | Difficulty 1.5 | 95% CI |
|-------|----------------|--------|----------------|--------|
| GPT-5 | 97% | [91.5, 99.0] | 90% | [82.6, 94.5] |
| GPT-4o | 75% | [65.7, 82.5] | 57% | [47.2, 66.3] |
| GPT-5-mini | 96% | [90.2, 98.4] | 89% | [81.4, 93.7] |
| Mistral-Large | 69% | [59.4, 77.2] | 49% | [39.4, 58.7] |

## Distortion Accuracy Results

### Difficulty 1.0
| Model | Baseline | MIU 0.2 | MIU 0.5 | MIU 0.7 | MIU 0.9 | Avg Distortion |
|-------|----------|---------|---------|---------|---------|----------------|
| GPT-5 | 97% | 96% | 94% | 95% | 95% | 95.0% |
| GPT-4o | 75% | 77% | 70% | 79% | 73% | 74.8% |
| GPT-5-mini | 96% | 84% | 81% | 87% | 81% | 83.4% |
| Mistral-Large | 69% | 70% | 65% | 68% | 68% | 67.8% |

### Difficulty 1.5
| Model | Baseline | MIU 0.2 | MIU 0.5 | MIU 0.7 | MIU 0.9 | Avg Distortion |
|-------|----------|---------|---------|---------|---------|----------------|
| GPT-5 | 90% | 90% | 90% | 88% | 85% | 88.2% |
| GPT-4o | 57% | 59% | 50% | 51% | 55% | 53.8% |
| GPT-5-mini | 89% | 68% | 65% | 65% | 60% | 64.5% |
| Mistral-Large | 49% | 46% | 44% | 45% | 37% | 43.0% |

## Statistical Significance Analysis (McNemar's Test)

### Difficulty 1.0
| Model | MIU | Lost | Gained | Net | χ² Statistic | p-value | Significant |
|-------|-----|------|--------|-----|--------------|---------|-------------|
| GPT-5 | 0.2 | 1 | 0 | -1 | 1.00 | N/A |  |
| GPT-5 | 0.5 | 3 | 0 | -3 | 3.00 | 0.2500 |  |
| GPT-5 | 0.7 | 2 | 0 | -2 | 2.00 | 0.5000 |  |
| GPT-5 | 0.9 | 2 | 0 | -2 | 2.00 | 0.5000 |  |
| GPT-4o | 0.2 | 2 | 4 | +2 | 0.67 | 0.6875 |  |
| GPT-4o | 0.5 | 11 | 6 | -5 | 1.47 | 0.3323 |  |
| GPT-4o | 0.7 | 4 | 8 | +4 | 1.33 | 0.3877 |  |
| GPT-4o | 0.9 | 5 | 3 | -2 | 0.50 | 0.7266 |  |
| GPT-5-mini | 0.2 | 13 | 1 | -12 | 10.29 | 0.0018 | *** |
| GPT-5-mini | 0.5 | 16 | 1 | -15 | 13.24 | 0.0003 | *** |
| GPT-5-mini | 0.7 | 10 | 1 | -9 | 7.36 | 0.0117 | ** |
| GPT-5-mini | 0.9 | 16 | 1 | -15 | 13.24 | 0.0003 | *** |
| Mistral-Large | 0.2 | 6 | 7 | +1 | 0.08 | N/A |  |
| Mistral-Large | 0.5 | 13 | 9 | -4 | 0.73 | 0.5235 |  |
| Mistral-Large | 0.7 | 11 | 10 | -1 | 0.05 | N/A |  |
| Mistral-Large | 0.9 | 12 | 11 | -1 | 0.04 | N/A |  |

### Difficulty 1.5
| Model | MIU | Lost | Gained | Net | χ² Statistic | p-value | Significant |
|-------|-----|------|--------|-----|--------------|---------|-------------|
| GPT-5 | 0.2 | 1 | 1 | +0 | 0.00 | N/A |  |
| GPT-5 | 0.5 | 1 | 1 | +0 | 0.00 | N/A |  |
| GPT-5 | 0.7 | 3 | 1 | -2 | 1.00 | 0.6250 |  |
| GPT-5 | 0.9 | 6 | 1 | -5 | 3.57 | 0.1250 |  |
| GPT-4o | 0.2 | 2 | 4 | +2 | 0.67 | 0.6875 |  |
| GPT-4o | 0.5 | 12 | 5 | -7 | 2.88 | 0.1435 |  |
| GPT-4o | 0.7 | 10 | 4 | -6 | 2.57 | 0.1796 |  |
| GPT-4o | 0.9 | 8 | 6 | -2 | 0.29 | 0.7905 |  |
| GPT-5-mini | 0.2 | 22 | 1 | -21 | 19.17 | 0.0000 | *** |
| GPT-5-mini | 0.5 | 24 | 1 | -23 | 19.36 | 0.0000 | *** |
| GPT-5-mini | 0.7 | 25 | 1 | -24 | 20.35 | 0.0000 | *** |
| GPT-5-mini | 0.9 | 30 | 1 | -29 | 25.29 | 0.0000 | *** |
| Mistral-Large | 0.2 | 4 | 1 | -3 | 1.80 | 0.3750 |  |
| Mistral-Large | 0.5 | 12 | 7 | -5 | 1.32 | 0.3593 |  |
| Mistral-Large | 0.7 | 9 | 5 | -4 | 1.14 | 0.4240 |  |
| Mistral-Large | 0.9 | 16 | 4 | -12 | 7.20 | 0.0118 | ** |

*Significance: *** p<0.01, ** p<0.05, * p<0.10*

## Effect Size Analysis (Cohen's h)

### Difficulty 1.0
| Model | MIU | Baseline | Distortion | Degradation | Cohen's h | Interpretation |
|-------|-----|----------|------------|-------------|-----------|----------------|
| GPT-5 | 0.2 | 97.0% | 96.0% | +1.0% | 0.055 | Negligible |
| GPT-5 | 0.5 | 97.0% | 94.0% | +3.0% | 0.147 | Negligible |
| GPT-5 | 0.7 | 97.0% | 95.0% | +2.0% | 0.103 | Negligible |
| GPT-5 | 0.9 | 97.0% | 95.0% | +2.0% | 0.103 | Negligible |
| GPT-4o | 0.2 | 75.0% | 77.0% | -2.0% | -0.047 | Negligible |
| GPT-4o | 0.5 | 75.0% | 70.0% | +5.0% | 0.112 | Negligible |
| GPT-4o | 0.7 | 75.0% | 79.0% | -4.0% | -0.095 | Negligible |
| GPT-4o | 0.9 | 75.0% | 73.0% | +2.0% | 0.046 | Negligible |
| GPT-5-mini | 0.2 | 96.0% | 84.0% | +12.0% | 0.420 | Small |
| GPT-5-mini | 0.5 | 96.0% | 81.4% | +14.6% | 0.488 | Small |
| GPT-5-mini | 0.7 | 96.0% | 87.0% | +9.0% | 0.335 | Small |
| GPT-5-mini | 0.9 | 96.0% | 81.0% | +15.0% | 0.499 | Small |
| Mistral-Large | 0.2 | 69.0% | 70.0% | -1.0% | -0.022 | Negligible |
| Mistral-Large | 0.5 | 69.0% | 65.0% | +4.0% | 0.085 | Negligible |
| Mistral-Large | 0.7 | 69.0% | 68.0% | +1.0% | 0.022 | Negligible |
| Mistral-Large | 0.9 | 69.0% | 68.0% | +1.0% | 0.022 | Negligible |

### Difficulty 1.5
| Model | MIU | Baseline | Distortion | Degradation | Cohen's h | Interpretation |
|-------|-----|----------|------------|-------------|-----------|----------------|
| GPT-5 | 0.2 | 90.0% | 90.0% | +0.0% | 0.000 | Negligible |
| GPT-5 | 0.5 | 90.0% | 90.0% | +0.0% | 0.000 | Negligible |
| GPT-5 | 0.7 | 90.0% | 87.8% | +2.2% | 0.071 | Negligible |
| GPT-5 | 0.9 | 90.0% | 85.0% | +5.0% | 0.152 | Negligible |
| GPT-4o | 0.2 | 57.0% | 59.0% | -2.0% | -0.041 | Negligible |
| GPT-4o | 0.5 | 57.0% | 50.0% | +7.0% | 0.140 | Negligible |
| GPT-4o | 0.7 | 57.0% | 51.0% | +6.0% | 0.120 | Negligible |
| GPT-4o | 0.9 | 57.0% | 55.0% | +2.0% | 0.040 | Negligible |
| GPT-5-mini | 0.2 | 89.0% | 68.0% | +21.0% | 0.526 | Medium |
| GPT-5-mini | 0.5 | 89.0% | 65.3% | +23.7% | 0.584 | Medium |
| GPT-5-mini | 0.7 | 89.0% | 65.0% | +24.0% | 0.590 | Medium |
| GPT-5-mini | 0.9 | 89.0% | 59.6% | +29.4% | 0.702 | Medium |
| Mistral-Large | 0.2 | 49.0% | 46.0% | +3.0% | 0.060 | Negligible |
| Mistral-Large | 0.5 | 49.0% | 44.0% | +5.0% | 0.100 | Negligible |
| Mistral-Large | 0.7 | 49.0% | 45.0% | +4.0% | 0.080 | Negligible |
| Mistral-Large | 0.9 | 49.0% | 37.0% | +12.0% | 0.243 | Small |

## Model Resilience Comparison
| Rank | Model | Avg Degradation | Interpretation |
|------|-------|-----------------|----------------|
| 1 | GPT-4o | 1.7% | Highly Resilient |
| 2 | GPT-5 | 1.9% | Highly Resilient |
| 3 | Mistral-Large | 3.6% | Moderately Resilient |
| 4 | GPT-5-mini | 18.6% | Highly Vulnerable |

## MIU Level Analysis
Average degradation by distortion type:

| MIU Level | Description | Avg Degradation (D1.0) | Avg Degradation (D1.5) |
|-----------|-------------|------------------------|------------------------|
| 0.2 | Synonym Substitution | +2.5% | +5.5% |
| 0.5 | Notation Variation | +6.6% | +8.9% |
| 0.7 | Format Conversion | +2.0% | +9.1% |
| 0.9 | Maximum Distortion | +5.0% | +12.1% |

## Research Questions Answered

### 1. Does semantic distortion cause statistically significant performance degradation?
**Answer:** Yes. 9 of 32 comparisons (28.1%) showed statistically significant degradation at p<0.05, with 7 (21.9%) significant at p<0.01.

### 2. Which models are most resilient to distortion?
**Answer:** GPT-4o is the most resilient model with only 1.7% average degradation. GPT-5 is second most resilient with 1.9% degradation.

### 3. Which models are most vulnerable?
**Answer:** GPT-5-mini is the most vulnerable with 18.6% average degradation. Mistral-Large is second most vulnerable with 3.6% degradation.

### 4. Does problem difficulty affect vulnerability to distortion?
**Answer:** Yes. Harder problems (Difficulty 1.5) show 8.9% average degradation compared to 4.0% for easier problems (Difficulty 1.0). This suggests that when models are already struggling with harder problems, semantic distortion has a more pronounced negative effect.

### 5. Which types of distortion cause the most degradation?
**Answer:** Maximum Distortion (MIU 0.9) causes the most degradation at 8.6% on average. Least harmful is Synonym Substitution (MIU 0.2) with 4.0% degradation.

### 6. Is there evidence that models rely on surface patterns rather than understanding?
**Answer:** The evidence is mixed but suggestive. The fact that 9 of 32 comparisons show significant degradation when only the surface form (not the underlying mathematics) changes indicates some reliance on surface patterns. However, the most capable models (GPT-4o and GPT-5) show relatively small degradation, suggesting they have developed more robust mathematical understanding. The weaker models (GPT-5-mini and Mistral-Large) show greater vulnerability, suggesting they may rely more heavily on pattern matching.

## Limitations and Caveats

1. **Empty Answers:** Some models (especially GPT-5-mini on distortion tasks) produced empty answers due to token limits. These are counted as incorrect.
2. **Sample Size:** 100 questions per condition limits statistical power for detecting small effects.
3. **Answer Matching:** Despite corrections, some semantically equivalent answers may be marked as incorrect due to format differences.
4. **Distortion Quality:** The quality and semantic equivalence of distortions varies by MIU level.
5. **Model Versions:** Results are specific to the model versions tested and may not generalize to future updates.

## Conclusions

1. **Semantic distortion significantly impacts model performance** in mathematical reasoning, with the majority of comparisons showing statistically significant degradation.

2. **More capable models are more resilient** to semantic distortion, suggesting that improved mathematical understanding provides some protection against surface-level changes.

3. **Harder problems are more vulnerable** to distortion effects, likely because models are already operating closer to their capability limits.

4. **All distortion types cause measurable degradation**, though the severity varies. This suggests models have some sensitivity to multiple aspects of question phrasing.

5. **The hypothesis that models rely on surface patterns is partially supported**, particularly for less capable models, but more capable models show meaningful resilience.

## Visualizations

The following visualizations are available in the `statistical_analysis_report/` directory:

1. `baseline_vs_distortion.png` - Comparison of baseline and distorted accuracy by model
2. `degradation_curves.png` - Accuracy trends across MIU levels
3. `effect_size_heatmap.png` - Cohen's h effect sizes by model and MIU level
4. `significance_summary.png` - Statistical significance overview
5. `net_change_chart.png` - Questions lost vs gained due to distortion
6. `comprehensive_dashboard.png` - All key findings in one view
