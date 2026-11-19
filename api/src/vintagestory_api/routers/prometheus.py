"""Prometheus metrics at the root, open like /healthz (Epic 22 ADR-3)."""

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_PLAIN_0_0_4, CollectorRegistry, generate_latest

from vintagestory_api.services.prometheus_metrics import get_metrics_registry

router = APIRouter(tags=["Metrics"])


@router.get("/metrics", response_class=Response)
async def prometheus_metrics(
    registry: CollectorRegistry = Depends(get_metrics_registry),
) -> Response:
    """The game server's and the manager's metrics in the Prometheus text format.

    No authentication (Epic 22 ADR-3 decision 6). Values are read at each scrape.
    """
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_PLAIN_0_0_4)
