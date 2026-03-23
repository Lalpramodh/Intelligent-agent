def validate_output(response):
    if not isinstance(response, dict):
        response = {}

    normalized = {
        "status": response.get("status", "error"),
        "message": response.get("message", "Invalid response format"),
        "summary": response.get("summary", {}),
        "parsed_request": response.get("parsed_request", {}),
        "api_results": response.get("api_results", {}),
        "decision_logic": response.get("decision_logic", []),
        "flow_diagram": response.get("flow_diagram", []),
        "failure_handling": response.get("failure_handling", []),
        "warnings": response.get("warnings", []),
        "recommendations": response.get("recommendations", []),
    }

    checks = [
        {
            "name": "response_status",
            "passed": normalized["status"] in {"success", "partial_success", "fail", "error"},
            "detail": "Response status uses an expected lifecycle value.",
        },
        {
            "name": "summary_object",
            "passed": isinstance(normalized["summary"], dict),
            "detail": "Summary payload is a JSON object.",
        },
        {
            "name": "api_results_object",
            "passed": isinstance(normalized["api_results"], dict),
            "detail": "API results payload is a JSON object.",
        },
        {
            "name": "decision_logic_list",
            "passed": isinstance(normalized["decision_logic"], list) and bool(normalized["decision_logic"]),
            "detail": "Decision logic is captured as a non-empty list.",
        },
        {
            "name": "flow_diagram_list",
            "passed": isinstance(normalized["flow_diagram"], list) and bool(normalized["flow_diagram"]),
            "detail": "API flow diagram steps are present.",
        },
        {
            "name": "failure_handling_list",
            "passed": isinstance(normalized["failure_handling"], list) and bool(normalized["failure_handling"]),
            "detail": "Failure handling guidance is present.",
        },
    ]

    normalized["validation"] = {
        "is_valid": all(check["passed"] for check in checks),
        "checks": checks,
    }

    return normalized
