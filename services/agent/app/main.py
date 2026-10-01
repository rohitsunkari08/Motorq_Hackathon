"""FastAPI Main Entrypoint for Agent Service.

Per NOTE.md §6.6:
- Exposes /chat endpoint for Copilot natural language queries
- Validates delegated JWT token
- Runs LangGraph workflow with strict guardrails
- Exposes Prometheus metrics and health checks
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.agent.app.config import settings
from services.agent.app.graph import agent_graph
from services.agent.app.rag import index_kb_documents
from services.agent.app.monitoring import get_metrics, CONTENT_TYPE_LATEST
from services.api.app.domain.security.jwt import jwt_manager, TokenClaims


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Index KB docs into pgvector if database is reachable
    try:
        count = await index_kb_documents(settings.POSTGRES_URL)
        print(f"Indexed {count} KB chunks into pgvector doc_chunk table.")
    except Exception as e:
        print(f"Warning: KB indexing at startup deferred (DB connection: {e})")
    yield


app = FastAPI(
    title="EV Fleet Copilot Agent Service",
    version="1.0.0",
    description="LangGraph & LiteLLM-powered Fleet Copilot with strict security guardrails",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Natural language fleet inquiry")


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    guardrails: Dict[str, bool] = {
        "delegatedJwt": True,
        "roleChecked": True,
        "readOnlyEnforced": True,
        "maskingApplied": True,
    }
    blocked: bool = False
    is_fallback: bool = False
    latency_seconds: float = 0.0


def extract_claims(authorization: Optional[str]) -> Tuple[TokenClaims, str]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer JWT token",
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must follow Bearer <token> format",
        )
    raw_token = parts[1]
    try:
        claims = jwt_manager.verify_token(raw_token)
        return claims, raw_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired JWT token: {e}",
        )


@app.post("/chat", response_model=ChatResponse)
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
):
    """Execute natural language query through LangGraph agent workflow with guardrails."""
    claims, raw_token = extract_claims(authorization)

    result = await agent_graph.execute(
        prompt=req.prompt,
        token=raw_token,
        user_role=claims.role,
        tenant_id=claims.tenant_id,
        actor_email=claims.email,
    )

    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        guardrails={
            "delegatedJwt": True,
            "roleChecked": True,
            "readOnlyEnforced": True,
            "maskingApplied": claims.role == "viewer",
        },
        blocked=result.get("blocked", False),
        is_fallback=result.get("is_fallback", False),
        latency_seconds=result.get("latency_seconds", 0.0),
    )


@app.post("/index-kb")
async def trigger_index_kb(authorization: Optional[str] = Header(None)):
    """Admin endpoint to reindex markdown documentation into pgvector."""
    claims, _ = extract_claims(authorization)
    if claims.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to trigger KB indexing.")

    count = await index_kb_documents(settings.POSTGRES_URL)
    return {"status": "success", "chunks_indexed": count}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent", "version": "1.0.0"}


@app.get("/ready")
async def ready():
    return {"status": "ready", "service": "agent"}


@app.get("/metrics")
async def metrics():
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)
