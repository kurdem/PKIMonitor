"""APScheduler background worker wiring."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .services.monitoring import check_all_monitors, evaluate_alerts

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        check_all_monitors,
        trigger="interval",
        hours=settings.monitor_interval_hours,
        id="monitor_check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        evaluate_alerts,
        trigger="interval",
        hours=settings.alert_interval_hours,
        id="alert_eval",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started (monitors every %sh, alerts every %sh)",
        settings.monitor_interval_hours,
        settings.alert_interval_hours,
    )

    if settings.run_checks_on_startup:
        logger.info("Running initial monitor sweep on startup")
        scheduler.add_job(check_all_monitors, id="startup_check", replace_existing=True)
        scheduler.add_job(evaluate_alerts, id="startup_alerts", replace_existing=True)


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
