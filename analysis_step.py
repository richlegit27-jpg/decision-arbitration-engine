import json
from typing import Any, Dict, List

def analyze_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform analysis on the input data and return the results.

    The input_data is expected to have the following format:
    {
        "data": List[float],
        "parameters": Dict[str, Any]
    }

    The output will be a dictionary containing analysis results such as
    summary statistics.

    Args:
        input_data (Dict[str, Any]): The input data for analysis.

    Returns:
        Dict[str, Any]: The analysis results.
    """
    data: List[float] = input_data.get("data", [])
    parameters: Dict[str, Any] = input_data.get("parameters", {})

    if not data:
        return {
            "error": "Input data list is empty."
        }

    n = len(data)
    mean_val = sum(data) / n
    sorted_data = sorted(data)
    median_val = sorted_data[n // 2] if n % 2 == 1 else \
        (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2

    variance = sum((x - mean_val) ** 2 for x in data) / n
    std_dev = variance ** 0.5

    result = {
        "count": n,
        "mean": mean_val,
        "median": median_val,
        "variance": variance,
        "standard_deviation": std_dev,
    }

    # If parameters specify additional computations, handle them here
    if parameters.get("include_sum", False):
        result["sum"] = sum(data)
    if parameters.get("include_min", False):
        result["min"] = min(data)
    if parameters.get("include_max", False):
        result["max"] = max(data)
    if parameters.get("include_percentiles", False):
        percentiles = parameters.get("percentiles", [25, 50, 75])
        percentile_values = {}
        for p in percentiles:
            if not (0 <= p <= 100):
                continue
            k = (n - 1) * (p / 100)
            f = int(k)
            c = min(f + 1, n - 1)
            if f == c:
                percentile_values[str(p)] = sorted_data[int(k)]
            else:
                d0 = sorted_data[f] * (c - k)
                d1 = sorted_data[c] * (k - f)
                percentile_values[str(p)] = d0 + d1
        result["percentiles"] = percentile_values

    return result

def analysis_step(input_json: str) -> str:
    """
    Entry point for the analysis step.
    Accepts a JSON string as input, processes it, and returns results as JSON string.

    Args:
        input_json (str): JSON string input.

    Returns:
        str: JSON string output containing analysis results.
    """
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON input."})

    analysis_results = analyze_data(input_data)
    return json.dumps(analysis_results)
