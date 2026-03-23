# API-Integrated Intelligent Decision Agent

## API Flow Diagram

```text
Frontend
  -> POST /api/agent
  -> Request Parser
  -> Input Validation
  -> Calendar Availability Check
  -> Weather Validation
  -> CRM Logging
  -> Output Validator
  -> Frontend Dashboard
```

## Decision Logic

1. Parse the natural-language request into `intent`, `date`, `time`, `client_name`, and `city`.
2. Validate that the request is a scheduling request and that both `date` and `time` are present.
3. Query the calendar service to confirm slot availability and suggest alternatives if the slot is blocked.
4. Query the weather service to identify live weather risk for the meeting city.
5. Stop scheduling when weather risk is high, or continue in degraded mode when live weather data is unavailable.
6. Log the confirmed meeting in the CRM service and return a validated JSON response to the frontend.

## Failure Handling Approach

- Missing date or time returns a structured `fail` response with guidance on what the user should add.
- Busy or out-of-hours calendar slots return a blocked decision plus the next available alternatives.
- Weather API issues return a degraded warning instead of crashing the workflow.
- High-risk weather blocks CRM logging and asks the user to reschedule.
- CRM write failures return `partial_success` so the user can follow up manually.
- Every backend response is normalized and validated before it is sent to the frontend.
