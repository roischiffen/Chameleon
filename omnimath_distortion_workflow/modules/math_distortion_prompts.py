"""
🦎 Chameleon Framework - Mathematical Question Distortion Prompts
================================================================

Optimized prompts for GPT-4o to generate mathematically-preserving distortions
at 10 different μ (miu) intensity levels.

Each prompt is designed to:
1. Apply specific distortion techniques appropriate for that μ level
2. Preserve mathematical meaning and correctness ABSOLUTELY
3. Ensure the correct answer remains EXACTLY the same
4. Work across all mathematical domains (Algebra, Geometry, Number Theory, etc.)

Author: Chameleon Framework
"""

import math
from typing import Dict, Optional

# =============================================================================
# TEMPERATURE CALCULATION
# =============================================================================

def calculate_temperature(miu: float) -> float:
    """
    GPT-4o optimized temperature scaling (stable version).
    
    This formula is specifically tuned for GPT-4o which becomes unstable
    at temperatures above ~1.4. Balances creative distortion with mathematical
    accuracy to avoid computation errors in generated outputs.
    
    Design principles:
    1. Safe range: [0.5, 1.30] - creative but mathematically accurate
    2. Exponential curve (μ^1.3) for smooth differentiation
    3. Clear separation between all μ levels
    4. Maximum at μ=0.9 → 1.22 (safe for complex math questions)
    
    Temperature mapping:
        μ=0.0 → 0.0 (baseline, no generation)
        μ=0.1 → 0.54    μ=0.6 → 0.93
        μ=0.2 → 0.60    μ=0.7 → 1.03
        μ=0.3 → 0.67    μ=0.8 → 1.12
        μ=0.4 → 0.75    μ=0.9 → 1.22
        μ=0.5 → 0.84
    
    Args:
        miu: Distortion intensity (0.0 to 0.9)
        
    Returns:
        Temperature value (0.0 for baseline, 0.5-1.30 for distortions)
    """
    if miu == 0.0:
        return 0.0  # Baseline - no generation needed
    
    # GPT-4o safe temperature bounds (stable version - avoids math errors)
    MIN_TEMP = 0.5
    MAX_TEMP = 1.30
    
    # Exponential scaling: μ^1.3 provides smooth curve
    # that compresses high values while maintaining differentiation
    scale_factor = miu ** 1.3
    
    # Map to safe temperature range
    temperature = MIN_TEMP + scale_factor * (MAX_TEMP - MIN_TEMP)
    
    return round(temperature, 2)


# =============================================================================
# CRITICAL PRESERVATION RULES (Included in ALL prompts)
# =============================================================================

CRITICAL_PRESERVATION_RULES = """
## ⚠️ TWO ABSOLUTE REQUIREMENTS ⚠️

### 1. SAME MATHEMATICAL ANSWER
The distorted question MUST have the EXACT SAME numerical/mathematical answer as the original.
- All numbers must remain exactly the same
- All mathematical expressions must be equivalent
- The solution method may look different, but the answer is identical

### 2. SAME MATHEMATICAL MEANING
The distorted question must ask for the SAME thing mathematically.
- Preserve all conditions and constraints
- Preserve mathematical relationships (A > B must not become B > A)
- Preserve divisibility direction ("X divisible by Y" ≠ "X divides Y")
- Preserve operation order in expressions ((A-B) ≠ (B-A) unless commutative)

### WHAT'S ENCOURAGED (Surface Confusion):
✓ Creative vocabulary that confuses pattern-matching
✓ Unusual phrasing and sentence structures
✓ Different notation (symbolic ↔ verbal)
✓ Reordering sentences (not operands!)
✓ Renaming variables/entities systematically

### WHAT'S FORBIDDEN (Changes the Math):
❌ Changing any number
❌ Swapping non-commutative operands: (A-B) → (B-A)
❌ Reversing relationships: "divisible by" ↔ "divides"
❌ Adding or removing conditions
❌ Changing what the question asks for
"""

# =============================================================================
# μ-LEVEL SPECIFIC PROMPTS
# =============================================================================

MATH_DISTORTION_PROMPTS: Dict[float, str] = {
    
    # =========================================================================
    # μ = 0.1: ENTITY NAME REPLACEMENT
    # =========================================================================
    0.1: f"""You are an expert mathematical question paraphraser applying μ=0.1 distortion level.

## DISTORTION TYPE: ENTITY NAME REPLACEMENT (Lightest distortion)

This is the LIGHTEST form of distortion. Apply minimal changes while ensuring output differs from input.

### PRIMARY CHANGES (If entities exist):
✓ Person names: Alice → Bob, Josh → Maria, Ed → Carlos
✓ Set labels: Set S → Set T, Set A → Set B
✓ Point labels in geometry: Triangle ABC → Triangle PQR (systematic)
✓ Geometric object names: Circle Γ → Circle Ω
✓ Graph/tournament labels: Graph G → Graph H

### IF NO NAMED ENTITIES EXIST:
When the question has no people, places, or named objects, apply these minimal changes:
✓ Add context framing: "What is..." → "Determine what..."
✓ Minimal verb change: "Find" → "Calculate" or "Compute"
✓ Question restructure: "What is X?" → "X equals what?"

### EXAMPLES:

**WITH ENTITIES:**
Original: "Alice has 5 apples. How many does she have?"
Distorted: "Maria has 5 apples. How many does she have?"

**GEOMETRY WITH LABELS:**
Original: "In triangle ABC, if AB = 5, find AC."
Distorted: "In triangle PQR, if PQ = 5, find PR."

**NO ENTITIES (Pure Math):**
Original: "What is the value of 3x + 2 when x = 5?"
Distorted: "Calculate the value of 3x + 2 when x = 5."

**NO ENTITIES (Expression):**
Original: "Find the sum of 1 + 2 + 3 + ... + 100."
Distorted: "Compute the sum of 1 + 2 + 3 + ... + 100."

Note: This is μ=0.1 - the output SHOULD be very similar to the input. Only minimal changes are expected.

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.1 ENTITY NAME REPLACEMENT to the following problem.
The output should be SLIGHTLY different from input (this is the lightest distortion level).

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.2: SYNONYM SUBSTITUTION
    # =========================================================================
    0.2: f"""You are an expert mathematical question paraphraser applying μ=0.2 distortion level.

## DISTORTION TYPE: SYNONYM SUBSTITUTION

Replace mathematical verbs and common phrases with equivalent synonyms.

### SYNONYM REPLACEMENT TABLE:
| Original | → | Replacement Options |
|----------|---|---------------------|
| find | → | determine, compute, calculate, obtain |
| prove | → | show, demonstrate, establish, verify |
| show | → | prove, demonstrate, establish |
| calculate | → | compute, evaluate, find, determine |
| exists | → | there exists, there is, one can find |
| such that | → | satisfying, where, with the property that, for which |
| for all | → | for every, for each, for any |
| for every | → | for all, for each, for any |
| divides | → | is a divisor of, is a factor of, evenly divides |
| is divisible by | → | is a multiple of, is evenly divided by |
| greater than | → | larger than, exceeds, is more than |
| less than | → | smaller than, is below, is under |
| given | → | suppose, let, assuming, consider |
| consider | → | take, let, suppose |
| denote | → | let, call, represent by |
| if and only if | → | precisely when, exactly when, iff |

### ⚠️ CRITICAL SYNONYM TRAP - NEVER CONFUSE:
"X is divisible by Y" = "X is a multiple of Y" = "Y divides X" (Y | X)
"X is a divisor of Y" = "X divides Y" = "Y is divisible by X" (X | Y)
These are OPPOSITE relationships! NEVER swap "is divisible by" with "is a divisor of"!

### WHAT TO PRESERVE EXACTLY:
✗ ALL numbers and numerical values
✗ ALL variables and mathematical symbols
✗ Mathematical terminology (triangle, prime, integer, matrix, polynomial)
✗ ALL mathematical operations and relationships
✗ ALL constraints

### EXAMPLES ACROSS DOMAINS:

**ALGEBRA EXAMPLE:**
Original: "Find all real solutions x such that x³ - 2x² + x = 0."
Distorted: "Determine every real solution x satisfying x³ - 2x² + x = 0."

**GEOMETRY EXAMPLE:**
Original: "Prove that in triangle ABC with AB = AC, the altitude from A bisects BC."
Distorted: "Show that in triangle ABC where AB = AC, the altitude from A bisects BC."

**NUMBER THEORY EXAMPLE:**
Original: "Prove that for all integers n ≥ 1, if n divides 100, then n ≤ 100."
Distorted: "Demonstrate that for every integer n ≥ 1, if n is a factor of 100, then n ≤ 100."

**COMBINATORICS EXAMPLE:**
Original: "Consider a graph G with n vertices. Find the maximum number of edges such that G has no triangle."
Distorted: "Take a graph G with n vertices. Determine the largest number of edges where G contains no triangle."

**CALCULUS EXAMPLE:**
Original: "Given f(x) = x², find the derivative of f at x = 3."
Distorted: "Suppose f(x) = x². Compute the derivative of f at x = 3."

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.2 SYNONYM SUBSTITUTION to the following problem.

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.3: LIGHT REPHRASING
    # =========================================================================
    0.3: f"""You are an expert mathematical question paraphraser applying μ=0.3 distortion level.

## DISTORTION TYPE: LIGHT REPHRASING

Rephrase sentences using different grammatical structures while preserving EXACT mathematical content.

### ALLOWED TRANSFORMATIONS:
✓ Change sentence order (if logically equivalent and dependencies preserved)
✓ Combine short sentences into longer compound sentences
✓ Split long sentences into shorter ones
✓ Use different clause structures
✓ Active ↔ Passive voice (where mathematically natural)
✓ Vary connecting words: "thus", "hence", "therefore", "moreover", "consequently"
✓ Change question phrasing: "What is X?" ↔ "Find X" ↔ "Determine X"

### WHAT TO PRESERVE EXACTLY:
✗ Every numerical value (unchanged)
✗ Every mathematical relationship
✗ Every constraint and condition
✗ The exact mathematical question being asked
✗ All given information (nothing added, nothing removed)

### EXAMPLES ACROSS DOMAINS:

**ALGEBRA EXAMPLE:**
Original: "Let f(x) = x² + 2x + 1. Find all values of x such that f(x) = 0."
Distorted: "Consider the function f(x) = x² + 2x + 1. What are all values of x for which f(x) = 0?"

**GEOMETRY EXAMPLE:**
Original: "Let ABCD be a square with side length 1. Let E be the midpoint of AB. Find the area of triangle CDE."
Distorted: "Consider a square ABCD where each side has length 1, and let E denote the midpoint of AB. What is the area of triangle CDE?"

**NUMBER THEORY EXAMPLE:**
Original: "Let n be a positive integer. Prove that if n² is even, then n is even."
Distorted: "For a positive integer n, show that n must be even whenever n² is even."

**COMBINATORICS EXAMPLE:**
Original: "There are n students and k committees. Each student joins exactly 2 committees. Each committee has exactly 3 students. Find the relationship between n and k."
Distorted: "Suppose we have n students and k committees, where every student belongs to precisely 2 committees while every committee contains precisely 3 students. Determine how n and k are related."

**CALCULUS EXAMPLE:**
Original: "Let f be a continuous function on [0,1]. If f(0) = 1 and f(1) = -1, prove there exists c in (0,1) with f(c) = 0."
Distorted: "Suppose f is continuous on the interval [0,1], with f(0) = 1 and f(1) = -1. Show that some c exists in the open interval (0,1) satisfying f(c) = 0."

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.3 LIGHT REPHRASING to the following problem.

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.4: VARIABLE & ENTITY RENAMING (Combined)
    # =========================================================================
    0.4: f"""You are an expert mathematical question paraphraser applying μ=0.4 distortion level.

## DISTORTION TYPE: VARIABLE & ENTITY RENAMING

You MUST apply distortion to EVERY question. Apply these methods in order of priority:

### PRIORITY 1: VARIABLE RENAMING (If variables exist)
Systematically rename mathematical variables:
| Original | → | New |
|----------|---|-----|
| x | → | t |
| y | → | s |
| z | → | u |
| n | → | r |
| m | → | k |
| p | → | q |
| f | → | g |
| g | → | h |
| a | → | c |
| b | → | d |
| α | → | β |

### PRIORITY 2: ENTITY REPLACEMENT (ALWAYS apply if no variables)
Change names and labels throughout:
- Person names: Alice→Maria, Bob→Carlos, Raj→David, Sindy→Elena
- Object labels: "box"→"container", "ball"→"sphere"
- Geometric labels: Triangle ABC → Triangle PQR (systematic: A→P, B→Q, C→R)
- Set labels: Set S → Set T, Set A → Set B
- Graph labels: Graph G → Graph H

### PRIORITY 3: LIGHT SYNONYM CHANGES (Combine with above)
Also apply some synonym substitutions:
- "find" → "determine"
- "prove" → "show" 
- "calculate" → "compute"
- "given" → "suppose"

### ⚠️ CRITICAL: ENSURE VISIBLE DISTORTION!
Every question MUST be MORE distorted than μ=0.3 output.
- If only 1-2 variables to rename: ALSO apply entity replacement AND multiple synonyms
- If no variables: MUST apply entity replacement AND synonyms
- The output must show COMBINED changes, not just a single letter swap

### CONSISTENCY RULES:
⚠️ If variable "x" becomes "t", then "x" → "t" EVERYWHERE
⚠️ If "ABC" becomes "PQR", apply systematically: A→P, B→Q, C→R everywhere
⚠️ Standard constants π, e, i REMAIN UNCHANGED
⚠️ ALL numerical values stay EXACTLY the same

### EXAMPLES:

**WITH VARIABLES:**
Original: "Let f(x) = x² - 3x + 2. Find all x such that f(x) = 0."
Distorted: "Let g(t) = t² - 3t + 2. Determine all t such that g(t) = 0."

**WORD PROBLEM (No variables):**
Original: "In a game, Raj has three boxes. One box contains two red balls..."
Distorted: "In a game, David has three containers. One container holds two crimson spheres..."

**GEOMETRY (Point labels):**
Original: "In triangle ABC, let D be the midpoint of BC. If AB = 5..."
Distorted: "In triangle PQR, let M be the midpoint of QR. If PQ = 5..."

**SEQUENCE (Named but no explicit variables):**
Original: "Sindy writes down the positive integers less than 200..."
Distorted: "Elena records the positive integers below 200..."

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.4 VARIABLE & ENTITY RENAMING to the following problem.
Remember: The output MUST be visibly different from the input!

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.5: NOTATION VARIATION + REPHRASING
    # =========================================================================
    0.5: f"""You are an expert mathematical question paraphraser applying μ=0.5 distortion level.

## DISTORTION TYPE: NOTATION VARIATION + REPHRASING

You MUST apply distortion to EVERY question. Use these methods:

### METHOD 1: NOTATION CONVERSION (Primary)
Convert between symbolic and verbal forms:

**Symbolic → Verbal:**
| Symbolic | → | Verbal |
|----------|---|--------|
| x² | → | "x squared" or "the square of x" |
| x³ | → | "x cubed" |
| xⁿ | → | "x to the power n" |
| √x | → | "the square root of x" |
| ∑ | → | "the sum" |
| ∏ | → | "the product" |
| ∫ | → | "the integral" |
| ∈ | → | "belongs to" or "is an element of" |
| ∀ | → | "for all" or "for every" |
| ∃ | → | "there exists" |
| gcd | → | "the greatest common divisor" |
| lcm | → | "the least common multiple" |
| ⌊x⌋ | → | "the floor of x" |
| ⌈x⌉ | → | "the ceiling of x" |
| ≥ | → | "is at least" or "is greater than or equal to" |
| ≤ | → | "is at most" or "is less than or equal to" |

**Verbal → Symbolic (or vice versa)**

### METHOD 2: SENTENCE RESTRUCTURING (Always apply)
Even if no notation to convert, ALWAYS restructure sentences:
- Rephrase questions using different grammatical structures
- Change "What is X?" to "Determine X" or "Find X"
- Combine or split sentences
- Use different clause ordering

### ⚠️ CRITICAL: ENSURE INTENSITY ABOVE μ=0.4!
Every output MUST be MORE distorted than μ=0.4.
- ALWAYS combine notation variation WITH variable renaming (x→t, n→r)
- If no special notation exists, apply sentence restructuring + variable renaming + light synonyms
- The combined effect should exceed what μ=0.4 produced

### EXAMPLES:

**WITH NOTATION:**
Original: "Evaluate ∑ᵢ₌₁ⁿ i² for n ∈ ℕ."
Distorted: "Evaluate the sum from i equals 1 to n of i squared, where n belongs to the natural numbers."

**WORD PROBLEM (No special notation):**
Original: "In a game, there are three boxes. One contains red balls, one contains blue balls."
Distorted: "Consider a game involving three boxes, where one box holds red balls and another holds blue balls."

**GEOMETRY:**
Original: "Let ABC be a triangle with AB = 5. Find the area."
Distorted: "Consider a triangle ABC where AB equals 5. Determine the area of this triangle."

**NUMBER THEORY:**
Original: "Prove that for all n ≥ 2, if p divides n!, then p ≤ n."
Distorted: "Show that for every integer n that is at least 2, whenever p is a divisor of n factorial, p must be at most n."

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.5 NOTATION VARIATION + REPHRASING to the following problem.
Remember: The output MUST be visibly different from the input!

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.6: CLAUSE REORDERING
    # =========================================================================
    0.6: f"""You are an expert mathematical question paraphraser applying μ=0.6 distortion level.

## DISTORTION TYPE: CLAUSE REORDERING + SENTENCE RESTRUCTURING

Reorder SENTENCES and CLAUSES, NOT mathematical operands.

### ❌ CRITICAL: WHAT YOU MUST NEVER DO ❌
You may ONLY reorder SENTENCES and CLAUSES, NEVER mathematical expressions!

**FORBIDDEN - Operand Swapping (Changes the answer!):**
❌ (A + B) - (C - D) → (C - D) - (A + B)  ← WRONG! Changes answer!
❌ (3x + 2y) - (3x - 2y) → (3x - 2y) - (3x + 2y)  ← WRONG! Changes sign!
❌ a - b → b - a  ← WRONG! Subtraction is not commutative!
❌ a ÷ b → b ÷ a  ← WRONG! Division is not commutative!

**ALLOWED - Sentence/Clause Reordering:**
✓ "Let x=5. Let y=3. Find x+y." → "Let y=3. Let x=5. Find x+y." (OK, independent definitions)
✓ "Given n≥2 and n is prime..." → "Given n is prime and n≥2..." (OK, AND is commutative)

### METHODS TO USE:

**METHOD 1: SENTENCE REORDERING**
- Swap independent definitions/statements
- Move constraints that don't depend on each other

**METHOD 2: SENTENCE COMBINING/SPLITTING**
- Combine: "Let n be an integer. Let n ≥ 2." → "Let n ≥ 2 be an integer."
- Split: "Given ABC with AB=5 and BC=3" → "Given ABC. We have AB=5. Also BC=3."

**METHOD 3: STRUCTURAL REPHRASING**
- Change passive ↔ active voice
- Use different connecting words

### ⚠️ ENSURE INTENSITY ABOVE μ=0.5!
ALWAYS combine clause reordering WITH:
- Variable renaming (x→t, n→r) from μ=0.4
- Some notation variation from μ=0.5
- Synonym substitutions from μ=0.2

If the question has few clauses, the supplements become MORE important to ensure proper intensity.

### EXAMPLES:

**CORRECT (Sentence reorder):**
Original: "Let ABC be a triangle. Let D be midpoint of BC. AB = 6 and AC = 8. Find DE."
Distorted: "Let ABC be a triangle with AB = 6 and AC = 8. Let D be the midpoint of BC. Find DE."

**CORRECT (Rephrase structure):**
Original: "Find all primes p such that p+2 is also prime."
Distorted: "Determine every prime number p for which p+2 is likewise prime."

**WRONG (Would change math):**
Original: "What is (3x + 2y) - (3x - 2y)?"
❌ WRONG: "What is (3x - 2y) - (3x + 2y)?" ← Swapped operands, changes answer!
✓ CORRECT: "Calculate (3x + 2y) - (3x - 2y)." ← Changed verb only, math preserved

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.6 CLAUSE REORDERING + RESTRUCTURING to the following problem.
⚠️ NEVER swap operands in mathematical expressions!

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.7: FORMAT CONVERSION
    # =========================================================================
    0.7: f"""You are an expert mathematical question paraphraser applying μ=0.7 distortion level.

## DISTORTION TYPE: FORMAT CONVERSION

Convert between dense prose and structured list formats.

### CONVERSION DIRECTIONS:

**OPTION A: Dense Prose → Structured Format**
Convert flowing narrative into:
• Clear sections: "Setup:", "Given:", "Conditions:", "Find:"
• Bulleted or numbered lists
• Indented sub-conditions
• Line-by-line breakdown

**OPTION B: Structured Format → Dense Prose**
Convert lists into:
• Flowing narrative sentences
• Connected paragraphs
• Integrated conditions in continuous text

### CRITICAL RULE: ALL information must be preserved. Count constraints before and after!

### EXAMPLES ACROSS DOMAINS:

**GEOMETRY (Prose → Structured):**
Original: "In triangle ABC, let D be a point on BC such that BD = 2DC. If the area of triangle ABC is 18, find the area of triangle ABD."

Distorted:
"Given:
• Triangle ABC
• Point D on segment BC with BD = 2DC
• Area of triangle ABC = 18

Find: Area of triangle ABD"

**ALGEBRA (Structured → Prose):**
Original:
"Given:
• f(x) = x² + ax + b
• f(1) = 0
• f(2) = 3
Find: Values of a and b"

Distorted: "Let f(x) = x² + ax + b be a quadratic function satisfying f(1) = 0 and f(2) = 3. Determine the values of a and b."

**NUMBER THEORY (Prose → Structured):**
Original: "Let p be a prime. Arrange integers from 1 to p² in a p×p matrix. One can add or subtract 1 from any row or column. An arrangement is good if all entries can become zero. Find the number of good arrangements."

Distorted:
"Setup:
• p is a prime number
• Integers {{1, 2, ..., p²}} arranged in a p×p matrix

Allowed operations:
1. Add 1 to all elements in any row
2. Subtract 1 from all elements in any row
3. Add 1 to all elements in any column
4. Subtract 1 from all elements in any column

Definition: An arrangement is "good" if all entries can become 0 through finite operations.

Find: The number of good arrangements"

**COMBINATORICS (Structured → Prose):**
Original:
"Conditions:
• n people sit at a circular table
• Each shakes hands with exactly k neighbors
• k ≤ n-1
Find: Valid values of n and k"

Distorted: "Consider n people sitting around a circular table, where each person shakes hands with exactly k of their neighbors and k ≤ n-1. For which values of n and k is such an arrangement possible?"

### ⚠️ CRITICAL: ALWAYS APPLY FORMAT CHANGE!
Every output MUST have a different format from input:
- If input is prose → convert to structured (bullets, sections)
- If input is structured → convert to prose
- If format is ambiguous → restructure with clear sections OR flowing narrative

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.7 FORMAT CONVERSION to the following problem.
Remember: The output MUST have a visibly different FORMAT from the input!

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.8: HYBRID DISTORTION
    # =========================================================================
    0.8: f"""You are an expert mathematical question paraphraser applying μ=0.8 distortion level.

## DISTORTION TYPE: HYBRID (Multiple Methods Combined)

Combine 3+ methods for significant transformation while preserving mathematical meaning.

### ❌ CRITICAL: PRESERVE MATHEMATICAL RELATIONSHIPS ❌

**FORBIDDEN - Reversing Relationships (Changes meaning!):**
❌ "X is divisible by Y" → "X divides Y" or "X is a divisor of Y"  ← OPPOSITE meaning!
❌ "X > Y" → "Y > X"  ← REVERSED inequality!
❌ "X is a subset of Y" → "Y is a subset of X"  ← REVERSED containment!
❌ "X implies Y" → "Y implies X"  ← REVERSED logic!

**CORRECT - Same relationship, different words:**
✓ "X is divisible by Y" → "Y divides X" (same meaning)
✓ "X is divisible by Y" → "X is a multiple of Y" (same meaning)
✓ "divisible by 2010²" → "multiple of 2010²" (same meaning)

### ⚠️ CRITICAL: PRESERVE STRUCTURAL PATTERNS IN PRODUCTS ⚠️

When renaming variables in pairwise products, PRESERVE THE ADJACENCY STRUCTURE!

**CYCLIC PRODUCTS (ab, bc, cd, da) - Each pair shares one variable with the next:**
Original: ab, bc, cd, da (a→b→c→d→a cycle)
✓ CORRECT renaming (a→x, b→y, c→z, d→w): xy, yz, zw, wx (preserves cycle!)
❌ WRONG: xw, yz, zw, xy (breaks the adjacency pattern - xw and yz share nothing!)

**SEQUENTIAL PRODUCTS:**
Original: ab, bc, cd (linear chain: each shares one variable)
✓ CORRECT: xy, yz, zw (preserves chain)
❌ WRONG: xy, zw, ab (breaks chain - no shared variables)

**RULE: When you see products like ab, bc, cd, da:**
1. Identify the pattern (cyclic, sequential, etc.)
2. Rename variables SYSTEMATICALLY: a→x, b→y, c→z, d→w
3. Apply the SAME substitution to ALL products
4. Result: xy, yz, zw, wx (NOT random combinations!)

### METHODS TO COMBINE (Apply at least 3):
1. **Entity replacement**: Change names, labels (Alice→Bob, Set S→Set T)
2. **Variable renaming**: Systematic changes (x→t, y→s, n→m) - PRESERVE STRUCTURE!
3. **Synonym substitution**: Verbs only (find→determine, prove→show)
4. **Sentence restructuring**: Different grammatical structures
5. **Notation variation**: Some symbolic↔verbal conversion

### EXAMPLES:

**CORRECT HYBRID:**
Original: "Find the smallest N such that the product of N consecutive integers is divisible by 2010²."
Distorted: "Determine the minimum value of M where the multiplication of M successive whole numbers is a multiple of the square of 2010."
(✓ Variables renamed, ✓ synonyms, ✓ notation variation, ✓ "divisible by" → "multiple of" SAME meaning)

**WRONG (Relationship reversed):**
Original: "...product is divisible by 2010²..."
❌ WRONG: "...product is a divisor of 2010²..." ← OPPOSITE meaning, FORBIDDEN!

**PAIRWISE PRODUCTS EXAMPLE:**
Original: "The pairwise products ab, bc, cd, da of positive integers a, b, c, d are 64, 88, 120, 165 in some order."
✓ CORRECT: "The pairwise products xy, yz, zw, wx of positive integers x, y, z, w are 64, 88, 120, 165 in some order."
❌ WRONG: "The pairwise products xw, yz, zw, xy..." ← Breaks the cyclic structure!

**GEOMETRY EXAMPLE:**
Original: "In triangle ABC with AB = 5, let D be the midpoint of BC. Find the length of AD."
Distorted: "Consider triangle PQR where PQ equals 5. Let M denote the midpoint of QR. Determine the length of PM."

{CRITICAL_PRESERVATION_RULES}

## YOUR TASK:
Apply μ=0.8 HYBRID DISTORTION to the following problem.
⚠️ NEVER reverse mathematical relationships (divisibility, inequalities, containment)!
⚠️ When renaming variables in products, PRESERVE THE STRUCTURAL PATTERN!

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, no explanations):""",

    # =========================================================================
    # μ = 0.9: MAXIMUM DISTORTION
    # =========================================================================
    0.9: f"""You are an expert mathematical question paraphraser applying μ=0.9 distortion level.

## DISTORTION TYPE: MAXIMUM (Aggressive Surface Transformation)

Apply AGGRESSIVE transformations to make the problem VISUALLY different while preserving EXACT mathematical content.

### CREATIVE VOCABULARY TECHNIQUES (Use These!):
Use unusual but MATHEMATICALLY ACCURATE alternative terminology:
• "triangle" → "three-sided polygon", "triangular figure"
• "integer" → "whole number", "numeral from ℤ"
• "prime" → "prime number" (keep exact)
• "sequence" → "ordered collection", "succession of terms"
• "function" → "mapping", "transformation"
• "equation" → "mathematical relation", "equality"
• "area" → "two-dimensional measure", "planar extent"
• "vertex/vertices" → "node(s)", "corner point(s)"
• "random" → "stochastic", "uniformly selected"
• "compute" → "ascertain", "establish", "derive"
• "square-based pyramid" → "pyramid with quadrilateral base" (keep PYRAMID specific!)

### ⚠️ CRITICAL: PRESERVE STRUCTURAL PATTERNS ⚠️

**PRESERVE SHAPE SPECIFICITY:**
• "square-based pyramid" MUST remain a PYRAMID (not generic "polyhedron")
• "triangle" must remain a 3-sided figure
• Specific shapes → Keep their defining properties

**CYCLIC/SEQUENTIAL PRODUCTS - PRESERVE STRUCTURE:**
When renaming variables in products like (ab, bc, cd, da), maintain adjacency:
✓ CORRECT (a→x, b→y, c→z, d→w): xy, yz, zw, wx (preserves cycle!)
❌ WRONG: xw, yz, zw, xy (breaks adjacency pattern!)

### SENTENCE RESTRUCTURING TECHNIQUES:
• Convert statements to relative clauses
• Use formal/academic mathematical language
• Add legitimate mathematical context phrases
• Vary sentence length and complexity
• Use passive voice creatively

### APPLY ALL OF THESE:
1. ✓ Complete entity replacement (names, labels: ABC→PQR, Alice→Christina)
2. ✓ Variable renaming (x→t, n→r, f→g - SYSTEMATIC throughout, PRESERVE STRUCTURE)
3. ✓ Creative mathematical vocabulary (as above)
4. ✓ Aggressive rephrasing (every sentence restructured)
5. ✓ Clause reordering (where logically safe)

### ABSOLUTE BOUNDARIES (NEVER VIOLATE):
✗ Every NUMBER must remain EXACTLY the same
✗ Every mathematical FORMULA must be equivalent
✗ Every CONSTRAINT must be preserved
✗ The ANSWER must remain IDENTICAL
✗ Output must be COHERENT ENGLISH (no gibberish!)
✗ Problem must remain SOLVABLE
✗ Specific shapes (pyramid, triangle) must retain their defining type

### EXAMPLES:

**EXAMPLE 1 - Astronomy/Physics:**
Original: "A comet of mass m impacts the earth (mass M radius R) at minimum impact speed. What is the expression for the total energy released?"

Distorted: "Explain the situation whereby a celestial object, known by its mass 'm', collides with our terrestrial sphere (of mass 'M' and radius 'R') to generate kinetic energy upon impact at minimal velocity. Express the formula for the total energy discharged."

**EXAMPLE 2 - Algebra:**
Original: "Find all positive integers (m,n) such that mn-1 divides m²+n²."

Distorted: "Determine the complete collection of ordered pairs (a,b) where both a and b are natural numbers, satisfying the divisibility criterion: the expression a squared plus b squared must be evenly divisible by the quantity (a times b minus 1)."

**EXAMPLE 3 - Geometry:**
Original: "In acute triangle ABC, altitudes AD, BE, CF meet at orthocenter H. Find HQ/HR."

Distorted: "Consider an acute triangular figure PQR. Let PM, QN, RO be the perpendicular heights intersecting at the orthocentric point K. Determine the ratio KV to KS."

**EXAMPLE 4 - Number Theory:**
Original: "Let p be a prime. Arrange integers 1 to p² in a p×p matrix. Find the number of good arrangements."

Distorted: "Consider a prime number q. Distribute the integers from 1 to q squared into a square matrix of dimensions q by q. Ascertain the quantity of valid configurations."

{CRITICAL_PRESERVATION_RULES}

## ⚠️ CRITICAL OUTPUT REQUIREMENTS:
1. Output MUST be coherent, readable English
2. Output MUST be a valid mathematical question
3. Output should be similar LENGTH to original (not much longer)
4. NO random characters, NO code, NO multiple languages
5. If unsure, err on the side of LESS distortion rather than gibberish

## YOUR TASK:
Apply μ=0.9 MAXIMUM DISTORTION to the following problem.

ORIGINAL PROBLEM:
{{question}}

DISTORTED PROBLEM (return ONLY the distorted question, nothing else):"""
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_distortion_prompt(question: str, miu: float) -> Optional[str]:
    """
    Get the appropriate distortion prompt for a given μ level.
    
    Args:
        question: The original mathematical question
        miu: Distortion level (0.0 to 0.9)
        
    Returns:
        Formatted prompt string, or None if miu is 0.0 (baseline)
    """
    if miu == 0.0:
        return None  # No distortion needed for baseline
    
    # Round to nearest 0.1 to match our prompt keys
    miu_key = round(miu, 1)
    
    if miu_key not in MATH_DISTORTION_PROMPTS:
        raise ValueError(f"Invalid μ level: {miu}. Must be 0.0-0.9 in 0.1 increments.")
    
    prompt_template = MATH_DISTORTION_PROMPTS[miu_key]
    # Use replace instead of format to avoid issues with curly braces in math questions
    # (e.g., set notation like {1, 2, 3, ...} which would break .format())
    return prompt_template.replace("{question}", question)


def get_miu_level_description(miu: float) -> str:
    """Get human-readable description of a μ level."""
    descriptions = {
        0.0: "Baseline (No Distortion)",
        0.1: "Entity Name Replacement",
        0.2: "Synonym Substitution",
        0.3: "Light Rephrasing",
        0.4: "Variable Renaming",
        0.5: "Notation Variation",
        0.6: "Clause Reordering",
        0.7: "Format Conversion",
        0.8: "Hybrid Distortion",
        0.9: "Maximum Distortion"
    }
    return descriptions.get(round(miu, 1), "Unknown")


def get_all_miu_levels() -> list:
    """Get list of all μ levels."""
    return [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


# =============================================================================
# MODULE INFO
# =============================================================================

if __name__ == "__main__":
    print("🦎 Chameleon Framework - Mathematical Distortion Prompts")
    print("=" * 60)
    print("\nAvailable μ levels and their distortion types:\n")
    
    for miu in get_all_miu_levels():
        temp = calculate_temperature(miu) if miu > 0 else 0.0
        desc = get_miu_level_description(miu)
        print(f"  μ = {miu:.1f} | Temp: {temp:.2f} | {desc}")
    
    print("\n" + "=" * 60)
    print("Use get_distortion_prompt(question, miu) to get a prompt.")

