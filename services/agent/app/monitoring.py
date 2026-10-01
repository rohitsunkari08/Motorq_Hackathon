"""Prometheus Observability for Agent Service."""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

AGENT_REQUESTS_TOTAL = Counter(
    "agent_requests_total",
    "Total agent chat requests",
    ["role", "status"],
)

AGENT_REQUEST_DURATION_SECONDS = Histogram(
    "agent_request_duration_seconds",
    "Agent chat request duration in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "agent_tool_calls_total",
    "Total tool calls executed by the agent",
    ["tool", "status"],
)

AGENT_TOOL_DURATION_SECONDS = Histogram(
    "agent_tool_duration_seconds",
    "Agent tool execution duration in seconds",
    ["tool"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

AGENT_PROMPT_INJECTIONS_BLOCKED_TOTAL = Counter(
    "agent_prompt_injections_blocked_total",
    "Total prompt injection or guardrail violations blocked",
    ["reason"],
)

AGENT_TOKENS_TOTAL = Counter(
    "agent_tokens_total",
    "Total tokens consumed by agent",
    ["type"],
)

AGENT_FALLBACK_TOTAL = Counter(
    "agent_fallback_total",
    "Total times deterministic fallback was engaged",
    ["reason"],
)

AGENT_ESTIMATED_COST_USD = Counter(
    "agent_estimated_cost_usd",
    "Estimated total cost in USD for LLM usage",
)


def get_metrics():
    return generate_latest()
