# Distortion Validation - Quick Reference Card

## ✅ VALID Distortions (DO NOT FLAG)

| Type | Example | Why Valid |
|------|---------|-----------|
| **Name changes** | Luxmi → Kiran | Entity replacement (μ=0.1, 0.4, 0.9) |
| **Systematic labels** | A,B,C,D → P,Q,R,S | Geometric renaming (μ=0.4) |
| **Synonyms** | "find" → "determine" | Synonym substitution (μ=0.2) |
| **Format** | Prose → bullets | Format conversion (μ=0.7) |
| **Creative vocab** | "triangle" → "three-sided polygon" | Maximum distortion (μ=0.9) |
| **Variable rename** | x → t (everywhere) | Variable renaming (μ=0.4) |

---

## ❌ INVALID Distortions (FLAG THESE)

| Type | Example | Why Invalid |
|------|---------|-------------|
| **Changed numbers** | 2^41 → 3^41 | Different answer |
| **Changed math symbols** | π → p×i | Different meaning |
| **Inconsistent rename** | x→t, then x→s | Breaks consistency |
| **Broke patterns** | ABC, ACD → XYZ, PQR | Lost shared vertices |
| **Added constraints** | Added conditions | Changes problem |
| **Changed question** | area → perimeter | Different answer |
| **Reversed relations** | A>B → B>A | Opposite meaning |
| **Broke LaTeX** | $x^{2}$ → x squared | Lost notation |

---

## 🔍 How to Check

### Name/Entity Changes
```
✅ VALID:   "Luxmi forgot" → "Kiran forgot"
❌ INVALID: "Luxmi forgot" → "Luxmi remembered"
```

### Systematic Renaming
```
✅ VALID:   A→P, B→Q, C→R, D→S (all consistent)
❌ INVALID: A→P, B→Q, C→R, D→P (D conflicts with A)
```

### Numbers
```
✅ VALID:   "8 red balls" → "8 crimson spheres"
❌ INVALID: "8 red balls" → "6 red balls"
```

### Mathematical Notation
```
✅ VALID:   π → π (preserved)
❌ INVALID: π → p×i (changed meaning)
```

---

## 🎯 Decision Tree

```
Is a number different? 
  YES → ❌ INVALID
  NO  → Continue

Is a math symbol changed (π→p×i)?
  YES → ❌ INVALID  
  NO  → Continue

Is it a name change (Luxmi→Kiran)?
  YES → ✅ VALID (entity replacement)
  NO  → Continue

Is it systematic label change (A,B,C→P,Q,R)?
  YES → Check consistency
    Consistent? → ✅ VALID
    Inconsistent? → ❌ INVALID
  NO  → Continue

Is it a synonym (find→determine)?
  YES → ✅ VALID
  NO  → Continue

Does it change what's asked (area→perimeter)?
  YES → ❌ INVALID
  NO  → ✅ VALID
```

---

## 📊 Expected Results

**Category 1, 2, 3 (100 questions × 4 μ levels each):**
- **Expected valid**: 395-398 out of 400 (99%+)
- **Expected invalid**: 2-5 actual errors
- **Common false positives**: 8-10 name changes (these are valid!)

---

## 💡 Key Insight

**Entity replacement is a FEATURE, not a bug!**

The distortion framework is designed to:
1. Change surface features (names, labels, synonyms, format)
2. Preserve mathematical meaning (numbers, relationships, constraints)

If the answer stays the same and the math is equivalent, it's valid.

