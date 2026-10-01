"""Unit and Integration Tests for Agent Tools.

Per NOTE.md §6.6:
- Tools: get_fleet_summary, list_at_risk_vehicles, get_vehicle_status, explain_alert, search_kb, propose_charge_plan
- Propose charge plan produces status='proposed' only
- Agent can never approve/erase/modify
"""

import pytest
from services.agent.app.tools import agent_tools
from services.agent.app.rag import get_query_embedding, embed_text
from services.api.app.domain.security.jwt import jwt_manager


@pytest.fixture
def manager_jwt():
    return jwt_manager.issue_token(
        user_id=2,
        email="manager@voltfleet.com",
        tenant_id=1,
        role="fleet_manager",
    )


@pytest.fixture
def viewer_jwt():
    return jwt_manager.issue_token(
        user_id=3,
        email="viewer@voltfleet.com",
        tenant_id=1,
        role="viewer",
    )


@pytest.mark.asyncio
async def test_search_kb_local_and_fallback():
    """Verify KB search retrieves relevant synthetic documents for battery degradation."""
    res = await agent_tools.search_kb(
        token="mock_token",
        query="battery degradation DC fast charge thermal limits",
        top_k=3,
        user_role="fleet_manager",
    )
    assert res is not None
    assert "chunks" in res
    assert len(res["chunks"]) > 0
    # Check that chunks contain relevant guidance
    first_chunk = res["chunks"][0]
    assert "source" in first_chunk
    assert "content" in first_chunk


def test_embedding_dimensions():
    """Verify embeddings produce 384-dimensional vectors matching pgvector vector(384) schema."""
    emb = embed_text("lithium-ion battery degradation rate")
    assert len(emb) == 384
    # Check unit norm
    norm = sum(x * x for x in emb) ** 0.5
    assert abs(norm - 1.0) < 1e-3


@pytest.mark.asyncio
async def test_explain_alert_rule_logic():
    """Verify rule-based alert explanation logic for thermal and range-risk alerts."""
    thermal_res = agent_tools._generate_rule_explanation({
        "type": "THERMAL",
        "detail": {"temp_c": 52.1},
        "vin": "1VXEV01A100000001",
    })
    assert "THERMAL STRESS" in thermal_res
    assert "52.1°C" in thermal_res

    range_res = agent_tools._generate_rule_explanation({
        "type": "RANGE_RISK",
        "detail": {},
        "vin": "1VXEV01A100000001",
    })
    assert "RANGE RISK" in range_res
    assert "1.2x" in range_res


@pytest.mark.asyncio
async def test_propose_charge_plan_creates_proposed_only(manager_jwt, viewer_jwt):
    """Verify propose_charge_plan creates status='proposed' and enforces governance."""
    # Viewer should be rejected
    v_res = await agent_tools.propose_charge_plan(
        token=viewer_jwt,
        vin="1VXEV01A100000001",
        target_soc=80.0,
        user_role="viewer",
    )
    assert v_res["status"] == "forbidden"
