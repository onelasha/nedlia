"""Health check endpoints for Kubernetes/ECS probes."""

from datetime import datetime

from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get("/health/live")
async def liveness():
    """
    Liveness probe - Is the process alive?

    Used by ECS/Kubernetes to determine if container should be restarted.
    Should always return 200 if the process is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness():
    """
    Readiness probe - Can the service handle requests?

    Used by load balancer to determine if traffic should be routed.
    Checks all critical dependencies.
    """
    checks = {
        "database": await _check_database(),
        "redis": await _check_redis(),
    }

    all_ready = all(c["status"] == "ready" for c in checks.values())

    if not all_ready:
        return Response(
            content='{"status": "not_ready"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )

    return {
        "status": "ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _check_database() -> dict:
    """Check database connectivity."""
    # TODO: Implement actual database check
    # try:
    #     await db.execute("SELECT 1")
    #     return {"status": "ready", "latency_ms": 5}
    # except Exception as e:
    #     return {"status": "unhealthy", "error": str(e)}
    return {"status": "ready", "latency_ms": 0}


async def _check_redis() -> dict:
    """Check Redis connectivity."""
    # TODO: Implement actual Redis check
    # try:
    #     await redis.ping()
    #     return {"status": "ready"}
    # except Exception as e:
    #     return {"status": "unhealthy", "error": str(e)}
    return {"status": "ready"}
