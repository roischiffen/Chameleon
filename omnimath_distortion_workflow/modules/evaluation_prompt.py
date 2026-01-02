"""
Evaluation Prompt Module for OmniMath GPT-5 Evaluation

Creates standardized prompts and batch requests for evaluating
math questions with GPT-5 using minimal reasoning effort.

Examples:
    >>> prompt = create_evaluation_prompt("What is 2 + 2?")
    >>> custom_id = generate_custom_id(3624, 0.4)
    >>> question_id, miu = parse_custom_id("q_3624_miu_0.4")
"""

import re
from typing import Tuple


# Prompt template for math problem evaluation
# Improved: Clear role, expectations, and format
EVALUATION_PROMPT_TEMPLATE = """You are an expert mathematician solving competition-level math problems.

Task: Solve the following problem and provide ONLY the final answer.

Format requirements:
- Give only the numerical answer (or exact mathematical expression if needed)
- No explanations, no work shown, no units unless asked
- For fractions, use the form a/b
- For "yes/no" questions, answer exactly "Yes" or "No"

Problem:
{question}

Final Answer:"""


def create_evaluation_prompt(question: str) -> str:
    """
    Create a standardized prompt for evaluating a math question.
    
    The prompt instructs GPT-5 to provide ONLY the final answer,
    optimized for minimal reasoning effort mode.
    
    Args:
        question: The math problem to solve
        
    Returns:
        Formatted prompt string
        
    Examples:
        >>> prompt = create_evaluation_prompt("What is 2 + 2?")
        >>> "What is 2 + 2?" in prompt
        True
        >>> "ONLY the final" in prompt
        True
    """
    return EVALUATION_PROMPT_TEMPLATE.format(question=question)


def generate_custom_id(question_id: int, miu: float) -> str:
    """
    Generate a unique custom_id for batch API requests.
    
    Format: q_{question_id}_miu_{miu}
    
    Args:
        question_id: Unique identifier for the question
        miu: Distortion level (0.0 for baseline, 0.1-0.9 for distorted)
        
    Returns:
        Custom ID string
        
    Examples:
        >>> generate_custom_id(3624, 0.4)
        'q_3624_miu_0.4'
        >>> generate_custom_id(3624, 0.0)
        'q_3624_miu_0.0'
        >>> generate_custom_id(100, 0.9)
        'q_100_miu_0.9'
    """
    return f"q_{question_id}_miu_{miu}"


def parse_custom_id(custom_id: str) -> Tuple[int, float]:
    """
    Parse a custom_id string to extract question_id and miu.
    
    Reverse of generate_custom_id.
    
    Args:
        custom_id: Custom ID string in format q_{id}_miu_{miu}
        
    Returns:
        Tuple of (question_id, miu)
        
    Raises:
        ValueError: If custom_id format is invalid
        
    Examples:
        >>> parse_custom_id("q_3624_miu_0.4")
        (3624, 0.4)
        >>> parse_custom_id("q_3624_miu_0.0")
        (3624, 0.0)
        >>> parse_custom_id("q_100_miu_0.9")
        (100, 0.9)
    """
    pattern = r'^q_(\d+)_miu_([\d.]+)$'
    match = re.match(pattern, custom_id)
    
    if not match:
        raise ValueError(f"Invalid custom_id format: {custom_id}. Expected: q_{{id}}_miu_{{miu}}")
    
    question_id = int(match.group(1))
    miu = float(match.group(2))
    
    return (question_id, miu)


def create_batch_request(question_id: int, miu: float, question: str, custom_id: str = None) -> dict:
    """
    Create a single batch API request for OpenAI Batch API.
    
    Configures GPT-5 with minimal reasoning effort for fast answer extraction.
    
    Args:
        question_id: Unique identifier for the question
        miu: Distortion level (0.0 for baseline)
        question: The math problem text
        custom_id: Optional custom ID (generated if not provided)
        
    Returns:
        Dictionary formatted for OpenAI Batch API
        
    Examples:
        >>> req = create_batch_request(3624, 0.4, "What is 2+2?")
        >>> req["custom_id"]
        'q_3624_miu_0.4'
        >>> req["body"]["model"]
        'gpt-5'
        >>> req["body"]["reasoning_effort"]
        'minimal'
    """
    if custom_id is None:
        custom_id = generate_custom_id(question_id, miu)
    
    prompt = create_evaluation_prompt(question)
    
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-5",
            "reasoning_effort": "minimal",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_completion_tokens": 100
        }
    }


# Simple test runner when executed directly
if __name__ == "__main__":
    import json
    
    print("Testing Evaluation Prompt Module\n")
    print("=" * 50)
    
    # Test 1: Prompt generation
    print("\n1. Testing create_evaluation_prompt()")
    test_question = "The altitudes of a triangle are 12, 15, and 20. What is the area?"
    prompt = create_evaluation_prompt(test_question)
    print(f"   Question: {test_question}")
    print(f"   Generated prompt:\n{'-'*40}")
    print(prompt)
    print(f"{'-'*40}")
    
    # Test 2: Custom ID generation
    print("\n2. Testing generate_custom_id()")
    test_cases_gen = [
        (3624, 0.4, "q_3624_miu_0.4"),
        (3624, 0.0, "q_3624_miu_0.0"),
        (100, 0.9, "q_100_miu_0.9"),
    ]
    for qid, miu, expected in test_cases_gen:
        result = generate_custom_id(qid, miu)
        status = "✅" if result == expected else "❌"
        print(f"   {status} generate_custom_id({qid}, {miu}) = {repr(result)}")
    
    # Test 3: Custom ID parsing
    print("\n3. Testing parse_custom_id()")
    test_cases_parse = [
        ("q_3624_miu_0.4", (3624, 0.4)),
        ("q_3624_miu_0.0", (3624, 0.0)),
        ("q_100_miu_0.9", (100, 0.9)),
    ]
    for custom_id, expected in test_cases_parse:
        result = parse_custom_id(custom_id)
        status = "✅" if result == expected else "❌"
        print(f"   {status} parse_custom_id({repr(custom_id)}) = {result}")
    
    # Test 4: Roundtrip
    print("\n4. Testing roundtrip (generate → parse)")
    for qid, miu, _ in test_cases_gen:
        custom_id = generate_custom_id(qid, miu)
        parsed_qid, parsed_miu = parse_custom_id(custom_id)
        status = "✅" if (parsed_qid == qid and parsed_miu == miu) else "❌"
        print(f"   {status} {qid}, {miu} → {repr(custom_id)} → {parsed_qid}, {parsed_miu}")
    
    # Test 5: Batch request format
    print("\n5. Testing create_batch_request()")
    request = create_batch_request(3624, 0.4, test_question)
    print(f"   Generated request (formatted JSON):")
    print(json.dumps(request, indent=2))
    
    # Validate structure
    checks = [
        ("custom_id present", "custom_id" in request),
        ("custom_id correct", request.get("custom_id") == "q_3624_miu_0.4"),
        ("method is POST", request.get("method") == "POST"),
        ("url correct", request.get("url") == "/v1/chat/completions"),
        ("model is gpt-5", request.get("body", {}).get("model") == "gpt-5"),
        ("reasoning_effort is minimal", request.get("body", {}).get("reasoning_effort") == "minimal"),
        ("max_completion_tokens is 100", request.get("body", {}).get("max_completion_tokens") == 100),
        ("messages present", "messages" in request.get("body", {})),
    ]
    
    print("\n   Structure validation:")
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        if not passed:
            all_passed = False
        print(f"   {status} {check_name}")
    
    # Test 6: Invalid custom_id parsing
    print("\n6. Testing invalid custom_id handling")
    invalid_ids = ["invalid", "q_abc_miu_0.4", "q_3624_miu", "3624_0.4"]
    for invalid_id in invalid_ids:
        try:
            parse_custom_id(invalid_id)
            print(f"   ❌ parse_custom_id({repr(invalid_id)}) should have raised ValueError")
        except ValueError as e:
            print(f"   ✅ parse_custom_id({repr(invalid_id)}) raised ValueError")
    
    print("\n" + "=" * 50)
    print("All tests completed!")

