"""Notification test endpoint (issue #5: test button for e-mail / webhook)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from ..dependencies import require_api_key
from ..schemas import NotificationTestResult
from ..services import notifications

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


@router.post(
    "/test",
    response_model=list[NotificationTestResult],
    dependencies=[Depends(require_api_key)],
)
def send_test_notification(
    channel: str | None = Query(
        default=None,
        description="Which channel to test: 'email', 'webhook', or omit for all.",
    ),
):
    """Send a test message to the configured notification channel(s).

    Returns one result per channel describing whether it is enabled and whether
    the test message was delivered (with an error detail on failure).
    """
    logger.info("Running notification test (channel=%s)", channel or "all")
    results = notifications.test_channels(channel)
    return [NotificationTestResult(**vars(r)) for r in results]
