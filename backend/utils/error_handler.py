try:
    from .validator import validate_output
except ImportError:
    from utils.validator import validate_output


def handle_error(e):
    return validate_output({
        "status": "error",
        "message": "The backend hit an unexpected error while processing the scheduling request.",
        "summary": {
            "recommended_action": "Retry the request after checking the backend logs.",
            "error_type": type(e).__name__,
        },
        "parsed_request": {},
        "api_results": {},
        "decision_logic": [
            "The request reached the backend route.",
            "An unhandled exception interrupted the decision flow before a final response could be assembled.",
        ],
        "flow_diagram": [
            "Frontend -> Flask API",
            "Flask API -> Exception",
            "Exception -> Structured error handler",
            "Structured error handler -> Frontend",
        ],
        "failure_handling": [
            "Return a stable JSON error payload instead of a raw stack trace.",
            "Preserve the failure summary so the frontend can render it cleanly.",
            "Ask the operator to inspect the backend logs for the root cause.",
        ],
        "warnings": [str(e)],
        "recommendations": [
            "Verify environment variables and installed dependencies.",
            "Retry the same request after resolving the server-side exception.",
        ],
    })
