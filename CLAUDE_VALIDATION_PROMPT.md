# Claude Validation Task - Model Answer Accuracy Assessment

## YOUR ROLE

You are an expert mathematical validator tasked with evaluating whether AI model answers are genuinely incorrect or if they were misclassified as "false" due to:
1. The distorted question legitimately requiring a different answer
2. Empty responses
3. Equivalent mathematical values in different string formats
4. Other issues caused by question distortion rather than model error

## CONTEXT

We tested an AI model (GPT-5) on mathematical questions with varying levels of distortion:
- **Baseline (miu 0.0)**: Original question, no distortion
- **miu 0.2**: Synonym Substitution (minimal distortion)
- **miu 0.5**: Notation Variation (moderate distortion)
- **miu 0.7**: Format Conversion (significant distortion)
- **miu 0.9**: Maximum Distortion (heavy linguistic changes)

## YOUR VALIDATION TASK

For each question, you will see:
1. **Original Question** - The baseline mathematical problem
2. **Ground Truth Answer** - The correct answer to the original question
3. **Model Answer on Baseline** - What the model answered for the undistorted question
4. **4 Distorted Questions** - Each with the model's answer

For EACH of the 5 answers (baseline + 4 distortions), you must:

### Classify the answer as ONE of these statuses:

1. **CORRECT** - The answer exactly matches the ground truth or is clearly correct for the question asked

2. **DISTORTION-CAUSED** - The answer differs from ground truth BUT is actually correct given the distorted question. Examples:
   - A distorted question changed names/values, and the model correctly used the distorted values
   - The distortion legitimately changed what should be calculated
   - The model correctly answered what was actually asked in the distorted version

3. **EMPTY** - No answer was provided (marked as `[EMPTY ANSWER]`)

4. **EQUIVALENT** - The answer is mathematically equivalent to the ground truth but in different string format:
   - "0.5" vs "1/2"
   - "199π" vs "199 \\pi" vs "199*pi"
   - "6.28318..." vs "2π"
   - Different but equivalent mathematical notations

5. **INCORRECT** - The model made a genuine mistake:
   - Wrong calculation
   - Wrong reasoning
   - Misunderstood the question (even accounting for distortion)
   - Any other actual error by the model

### Provide Reasoning

For each classification, provide 1-2 sentences explaining:
- What you compared
- Why you chose that status
- For DISTORTION-CAUSED: specifically what changed in the distortion that justified the different answer
- For EQUIVALENT: what makes them mathematically the same despite different notation

## CRITICAL RULES

1. **Read the distorted question carefully** - Don't just compare model answer to ground truth. Check if the distorted question legitimately changed what should be answered.

2. **Mathematical equivalence matters** - "3/4" and "0.75" are EQUIVALENT, not INCORRECT

3. **Be precise about DISTORTION-CAUSED** - Only use this status if the distortion actually changed what the correct answer should be (e.g., different numbers, different names that affect the answer)

4. **Empty answers are always EMPTY** - Don't classify them as INCORRECT

5. **Baseline should usually be CORRECT** - If the baseline (miu 0.0) is wrong, that's a genuine model error since there's no distortion

## OUTPUT FORMAT

For each question, provide your validation in this EXACT format:

```
Question [N] - [question_id]:
  Baseline (miu 0.0): [STATUS] - [REASONING]
  miu 0.2: [STATUS] - [REASONING]
  miu 0.5: [STATUS] - [REASONING]
  miu 0.7: [STATUS] - [REASONING]
  miu 0.9: [STATUS] - [REASONING]
```

After all questions, provide a summary:

```
VALIDATION SUMMARY FOR QUESTIONS [X] to [Y]:

STATISTICS:
- Total answers evaluated: [NUMBER]
- CORRECT: [NUMBER] ([PERCENTAGE]%)
- DISTORTION-CAUSED: [NUMBER] ([PERCENTAGE]%)
- EMPTY: [NUMBER] ([PERCENTAGE]%)
- EQUIVALENT: [NUMBER] ([PERCENTAGE]%)
- INCORRECT: [NUMBER] ([PERCENTAGE]%)

CRITICAL FINDINGS:
[List any patterns, systematic issues, or important observations about the model's performance]

QUESTIONS REQUIRING HUMAN REVIEW:
[List question IDs where you're uncertain about the classification and why]
```

## EXAMPLES OF GOOD VALIDATION

**Example 1 - EQUIVALENT:**
```
Question 5:
  Baseline (miu 0.0): EQUIVALENT - Model answered "199π" while ground truth is "199 \\pi". These are mathematically identical, just different notation for pi.
```

**Example 2 - DISTORTION-CAUSED:**
```
Question 12:
  miu 0.7: DISTORTION-CAUSED - Original question asked about "radius 100", but distorted question changed it to "radius 50". Model correctly answered "25π" for radius 50, even though ground truth for original question is "100π".
```

**Example 3 - INCORRECT:**
```
Question 8:
  Baseline (miu 0.0): INCORRECT - Model answered "42" but ground truth is "36". The question asked for product of 2, 3, 6 which is 36. Model made a calculation error.
```

**Example 4 - CORRECT:**
```
Question 3:
  miu 0.2: CORRECT - Model answered "40" matching ground truth exactly. The synonym substitution didn't affect the mathematical content.
```

## BEGIN VALIDATION

Review the document I'm providing and perform the validation task as described above. Be thorough, precise, and systematic in your analysis.

