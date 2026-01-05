# Distortion Validation Task

I need you to validate mathematical question distortions to ensure they preserve the original mathematical meaning and answer.

## Your Task

Review the distortions in `data/distortion_validation/category_1/distortions_20260105_000210.json` and identify any distortions that **failed to preserve the mathematical question**.

## Validation Criteria

A distortion is **INVALID** if:

1. **Changed numerical values** - Any number is different (e.g., 2^41 → 3^41, 8 balls → 6 balls)
2. **Changed mathematical notation meaning** - Corrupted math symbols (e.g., π → p×i, which changes pi to "p times imaginary unit")
3. **Changed what is being asked** - Question asks for something different (e.g., "find area" → "find perimeter")
4. **Added or removed constraints** - Changed conditions that affect the solution
5. **Reversed mathematical relationships** - Changed inequalities, divisibility direction, or operand order (e.g., A>B → B>A, "divisible by" → "divides")
6. **Broke LaTeX syntax** - Corrupted mathematical notation (e.g., `$x^{2}$` → `x squared` or broken/missing delimiters)
7. **Inconsistent variable/label renaming** - Variables renamed differently in same problem (e.g., x→t in one place, x→s in another)
8. **Broke geometric relationships** - Label renaming that breaks shared vertices or structural patterns
9. **Added interpretation not in original** - Added explanations or descriptions that change the problem's meaning
10. **Made the question unsolvable** - Missing information or contradictory constraints

A distortion is **VALID** if:
- The mathematical meaning is identical
- The correct answer remains the same
- All constraints are preserved
- Only surface-level wording changed (synonyms, sentence structure, format)
- LaTeX notation is intact (variables may be renamed systematically)

## Output Format

**Only report INVALID distortions.** For each invalid distortion, provide:

```
❌ Question ID: [question_id]
μ Level: [miu_level]
Issue: [Brief description of what went wrong]

Baseline:
[original_problem]

Distorted:
[distorted_problem]

Expected Answer: [answer]
Why Invalid: [Specific explanation of the mathematical error]

---
```

## Example of What to Report

```
❌ Question ID: abc123
μ Level: 0.7
Issue: Changed what is being asked

Baseline:
Find the area of a circle with radius 5.

Distorted:
Find the circumference of a circle with radius 5.

Expected Answer: 25π
Why Invalid: Changed from asking for area to asking for circumference, which would give answer 10π instead of 25π.

---
```

## What NOT to Report

Do NOT report distortions that are valid but just look different, such as:
- **Synonym changes**: "find" → "determine", "calculate" → "compute"
- **Variable renaming**: x → t (if done systematically throughout)
- **Entity/name replacement**: Luxmi → Kiran, Grace → Isabella, Carrie → Christina
  - This is a CORE FEATURE of distortion (μ=0.1, 0.4, 0.9)
  - Names are entities, not mathematical values
  - As long as the same person is referenced consistently, it's valid
- **Geometric label renaming**: Triangle ABC → Triangle PQR, Points A,B,C,D → P,Q,R,S
  - MUST be systematic: if A→P, then ALL instances of A become P
  - Check that relationships are preserved (e.g., if triangles share vertex C, all should share the renamed vertex)
- **Format changes**: prose → structured bullets
- **Sentence reordering**: (if logical dependencies preserved)
- **Creative vocabulary at μ=0.9**: "triangle" → "three-sided polygon", "circle" → "circular region"

## Instructions

1. Load the file: `data/distortion_validation/category_2/distortions_20260105_002035.json`
2. Review all 100 questions × 4 μ levels = 400 distortions
3. For each distortion, check if it preserves mathematical meaning
4. Report ONLY the invalid ones using the format above
5. If all distortions are valid, respond: "✅ All 400 distortions in Category 1 are valid."

## Focus Areas

Pay special attention to:
- **LaTeX preservation**: Check that `$...$` notation is intact and symbols unchanged (π stays π, not p×i)
- **Number preservation**: Every number must be exactly the same
- **Relationship preservation**: "X divisible by Y" ≠ "X divides Y"
- **Operand order**: (A-B) ≠ (B-A), (A÷B) ≠ (B÷A)
- **Constraint preservation**: All "if", "given", "such that" conditions must be equivalent
- **Systematic renaming**: If x→t, then ALL x must become t (check consistency)
- **Geometric patterns**: If triangles share vertices, renaming must preserve this (ABC, ACD, ADE all share A)

## Common False Positives (DO NOT REPORT)

These are VALID distortions, not errors:
- ❌ "Changed name from Luxmi to Kiran" → ✅ This is entity replacement (valid)
- ❌ "Changed labels A,B,C to P,Q,R" → ✅ This is systematic renaming (valid if consistent)
- ❌ "Changed 'find' to 'determine'" → ✅ This is synonym substitution (valid)
- ❌ "Changed format from prose to bullets" → ✅ This is format conversion (valid)

Begin your validation now.

