# Token Limit Pattern Analysis - Overview

## Executive Summary

Out of **68 unique questions** that were flagged for having empty answer content, the analysis reveals distinct patterns of token limit issues across different MIU levels (baseline + 4 distortion levels).

## Key Findings

### Overall Pattern Distribution

- **Only Baseline Affected (MIU 0.0)**: 3 questions (4.4%)
  - These questions hit the token limit only on the original baseline question
  - Distorted versions (MIU 0.2, 0.5, 0.7, 0.9) did NOT hit the limit
  
- **Multiple MIU Levels Affected (2-4 levels)**: 13 questions (19.1%)
  - These questions hit the token limit at 2-4 out of 5 MIU levels
  - Shows partial vulnerability across distortion levels
  
- **All 5 MIU Levels Affected**: 52 questions (76.5%)
  - These questions hit the token limit at ALL levels: baseline (0.0) + all 4 distortions (0.2, 0.5, 0.7, 0.9)
  - Indicates these are inherently complex questions that require extensive reasoning regardless of distortion

## Detailed Breakdown

### 1. Questions with ONLY Baseline Token Limit Issues (3 questions)

These questions are particularly interesting because:
- The **original question** is complex enough to hit the 1500 token limit
- However, **distorted versions** (even at high MIU levels like 0.9) do NOT hit the limit
- This suggests the distortions may have simplified the problem or changed it in a way that requires less reasoning

**Examples:**
- Category 2, QID `73dbbd0fa393`: Only gpt-5 affected at baseline
- Category 2, QID `95930bcd8794`: Only gpt-5 affected at baseline  
- Category 3, QID `b75fd08116b0`: Both gpt-5 and gpt-5-mini affected at baseline

### 2. Questions with MULTIPLE MIU Levels Affected (13 questions)

These questions show **selective vulnerability** across distortion levels:

**Pattern Examples:**

- **Category 2, QID `13124d8a98a9`**:
  - gpt-5: Affected at MIU 0.0, 0.2, 0.5 (3/5 levels)
  - gpt-5-mini: Affected only at MIU 0.0 (1/5 levels)
  - Pattern: Lower MIU levels (0.0-0.5) are problematic, but higher distortions (0.7, 0.9) are fine

- **Category 2, QID `60d03456ebad`**:
  - gpt-5: Affected at MIU 0.0, 0.2, 0.5, 0.9 (4/5 levels)
  - gpt-5-mini: Affected only at MIU 0.5 (1/5 levels)
  - Pattern: Most levels problematic for gpt-5, but only one level for gpt-5-mini

- **Category 2, QID `d7197019328f`**:
  - gpt-5: Affected at MIU 0.0, 0.7 (2/5 levels)
  - gpt-5-mini: Affected at MIU 0.0, 0.9 (2/5 levels)
  - Pattern: Different MIU levels problematic for different models

**Key Observations:**
- Some questions are problematic at **lower MIU levels** (0.0-0.5) but fine at higher distortions
- Some questions are problematic at **higher MIU levels** (0.7-0.9) but fine at baseline
- **Model-specific patterns**: gpt-5 and gpt-5-mini often show different vulnerability patterns for the same question

### 3. Questions with ALL 5 MIU Levels Affected (52 questions - 76.5%)

This is the **largest category**, indicating that most flagged questions are inherently complex:

**Characteristics:**
- These questions hit the token limit regardless of distortion level
- The problem complexity is **intrinsic to the question**, not caused by distortion
- All 5 variations (baseline + 4 distortions) require extensive reasoning that exceeds 1500 tokens

**Examples:**
- Category 1, QID `ac9ffea90714`: Both gpt-5 and gpt-5-mini affected at all levels
- Category 1, QID `81cdc5c39160`: gpt-5 affected at all levels
- Category 2, QID `10a65b3d22a1`: Both models affected at all levels
- Category 3, QID `f3c7404f0a13`: Both models affected at all levels

## Model-Specific Patterns

### gpt-4_1
- **No flagged questions** - This model did not hit token limits for any of the flagged questions

### gpt-5
- **Only baseline**: 3 questions
- **Multiple levels**: 13 questions  
- **All 5 levels**: 52 questions
- **Total**: 68 unique questions affected

### gpt-5-mini
- **Only baseline**: 9 questions
- **Multiple levels**: 25 questions
- **All 5 levels**: 26 questions
- **Total**: 60 unique questions affected

**Key Insight**: gpt-5-mini shows more variability (more questions with partial MIU level issues), while gpt-5 tends to hit limits more consistently across all levels.

## Implications

### 1. Question Complexity
- **76.5% of flagged questions** hit limits at ALL distortion levels
- This suggests these questions are fundamentally complex and require more than 1500 tokens regardless of how they're phrased

### 2. Distortion Effects
- **Only 4.4%** of questions hit limits only at baseline
- This suggests that distortions rarely simplify problems enough to avoid token limits
- In fact, distortions may sometimes make problems harder (as seen in the "multiple levels" category)

### 3. Model Behavior
- **gpt-5** shows more consistent behavior (all-or-nothing pattern)
- **gpt-5-mini** shows more variability (partial MIU level issues)
- **gpt-4_1** handles these questions without hitting limits

### 4. Recommendations
- Questions hitting limits at **all 5 levels** likely need:
  - Higher token limits (e.g., 2000-3000 tokens)
  - Or alternative evaluation approaches
  
- Questions hitting limits at **only baseline** may benefit from:
  - Using distorted versions for evaluation
  - Investigating why distortions reduce complexity
  
- Questions with **selective MIU level issues** suggest:
  - Some distortion types may increase complexity
  - Model-specific sensitivity to certain distortion patterns

## Conclusion

The analysis reveals that **most flagged questions (76.5%) hit token limits across all MIU levels**, indicating intrinsic complexity rather than distortion-induced issues. Only a small fraction (4.4%) hit limits only at baseline, suggesting that distortions rarely simplify problems enough to avoid token limits. The pattern suggests these questions fundamentally require more reasoning capacity than the 1500 token limit allows.

