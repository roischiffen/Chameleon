"""
Results Parser Module for OmniMath GPT-5 Evaluation

Parses OpenAI Batch API response files and extracts answers with token usage.

Usage:
    from modules.results_parser import parse_batch_results
    results = parse_batch_results(Path("evaluation/results/eval_batch1_results.jsonl"))
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Handle imports for both direct execution and module import
try:
    from omnimath_distortion_workflow.modules.evaluation_prompt import parse_custom_id
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from omnimath_distortion_workflow.modules.evaluation_prompt import parse_custom_id


def extract_answer_from_response(response_body: dict) -> str:
    """
    Extract the answer from a GPT-5 response body.
    
    Handles various response formats:
    - Direct numerical answer: "150"
    - With prefix: "The answer is 150"
    - With formatting: "Answer: 150"
    
    Args:
        response_body: The 'body' field from the API response
        
    Returns:
        Extracted answer string (cleaned)
        
    Examples:
        >>> body = {"choices": [{"message": {"content": "150"}}]}
        >>> extract_answer_from_response(body)
        '150'
        >>> body = {"choices": [{"message": {"content": "The answer is 150."}}]}
        >>> extract_answer_from_response(body)
        '150'
    """
    try:
        content = response_body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""
    
    if not content:
        return ""
    
    # Clean up the content
    answer = content.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        r'^the\s+answer\s+is\s*:?\s*',
        r'^answer\s*:?\s*',
        r'^result\s*:?\s*',
        r'^=\s*',
        r'^:\s*',
    ]
    
    for pattern in prefixes_to_remove:
        answer = re.sub(pattern, '', answer, flags=re.IGNORECASE)
    
    # Remove trailing punctuation (period, comma) if it's not part of a decimal
    # Keep decimal points: "0.5" but remove "150."
    if answer and answer[-1] in '.,' and not re.match(r'.*\d$', answer[:-1]):
        answer = answer[:-1]
    elif answer.endswith('.') and re.match(r'^\d+\.$', answer):
        # "150." → "150"
        answer = answer[:-1]
    
    return answer.strip()


def extract_token_usage(usage: Optional[dict]) -> Dict[str, Optional[int]]:
    """
    Extract token usage information from GPT-5 response.
    
    GPT-5 token fields:
    - input_tokens: Tokens in the prompt
    - output_tokens: Tokens in model's answer
    - reasoning_tokens: Internal reasoning tokens (in completion_tokens_details)
    
    Args:
        usage: The 'usage' field from the API response body
        
    Returns:
        Dict with input_tokens, output_tokens, reasoning_tokens (None if missing)
        
    Examples:
        >>> usage = {"input_tokens": 45, "output_tokens": 3}
        >>> extract_token_usage(usage)
        {'input_tokens': 45, 'output_tokens': 3, 'reasoning_tokens': None}
    """
    result = {
        "input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None
    }
    
    if not usage:
        return result
    
    # Extract input_tokens (GPT-5 uses input_tokens, older models use prompt_tokens)
    result["input_tokens"] = usage.get("input_tokens") or usage.get("prompt_tokens")
    
    # Extract output_tokens (GPT-5 uses output_tokens, older models use completion_tokens)
    result["output_tokens"] = usage.get("output_tokens") or usage.get("completion_tokens")
    
    # Extract reasoning_tokens from completion_tokens_details
    completion_details = usage.get("completion_tokens_details", {})
    if completion_details:
        result["reasoning_tokens"] = completion_details.get("reasoning_tokens")
    
    return result


def parse_single_result(result_line: dict) -> Dict[str, Any]:
    """
    Parse a single result line from the batch response.
    
    Args:
        result_line: Parsed JSON from one line of results file
        
    Returns:
        Structured result dict with question_id, miu, answer, tokens, etc.
    """
    custom_id = result_line.get("custom_id", "")
    
    # Initialize result
    parsed = {
        "custom_id": custom_id,
        "question_id": None,
        "miu": None,
        "model_answer": "",
        "success": False,
        "input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None,
        "error": None
    }
    
    # Parse custom_id to get question_id and miu
    try:
        question_id, miu = parse_custom_id(custom_id)
        parsed["question_id"] = question_id
        parsed["miu"] = miu
    except ValueError as e:
        parsed["error"] = f"Invalid custom_id: {e}"
        return parsed
    
    # Check response
    response = result_line.get("response", {})
    status_code = response.get("status_code")
    
    if status_code != 200:
        parsed["error"] = f"API error: status_code={status_code}"
        error_body = response.get("body", {})
        if isinstance(error_body, dict):
            parsed["error"] += f", {error_body.get('error', {}).get('message', '')}"
        return parsed
    
    # Extract answer from response body
    body = response.get("body", {})
    parsed["model_answer"] = extract_answer_from_response(body)
    parsed["success"] = True
    
    # Extract token usage
    usage = body.get("usage", {})
    token_info = extract_token_usage(usage)
    parsed["input_tokens"] = token_info["input_tokens"]
    parsed["output_tokens"] = token_info["output_tokens"]
    parsed["reasoning_tokens"] = token_info["reasoning_tokens"]
    
    return parsed


def parse_batch_results(results_file: Path) -> List[Dict[str, Any]]:
    """
    Parse an OpenAI Batch API results file (JSONL format).
    
    Args:
        results_file: Path to the results JSONL file
        
    Returns:
        List of parsed result dictionaries
        
    Output format per entry:
    {
        "custom_id": "q_3624_miu_0.4",
        "question_id": 3624,
        "miu": 0.4,
        "model_answer": "150",
        "success": True,
        "input_tokens": 45,
        "output_tokens": 3,
        "reasoning_tokens": 0,
        "error": None
    }
    """
    results_file = Path(results_file)
    
    if not results_file.exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")
    
    results = []
    
    with open(results_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                result_line = json.loads(line)
                parsed = parse_single_result(result_line)
                parsed["line_number"] = line_num
                results.append(parsed)
                
            except json.JSONDecodeError as e:
                results.append({
                    "custom_id": "",
                    "question_id": None,
                    "miu": None,
                    "model_answer": "",
                    "success": False,
                    "input_tokens": None,
                    "output_tokens": None,
                    "reasoning_tokens": None,
                    "error": f"JSON parse error on line {line_num}: {e}",
                    "line_number": line_num
                })
    
    return results


def parse_all_results(results_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse all result files in a directory.
    
    Args:
        results_dir: Directory containing result JSONL files
        
    Returns:
        Dict mapping filename to list of parsed results
    """
    results_dir = Path(results_dir)
    all_results = {}
    
    for results_file in sorted(results_dir.glob("*.jsonl")):
        all_results[results_file.name] = parse_batch_results(results_file)
    
    return all_results


def get_parsing_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of parsed results.
    
    Args:
        results: List of parsed result dictionaries
        
    Returns:
        Summary statistics
    """
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    
    # Token stats
    input_tokens = [r["input_tokens"] for r in results if r["input_tokens"] is not None]
    output_tokens = [r["output_tokens"] for r in results if r["output_tokens"] is not None]
    reasoning_tokens = [r["reasoning_tokens"] for r in results if r["reasoning_tokens"] is not None]
    
    # μ distribution
    miu_counts = {}
    for r in results:
        if r["miu"] is not None:
            miu_key = str(r["miu"])
            miu_counts[miu_key] = miu_counts.get(miu_key, 0) + 1
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / total * 100) if total > 0 else 0,
        "total_input_tokens": sum(input_tokens) if input_tokens else 0,
        "total_output_tokens": sum(output_tokens) if output_tokens else 0,
        "total_reasoning_tokens": sum(reasoning_tokens) if reasoning_tokens else 0,
        "miu_distribution": miu_counts
    }


# Test/demo when executed directly
if __name__ == "__main__":
    print("Testing Results Parser Module\n")
    print("=" * 60)
    
    # Test 1: extract_answer_from_response
    print("\n1. Testing extract_answer_from_response()")
    test_bodies = [
        ({"choices": [{"message": {"content": "150"}}]}, "150"),
        ({"choices": [{"message": {"content": "The answer is 150"}}]}, "150"),
        ({"choices": [{"message": {"content": "Answer: 42"}}]}, "42"),
        ({"choices": [{"message": {"content": "  0.5  "}}]}, "0.5"),
        ({"choices": [{"message": {"content": "150."}}]}, "150"),
        ({}, ""),
    ]
    
    for body, expected in test_bodies:
        result = extract_answer_from_response(body)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {body} → {repr(result)} (expected {repr(expected)})")
    
    # Test 2: extract_token_usage
    print("\n2. Testing extract_token_usage()")
    test_usages = [
        ({"input_tokens": 45, "output_tokens": 3}, {"input_tokens": 45, "output_tokens": 3, "reasoning_tokens": None}),
        ({"input_tokens": 100, "output_tokens": 10, "completion_tokens_details": {"reasoning_tokens": 5}}, 
         {"input_tokens": 100, "output_tokens": 10, "reasoning_tokens": 5}),
        ({"prompt_tokens": 50, "completion_tokens": 5}, {"input_tokens": 50, "output_tokens": 5, "reasoning_tokens": None}),
        (None, {"input_tokens": None, "output_tokens": None, "reasoning_tokens": None}),
    ]
    
    for usage, expected in test_usages:
        result = extract_token_usage(usage)
        status = "✅" if result == expected else "❌"
        print(f"   {status} extract_token_usage({usage})")
        if result != expected:
            print(f"      Expected: {expected}")
            print(f"      Got: {result}")
    
    # Test 3: parse_single_result with mock data
    print("\n3. Testing parse_single_result()")
    mock_result = {
        "id": "response_abc",
        "custom_id": "q_3624_miu_0.4",
        "response": {
            "status_code": 200,
            "body": {
                "choices": [{"message": {"content": "150"}}],
                "usage": {
                    "input_tokens": 45,
                    "output_tokens": 3,
                    "total_tokens": 48,
                    "completion_tokens_details": {"reasoning_tokens": 0}
                }
            }
        }
    }
    
    parsed = parse_single_result(mock_result)
    print(f"   Parsed result:")
    print(f"      custom_id: {parsed['custom_id']}")
    print(f"      question_id: {parsed['question_id']}")
    print(f"      miu: {parsed['miu']}")
    print(f"      model_answer: {parsed['model_answer']}")
    print(f"      success: {parsed['success']}")
    print(f"      input_tokens: {parsed['input_tokens']}")
    print(f"      output_tokens: {parsed['output_tokens']}")
    print(f"      reasoning_tokens: {parsed['reasoning_tokens']}")
    print(f"      error: {parsed['error']}")
    
    expected_check = (
        parsed["question_id"] == 3624 and
        parsed["miu"] == 0.4 and
        parsed["model_answer"] == "150" and
        parsed["success"] == True and
        parsed["input_tokens"] == 45 and
        parsed["output_tokens"] == 3 and
        parsed["reasoning_tokens"] == 0
    )
    print(f"\n   {'✅' if expected_check else '❌'} All fields extracted correctly")
    
    # Test 4: Error handling
    print("\n4. Testing error handling")
    error_result = {
        "custom_id": "q_100_miu_0.5",
        "response": {
            "status_code": 500,
            "body": {"error": {"message": "Internal server error"}}
        }
    }
    
    parsed_error = parse_single_result(error_result)
    print(f"   Error result: success={parsed_error['success']}, error={parsed_error['error']}")
    status = "✅" if not parsed_error['success'] and parsed_error['error'] else "❌"
    print(f"   {status} Error handling works correctly")
    
    # Test 5: Mock file parsing
    print("\n5. Testing parse_batch_results() with mock file")
    
    # Create a temporary mock results file
    import tempfile
    mock_results = [
        {
            "id": "1",
            "custom_id": "q_100_miu_0.0",
            "response": {"status_code": 200, "body": {"choices": [{"message": {"content": "42"}}], "usage": {"input_tokens": 50, "output_tokens": 2}}}
        },
        {
            "id": "2", 
            "custom_id": "q_100_miu_0.1",
            "response": {"status_code": 200, "body": {"choices": [{"message": {"content": "The answer is 42"}}], "usage": {"input_tokens": 55, "output_tokens": 5}}}
        },
        {
            "id": "3",
            "custom_id": "q_200_miu_0.0",
            "response": {"status_code": 500, "body": {"error": {"message": "Rate limit"}}}
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for result in mock_results:
            f.write(json.dumps(result) + '\n')
        temp_path = f.name
    
    try:
        parsed_results = parse_batch_results(Path(temp_path))
        summary = get_parsing_summary(parsed_results)
        
        print(f"   Parsed {len(parsed_results)} results")
        print(f"   Summary:")
        print(f"      Total: {summary['total']}")
        print(f"      Successful: {summary['successful']}")
        print(f"      Failed: {summary['failed']}")
        print(f"      Success rate: {summary['success_rate']:.1f}%")
        print(f"      Total input tokens: {summary['total_input_tokens']}")
        print(f"      μ distribution: {summary['miu_distribution']}")
        
        success_check = (
            summary['total'] == 3 and
            summary['successful'] == 2 and
            summary['failed'] == 1
        )
        print(f"\n   {'✅' if success_check else '❌'} Mock file parsing works correctly")
        
    finally:
        import os
        os.unlink(temp_path)
    
    print("\n" + "=" * 60)
    print("Results parser tests completed!")

