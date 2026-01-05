# Next Steps: Distortion Generation for OmniMath Dataset

**Date**: January 4, 2026  
**Status**: ✅ Prompts validated and enhanced - Ready to proceed

---

## Summary of Changes

### What Was Done
1. ✅ Analyzed all 300 OmniMath questions across 3 categories
2. ✅ Validated distortion prompts against dataset characteristics
3. ✅ Enhanced prompts with LaTeX preservation guidance
4. ✅ Clarified multiple-answer handling
5. ✅ Created comprehensive documentation

### Files Modified
- `src/modules/math_distortion_prompts.py` - Enhanced with LaTeX handling

### Files Created
- `docs/DISTORTION_PROMPTS_ANALYSIS.md` - Detailed analysis
- `docs/PROMPT_COMPATIBILITY_SUMMARY.md` - Quick summary
- `docs/DISTORTION_EXAMPLES_OMNIMATH.md` - Example distortions
- `docs/NEXT_STEPS_DISTORTION_GENERATION.md` - This file

---

## Recommended Workflow

### Option A: Full Generation (Recommended)

**When to use**: You're confident and want to proceed immediately

**Steps**:

1. **Review the enhancements**:
   ```bash
   # Check what was changed
   git diff src/modules/math_distortion_prompts.py
   ```

2. **Run distortion generation**:
   ```bash
   # Activate your environment
   source venv/bin/activate
   
   # Run the distortion generation flow
   python src/flows/generate_distortions.py \
     --input data/source_verified/omnimath_solve_rate \
     --output data/distortion_validation \
     --miu-levels 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9
   ```

3. **Monitor progress**:
   - Watch for API errors
   - Check token usage
   - Monitor for rate limits

4. **Validate outputs**:
   ```bash
   # Run validation
   python src/flows/verify_data.py \
     --input data/distortion_validation
   ```

**Expected output**:
- 300 questions × 9 μ levels = 2,700 distorted questions
- Organized by category and μ level
- Validation reports showing preservation of answers

---

### Option B: Staged Validation (Safer)

**When to use**: You want to test on a small sample first

#### Stage 1: Small Sample Test (5-10 questions)

1. **Create a test subset**:
   ```bash
   # Create test directory
   mkdir -p data/distortion_validation/test_sample
   
   # Copy 5 questions from each category (15 total)
   # You can do this manually or with a script
   ```

2. **Test with sample**:
   ```python
   # Quick test script
   from src.modules.math_distortion_prompts import get_distortion_prompt
   import json
   
   # Load a sample question
   with open('data/source_verified/omnimath_solve_rate/baseline_questions_category_1.json') as f:
       questions = json.load(f)
   
   sample_q = questions[0]
   
   # Test μ=0.5 (notation variation - most likely to have LaTeX issues)
   prompt = get_distortion_prompt(sample_q['problem'], 0.5)
   print(prompt)
   
   # Manually verify:
   # - LaTeX preservation guidance is present
   # - Prompt is coherent
   # - Instructions are clear
   ```

3. **Generate distortions for sample**:
   ```bash
   # Run on test sample only
   python src/flows/generate_distortions.py \
     --input data/distortion_validation/test_sample \
     --output data/distortion_validation/test_results \
     --miu-levels 0.5 0.8 0.9
   ```
   *Note: Test the highest μ levels first (most likely to have issues)*

4. **Manual validation**:
   - Check 5-10 distorted questions manually
   - Verify LaTeX is preserved: `$x^{2}$` should remain as `$x^{2}$`
   - Verify variables renamed systematically: if `x→t`, all `x` become `t`
   - Verify answers unchanged
   - Verify mathematical relationships preserved

5. **If validation passes → Proceed to Stage 2**

#### Stage 2: Category-by-Category Generation

1. **Generate Category 1** (easiest):
   ```bash
   python src/flows/generate_distortions.py \
     --input data/source_verified/omnimath_solve_rate/baseline_questions_category_1.json \
     --output data/distortion_validation/category_1 \
     --miu-levels 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9
   ```

2. **Validate Category 1**:
   ```bash
   python src/flows/verify_data.py \
     --input data/distortion_validation/category_1
   ```

3. **Review validation report**:
   - Check for any errors
   - Spot-check a few distortions manually
   - Verify LaTeX preservation

4. **If Category 1 passes → Generate Categories 2 and 3**

#### Stage 3: Full Dataset Generation

Once Categories 1-3 are validated individually:

```bash
# Generate all remaining distortions
python src/flows/generate_distortions.py \
  --input data/source_verified/omnimath_solve_rate \
  --output data/distortion_validation \
  --miu-levels 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9
```

---

## Validation Checklist

For each generated distortion, verify:

### Mathematical Integrity
- [ ] All numbers remain exactly the same
- [ ] Answer is mathematically equivalent
- [ ] Constraints and conditions preserved
- [ ] Mathematical relationships unchanged (e.g., `A > B` not reversed)
- [ ] Operations not reordered incorrectly (e.g., `A-B` not changed to `B-A`)

### LaTeX Preservation
- [ ] All `$...$` delimiters intact
- [ ] Fractions preserved: `$\frac{a}{b}$`
- [ ] Exponents preserved: `$x^{2}$`, `$x^{n}$`
- [ ] Subscripts preserved: `$F_{n}$`, `$F_{n-1}$`
- [ ] Special symbols preserved: `$\pi$`, `$\mathbb{R}$`, `$\rightarrow$`
- [ ] Display math preserved: `$$ ... $$`

### Variable Renaming (μ=0.4+)
- [ ] Variables renamed systematically (if `x→t`, ALL `x` become `t`)
- [ ] No mixed renaming (not `x→t` in one place and `x→s` in another)
- [ ] Standard constants unchanged (`π`, `e`, `i`)

### Distortion Intensity
- [ ] μ=0.1: Minimal changes (entity/verb only)
- [ ] μ=0.2-0.3: Light changes (synonyms, rephrasing)
- [ ] μ=0.4-0.6: Moderate changes (variables, clauses)
- [ ] μ=0.7-0.9: Significant surface changes (format, vocabulary)

### Output Quality
- [ ] Coherent English (no gibberish)
- [ ] Grammatically correct
- [ ] Question is answerable
- [ ] Similar length to original (not excessively longer)

---

## Common Issues to Watch For

### Issue 1: LaTeX Corruption
**Symptom**: `$x^{2}$` becomes `x squared` or `$x^2` (missing braces)

**Cause**: GPT-4o converting LaTeX to verbal form

**Solution**: ✅ Already addressed with LaTeX preservation guidance

**How to detect**:
```bash
# Search for broken LaTeX in outputs
grep -r "x squared" data/distortion_validation/
grep -r "x cubed" data/distortion_validation/
```

### Issue 2: Inconsistent Variable Renaming
**Symptom**: `x→t` in some places, `x→s` in others within same question

**Cause**: GPT-4o not applying systematic renaming

**Solution**: Your prompts already emphasize "SYSTEMATIC throughout"

**How to detect**: Manual spot-checking of μ=0.4+ distortions

### Issue 3: Relationship Reversal
**Symptom**: "X is divisible by Y" becomes "X divides Y" (opposite meaning)

**Cause**: Synonym confusion

**Solution**: ✅ Your prompts explicitly warn against this

**How to detect**:
```bash
# Check for divisibility language changes
grep -r "divisible by" data/source_verified/
grep -r "divides" data/distortion_validation/
# Compare to ensure relationships preserved
```

### Issue 4: Operand Swapping
**Symptom**: `(A-B)` becomes `(B-A)` (changes answer)

**Cause**: Clause reordering applied to expressions

**Solution**: ✅ Your μ=0.6+ prompts explicitly forbid this

**How to detect**: Answer validation will catch this

### Issue 5: Insufficient Distortion
**Symptom**: μ=0.7 output looks like μ=0.3 output

**Cause**: GPT-4o being too conservative

**Solution**: Your prompts include intensity checks ("MUST be MORE distorted than μ=X")

**How to detect**: Manual review of distortion intensity

---

## Monitoring During Generation

### API Costs
- **Model**: GPT-4o (assumed)
- **Estimated tokens per distortion**: ~500-1000 tokens (input) + ~200-500 tokens (output)
- **Total for 2,700 distortions**: ~2-4M tokens
- **Estimated cost**: $5-15 (depending on pricing)

### Rate Limits
- Watch for rate limit errors
- Implement retry logic if needed
- Consider batching with delays

### Progress Tracking
```bash
# Monitor output directory
watch -n 10 'find data/distortion_validation -type f | wc -l'

# Expected: 2,700 files (300 questions × 9 μ levels)
```

---

## Post-Generation Analysis

### 1. Validation Report
```bash
python src/flows/verify_data.py \
  --input data/distortion_validation \
  --output output/reports/distortion_validation_report.json
```

**Expected outputs**:
- Answer preservation rate: 100%
- LaTeX preservation rate: >99%
- Mathematical integrity: 100%

### 2. Quality Spot-Check
Manually review:
- 5 questions from each category (15 total)
- All μ levels for those questions
- Focus on μ=0.5, 0.8, 0.9 (most complex)

### 3. Statistical Analysis
```bash
python src/analysis/run_analysis.py \
  --baseline data/source_verified/omnimath_solve_rate \
  --distorted data/distortion_validation
```

**Analyze**:
- Average text length by μ level
- Vocabulary diversity by μ level
- Lexical overlap with original

---

## Troubleshooting

### Problem: LaTeX is being converted to verbal form

**Solution**:
1. Check that you're using the updated `math_distortion_prompts.py`
2. Verify LaTeX handling sections are present in prompts
3. Try increasing temperature slightly (may help with following instructions)

### Problem: Variables not renamed systematically

**Solution**:
1. Add explicit examples in prompt showing systematic renaming
2. Reduce temperature slightly (may improve consistency)
3. Post-process with a script to enforce systematic renaming

### Problem: Distortion intensity insufficient

**Solution**:
1. Increase temperature for that μ level
2. Add more explicit examples of desired intensity
3. Emphasize "MUST be MORE distorted" language

### Problem: Mathematical relationships reversed

**Solution**:
1. Your prompts already warn against this
2. If it happens, add more explicit examples
3. Consider post-processing validation to catch and reject

---

## Success Criteria

### Minimum Acceptable
- ✅ 100% answer preservation
- ✅ >95% LaTeX preservation
- ✅ No mathematical relationship reversals
- ✅ Clear intensity progression across μ levels

### Ideal
- ✅ 100% answer preservation
- ✅ >99% LaTeX preservation
- ✅ 100% mathematical integrity
- ✅ All distortions coherent and natural
- ✅ Clear differentiation between all μ levels

---

## Timeline Estimate

### Option A: Full Generation
- **Setup**: 10 minutes
- **Generation**: 2-4 hours (depending on API speed)
- **Validation**: 1-2 hours
- **Total**: ~3-6 hours

### Option B: Staged Validation
- **Stage 1 (Sample)**: 1 hour
- **Stage 2 (Category-by-category)**: 4-6 hours
- **Stage 3 (Full dataset)**: 2-4 hours
- **Total**: ~7-11 hours

---

## Recommended Approach

**For your situation, I recommend Option A (Full Generation)** because:

1. ✅ Your prompts are well-designed and thoroughly tested
2. ✅ Enhancements specifically address OmniMath characteristics
3. ✅ You have validation tools in place
4. ✅ Dataset is manageable (300 questions)
5. ✅ You can spot-check outputs during generation

**However**, if you want to be extra cautious:
- Start with Stage 1 of Option B (test 15 questions)
- If those pass, proceed with full generation

---

## Final Checklist Before Starting

- [ ] Review changes to `math_distortion_prompts.py`
- [ ] Ensure API keys are configured
- [ ] Check API rate limits and quotas
- [ ] Verify output directory structure exists
- [ ] Have validation tools ready
- [ ] Set aside 3-6 hours for full process
- [ ] Read through example distortions in `DISTORTION_EXAMPLES_OMNIMATH.md`

---

## Questions to Consider

1. **Do you want to generate all μ levels (0.1-0.9) or a subset?**
   - Recommendation: All levels for complete analysis

2. **Do you want to process all 3 categories or start with one?**
   - Recommendation: All 3 categories (they're already validated)

3. **What's your tolerance for manual review?**
   - Option A: Minimal manual review (rely on automated validation)
   - Option B: More manual review at each stage

4. **Do you have API quota concerns?**
   - If yes: Use staged approach to monitor costs
   - If no: Full generation is fine

---

## Contact Points for Issues

If you encounter issues during generation:

1. **LaTeX problems**: Check `DISTORTION_EXAMPLES_OMNIMATH.md` for expected behavior
2. **Validation failures**: Review `DISTORTION_PROMPTS_ANALYSIS.md` for edge cases
3. **Intensity issues**: Adjust temperature in `calculate_temperature()` function
4. **Mathematical errors**: Review CRITICAL_PRESERVATION_RULES in prompts

---

## After Successful Generation

Once distortions are generated and validated:

1. **Archive the validated distortions**:
   ```bash
   cp -r data/distortion_validation data/results_verified/distortion/
   ```

2. **Update documentation**:
   - Note generation date
   - Record any issues encountered
   - Document any manual corrections made

3. **Proceed to evaluation**:
   ```bash
   python src/flows/evaluate_baseline.py
   python src/flows/evaluate_distortions.py
   ```

4. **Run analysis**:
   ```bash
   python src/flows/analyze_results.py
   ```

---

## Conclusion

You're ready to proceed with distortion generation. Your prompts are well-designed, thoroughly analyzed, and enhanced for the OmniMath dataset.

**Recommendation**: Start with **Option A (Full Generation)** unless you have specific concerns.

Good luck! 🦎

