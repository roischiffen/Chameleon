# How to Use the Validation Document

## What Was Created

✅ **File**: `prompts/CATEGORY_3_VALIDATION_FOR_CLAUDE.md`  
✅ **Size**: ~61,000 characters (fits in Claude's context)  
✅ **Content**: 34 questions × 4 μ levels = 136 distortions  
✅ **Category**: 3 (Harder questions, 20% solve rate)

---

## How to Use It

### Step 1: Open the File
```bash
open prompts/CATEGORY_3_VALIDATION_FOR_CLAUDE.md
```

Or in your editor:
```bash
code prompts/CATEGORY_3_VALIDATION_FOR_CLAUDE.md
```

### Step 2: Copy ALL Content
- Select all (Cmd+A / Ctrl+A)
- Copy (Cmd+C / Ctrl+C)

### Step 3: Send to Claude
1. Open Claude (claude.ai or API)
2. Paste the entire content
3. Send the message
4. Wait for validation results

---

## What Claude Will Do

Claude will:
1. ✅ Review all 136 distortions (34 questions × 4 μ levels)
2. ✅ Check mathematical preservation
3. ✅ Identify any invalid distortions
4. ✅ Report ONLY problems (not valid variations)

---

## Expected Response

### If Everything is Valid:
```
✅ All 136 distortions (34 questions × 4 μ levels) are VALID.
```

### If There Are Issues:
```
❌ Question ID: abc123
μ Level: 0.9
Issue: Changed numerical value

Baseline: Find 2^41
Distorted: Find 3^41
Answer: 13
Why Invalid: Changed the base from 2 to 3, which gives a different answer.
---

❌ Question ID: xyz789
μ Level: 0.7
Issue: Changed mathematical notation
...
```

---

## What to Look For in Results

### ✅ Valid (Claude should NOT report these):
- Name changes: Luxmi→Kiran
- Label changes: A,B,C→P,Q,R (if systematic)
- Variable renaming: F→G (if systematic)
- Synonyms: "find"→"determine"
- Format: prose→bullets

### ❌ Invalid (Claude SHOULD report these):
- Changed numbers: 2^41→3^41
- Changed symbols: π→p×i
- Inconsistent renaming: x→t, then x→s
- Broke patterns: Lost shared vertices
- Added/removed constraints

---

## After Validation

### If 0-2 Errors Found:
✅ **Excellent!** The distortions are high quality.
- Note the errors for manual correction
- Proceed with evaluation

### If 3-5 Errors Found:
⚠️ **Good, but needs attention**
- Review the flagged distortions
- Decide if they need regeneration
- Most can likely be manually corrected

### If 6+ Errors Found:
❌ **Needs investigation**
- Review the validation criteria with Claude
- Check if false positives (name changes flagged incorrectly)
- May need to regenerate some distortions

---

## Regenerating for Other Categories

To create validation documents for Categories 1 or 2:

### Edit the Script:
```python
# In create_validation_document.py, change:
INPUT_FILE = Path("data/distortion_validation/category_1/distortions_20260105_000210.json")
OUTPUT_FILE = Path("prompts/CATEGORY_1_VALIDATION_FOR_CLAUDE.md")
```

### Run Again:
```bash
python3 create_validation_document.py
```

---

## Quick Stats

- **Category 3**: 100 questions total
- **Validating**: First 34 questions (34%)
- **Distortions per question**: 4 (μ=0.2, 0.5, 0.7, 0.9)
- **Total validating**: 136 distortions
- **Remaining**: 66 questions (264 distortions) can be validated later

---

## File Locations

```
prompts/
├── CATEGORY_3_VALIDATION_FOR_CLAUDE.md  ← Send this to Claude
├── DISTORTION_VALIDATION_PROMPT.md      ← General validation prompt
├── VALIDATOR_CORRECTION_MESSAGE.md      ← Correction guide
└── VALIDATION_QUICK_REFERENCE.md        ← Quick reference card
```

---

## Next Steps

1. ✅ Copy `CATEGORY_3_VALIDATION_FOR_CLAUDE.md`
2. ✅ Send to Claude
3. ✅ Review results
4. ✅ Address any flagged issues
5. ✅ Repeat for remaining 66 questions if needed
6. ✅ Proceed with evaluation once validated

---

**Ready to validate!** Just copy and paste the file content to Claude. 🦎

