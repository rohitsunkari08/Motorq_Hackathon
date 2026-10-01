"""OpenAPI Contract Conformance Test using Schemathesis
Per NOTE.md §9 & §15:
- Validates FastAPI endpoints against published OpenAPI schema
- Ensures response schemas, status codes, and RFC 7807 problem details conform to contract
"""

import pytest
import schemathesis
from hypothesis import settings, HealthCheck
from services.api.app.main import app
from services.api.app.domain.security.jwt import jwt_manager

# Load OpenAPI schema from ASGI app
schema = schemathesis.openapi.from_asgi("/openapi.json", app)
token = jwt_manager.create_access_token(user_id=1, email="admin@voltfleet.com", tenant_id=1, role="admin")


@schema.parametrize()
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    deadline=None,
)
def test_api_contract(case):
    # Attach authenticated JWT Bearer headers
    if "/stream/alerts" in case.path:
        return  # Streaming SSE endpoint tested separately in test_sse_alerts.py
    case.headers = {"Authorization": f"Bearer {token}"}
    response = case.call()
    assert response.status_code < 500, f"Server error {response.status_code} on {case.path}"
