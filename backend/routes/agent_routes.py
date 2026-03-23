from flask import Blueprint, request, jsonify

try:
    from ..agent.decision_agent import process_request
    from ..utils.error_handler import handle_error
    from ..utils.validator import validate_output
except ImportError:
    from agent.decision_agent import process_request
    from utils.error_handler import handle_error
    from utils.validator import validate_output

agent_bp = Blueprint('agent', __name__)

@agent_bp.route('/agent', methods=['POST'])
def agent():
    try:
        data = request.get_json(silent=True) or {}

        user_input = (data.get("query") or "").strip()

        if not user_input:
            return jsonify(validate_output({
                "status": "fail",
                "message": "Query is required",
                "summary": {
                    "recommended_action": "Provide a scheduling request in natural language.",
                    "outcome": "Input validation failed at the API boundary.",
                },
                "parsed_request": {},
                "api_results": {},
                "decision_logic": [
                    "The request reached the API route.",
                    "The route rejected the request because the query field was missing or empty.",
                ],
                "flow_diagram": [
                    "Frontend -> POST /api/agent",
                    "POST /api/agent -> API boundary validation",
                    "API boundary validation -> Structured fail response",
                ],
                "failure_handling": [
                    "Reject empty requests before any API calls are made.",
                    "Return a structured validation response to the frontend.",
                ],
                "warnings": [],
                "recommendations": [
                    "Try a prompt such as 'Schedule a meeting with Priya tomorrow at 4 PM in Hyderabad.'",
                ],
            })), 400

        result = process_request(user_input)

        status_code = {
            "success": 200,
            "partial_success": 207,
            "fail": 422,
            "error": 500,
        }.get(result.get("status"), 200)

        return jsonify(result), status_code

    except Exception as e:
        return jsonify(handle_error(e)), 500
