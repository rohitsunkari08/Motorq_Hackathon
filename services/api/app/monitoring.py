"""Prometheus Metrics Definitions and Exposition."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.5, 5.0],
)

CH_CIRCUIT_BREAKER_TRIPPED_TOTAL = Counter(
    "ch_circuit_breaker_tripped_total",
    "Total times the ClickHouse circuit breaker has tripped to OPEN",
)

RATE_LIMIT_EXCEEDED_TOTAL = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit rejections (HTTP 429)",
    ["route"],
)

PRIVACY_ERASURE_REQUESTS_TOTAL = Counter(
    "privacy_erasure_requests_total",
    "Total GDPR/DPDP privacy erasure operations",
    ["status"],
)

AUDIT_EVENTS_TOTAL = Counter(
    "audit_events_total",
    "Total audit trail events logged",
    ["actor_type", "action"],
)

SSE_ACTIVE_CONNECTIONS = Gauge(
    "sse_active_connections",
    "Number of active SSE alert stream connections",
)


def get_metrics_content() -> bytes:
    """Generate latest Prometheus metrics."""
    return generate_latest()
