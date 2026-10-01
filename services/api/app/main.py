"""FastAPI Application Main Entrypoint
Per NOTE.md §6.3:
- Hexagonal architecture
- OpenAPI published
- Versioned /api/v1
- RFC 7807 error responses
- Keyset pagination
- Rate limiting
- Security headers & CORS
- Health, Readiness & Prometheus metrics endpoints
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from services.api.app.config import settings
from services.api.app.api.dto.problem import ProblemDetails, ApiException
from services.api.app.api.v1 import api_v1_router
from services.api.app.infra.postgres import postgres_client
from services.api.app.infra.redis import redis_client
from services.api.app.infra.clickhouse import clickhouse_client
from services.api.app.domain.rate_limit.token_bucket import rate_limiter
from services.api.app.application.charger_service import charger_service
from services.api.app.monitoring import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    get_metrics_content,
    CONTENT_TYPE_LATEST,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize connections and pre-warm indexes
    try:
        await postgres_client.init_pool()
    except Exception as e:
        print(f"Warning: Postgres pool init failed: {e}")

    try:
        await redis_client.init()
        if redis_client.redis:
            rate_limiter.set_redis(redis_client.redis)
    except Exception as e:
        print(f"Warning: Redis init failed: {e}")

    try:
        await charger_service.get_spatial_index()
    except Exception as e:
        print(f"Warning: Charger spatial index pre-warm failed: {e}")

    yield

    # Shutdown
    await redis_client.close()
    await postgres_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="High-performance secure multi-tenant API for EV Fleet Charging & Battery-Health Copilot",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers & Prometheus Metrics Middleware
class SecurityAndObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        path = request.url.path

        response = await call_next(request)

        duration = time.time() - start_time

        # Security Headers per NOTE.md §7
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Prometheus metrics recording (exclude /metrics to avoid scrape bias)
        if path != "/metrics":
            status_code = str(response.status_code)
            HTTP_REQUESTS_TOTAL.labels(method=request.method, path=path, status=status_code).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path).observe(duration)

        return response


app.add_middleware(SecurityAndObservabilityMiddleware)


# RFC 7807 Exception Handlers
@app.exception_handler(ApiException)
async def api_exception_handler(request: Request, exc: ApiException):
    problem = exc.to_problem_details()
    problem.instance = request.url.path
    return JSONResponse(
        status_code=exc.status,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json", **exc.headers},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    invalid_params = []
    for err in exc.errors():
        invalid_params.append({
            "name": ".".join(str(loc) for loc in err["loc"]),
            "reason": err["msg"],
            "type": err["type"],
        })
    problem = ProblemDetails(
        type="https://api.evc.io/errors/422",
        title="Unprocessable Entity",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Request input validation failed",
        instance=request.url.path,
        invalid_params=invalid_params,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    problem = ProblemDetails(
        type="https://api.evc.io/errors/500",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


# Health, Readiness, and Metrics Endpoints
@app.get("/health", tags=["Monitoring"])
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/ready", tags=["Monitoring"])
async def ready():
    services_status = {}
    is_ready = True

    # Check Postgres
    try:
        if postgres_client.pool:
            async with postgres_client.pool.acquire() as conn:
                await conn.fetchval("SELECT 1;")
            services_status["postgres"] = "up"
        else:
            services_status["postgres"] = "down"
            is_ready = False
    except Exception:
        services_status["postgres"] = "down"
        is_ready = False

    # Check Redis
    try:
        if redis_client.redis:
            await redis_client.redis.ping()
            services_status["redis"] = "up"
        else:
            services_status["redis"] = "down"
            is_ready = False
    except Exception:
        services_status["redis"] = "down"
        is_ready = False

    # Check ClickHouse
    try:
        res = await clickhouse_client.query("SELECT 1")
        services_status["clickhouse"] = "up" if res.result_rows else "down"
    except Exception:
        services_status["clickhouse"] = "degraded"

    code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=code,
        content={"status": "ready" if is_ready else "not_ready", "services": services_status},
    )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    return Response(content=get_metrics_content(), media_type=CONTENT_TYPE_LATEST)


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
