try:
    from .parser import parse_input
    from ..services.weather_service import get_weather
    from ..services.calendar_service import check_availability
    from ..services.crm_service import log_meeting
    from ..utils.validator import validate_output
except ImportError:
    from agent.parser import parse_input
    from services.weather_service import get_weather
    from services.calendar_service import check_availability
    from services.crm_service import log_meeting
    from utils.validator import validate_output


FLOW_DIAGRAM = [
    "Frontend -> POST /api/agent",
    "POST /api/agent -> Request parser",
    "Parser -> Input validation",
    "Valid request -> Calendar availability API",
    "Available slot -> Weather API",
    "Approved slot -> CRM logging API",
    "Aggregated response -> Output validator -> Frontend",
]

FAILURE_HANDLING = [
    "If parsing misses the date or time, the agent returns a fail response and asks for the missing field.",
    "If the calendar slot is busy or outside business hours, the agent suggests the next available slots.",
    "If the weather API is unavailable, the agent continues in a degraded mode instead of crashing.",
    "If live weather risk is high, the agent blocks scheduling before CRM logging.",
    "If CRM logging fails, the agent returns partial_success so the operator can follow up manually.",
]


def process_request(user_input):
    parsed = parse_input(user_input)
    intent = parsed.get("intent")
    client = parsed.get("client_name") or "Client"
    city = parsed.get("city") or "Hyderabad"

    parsed["client_name"] = client
    parsed["city"] = city

    decision_logic = [
        f"Parsed the request with the {parsed.get('extraction_method', 'rules')} extraction path.",
    ]
    api_results = {}
    warnings = []
    recommendations = []

    if intent != "schedule":
        decision_logic.append("The parsed intent was not scheduling, so the workflow stopped before any API calls.")
        recommendations.append("Try a scheduling prompt such as 'Schedule a meeting with Priya tomorrow at 4 PM in Hyderabad.'")
        return _build_response(
            status="fail",
            message="Only smart scheduling requests are supported right now.",
            parsed_request=parsed,
            api_results=api_results,
            decision_logic=decision_logic,
            warnings=warnings,
            recommendations=recommendations,
            summary={
                "user_request": user_input,
                "recommended_action": "Resubmit the request with meeting details.",
                "outcome": "Intent not supported.",
            },
        )

    missing_fields = [field for field in ("date", "time") if not parsed.get(field)]
    if missing_fields:
        decision_logic.append(f"Validation stopped the workflow because these required fields were missing: {', '.join(missing_fields)}.")
        recommendations.append("Include a concrete date and time in the request.")
        return _build_response(
            status="fail",
            message=f"Please provide the missing field(s): {', '.join(missing_fields)}.",
            parsed_request=parsed,
            api_results=api_results,
            decision_logic=decision_logic,
            warnings=warnings,
            recommendations=recommendations,
            summary={
                "user_request": user_input,
                "recommended_action": "Collect the missing scheduling details.",
                "outcome": "Input validation failed.",
            },
        )

    calendar_result = check_availability(parsed.get("date"), parsed.get("time"))
    api_results["calendar"] = calendar_result
    decision_logic.append(calendar_result["message"])

    if not calendar_result.get("available"):
        next_available = calendar_result.get("next_available")
        if next_available:
            recommendations.append(f"Try {next_available['display']} instead.")

        return _build_response(
            status="fail",
            message=calendar_result["message"],
            parsed_request=parsed,
            api_results=api_results,
            decision_logic=decision_logic,
            warnings=warnings,
            recommendations=recommendations,
            summary={
                "user_request": user_input,
                "requested_slot": calendar_result["requested_slot"]["display"],
                "recommended_action": "Reschedule to an available slot.",
                "outcome": "Calendar check blocked the request.",
            },
        )

    weather_result = get_weather(city)
    api_results["weather"] = weather_result

    if weather_result.get("status") == "degraded":
        warnings.append(weather_result["advisory"])
        decision_logic.append("Weather validation continued in degraded mode because live weather data was unavailable.")
    else:
        decision_logic.append(
            f"Weather validation found {weather_result['condition']} conditions with {weather_result['risk_level']} risk in {city}."
        )

    if weather_result.get("risk_level") == "high":
        recommendations.append("Select a safer or indoor slot before logging the meeting in CRM.")
        return _build_response(
            status="fail",
            message=weather_result["advisory"],
            parsed_request=parsed,
            api_results=api_results,
            decision_logic=decision_logic,
            warnings=warnings,
            recommendations=recommendations,
            summary={
                "user_request": user_input,
                "requested_slot": calendar_result["requested_slot"]["display"],
                "recommended_action": "Reschedule because weather risk is high.",
                "outcome": "Weather risk blocked the request.",
            },
        )

    crm_result = log_meeting(client, parsed.get("date"), parsed.get("time"), city)
    api_results["crm"] = crm_result

    if crm_result.get("status") != "success":
        warnings.append(crm_result["message"])
        decision_logic.append("Scheduling reached the CRM step, but the CRM write did not complete successfully.")
        recommendations.append("Retry the CRM logging step or add the meeting manually.")
        return _build_response(
            status="partial_success",
            message="The meeting slot was approved, but CRM logging needs manual follow-up.",
            parsed_request=parsed,
            api_results=api_results,
            decision_logic=decision_logic,
            warnings=warnings,
            recommendations=recommendations,
            summary={
                "user_request": user_input,
                "requested_slot": calendar_result["requested_slot"]["display"],
                "recommended_action": "Retry CRM logging.",
                "outcome": "Scheduling succeeded but CRM logging failed.",
            },
        )

    decision_logic.append("The meeting was logged successfully in CRM, so the scheduling workflow completed.")
    recommendations.append(f"Share the confirmed slot {calendar_result['requested_slot']['display']} with {client}.")

    return _build_response(
        status="success",
        message=crm_result["message"],
        parsed_request=parsed,
        api_results=api_results,
        decision_logic=decision_logic,
        warnings=warnings,
        recommendations=recommendations,
        summary={
            "user_request": user_input,
            "requested_slot": calendar_result["requested_slot"]["display"],
            "recommended_action": "Confirm the meeting with the client.",
            "outcome": "Meeting scheduled successfully.",
            "weather_risk": weather_result.get("risk_level"),
            "crm_reference": crm_result.get("meeting_id"),
        },
    )


def _build_response(status, message, parsed_request, api_results, decision_logic, warnings, recommendations, summary):
    return validate_output({
        "status": status,
        "message": message,
        "summary": summary,
        "parsed_request": parsed_request,
        "api_results": api_results,
        "decision_logic": decision_logic,
        "flow_diagram": FLOW_DIAGRAM,
        "failure_handling": FAILURE_HANDLING,
        "warnings": warnings,
        "recommendations": recommendations,
    })
