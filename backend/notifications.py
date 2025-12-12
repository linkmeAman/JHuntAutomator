import json
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Iterable, List

import requests

from .config import settings
from .models import CrawlRun, Job

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles optional email and Telegram digests for new jobs."""

    def __init__(self):
        self.notifications_enabled = settings.ENABLE_NOTIFICATIONS

    def _filter_jobs(self, jobs: Iterable[Job]) -> List[Job]:
        return [
            job
            for job in jobs
            if job.relevance_score >= settings.NOTIFICATION_MIN_SCORE
        ]

    def send_daily_digest(self, jobs: Iterable[Job]) -> None:
        if not self.notifications_enabled:
            logger.debug("Notifications disabled; skipping digest.")
            return

        filtered_jobs = self._filter_jobs(jobs)
        if not filtered_jobs:
            logger.info("No jobs met the notification threshold.")
            return

        body = self._build_summary_body(filtered_jobs)

        if settings.ENABLE_EMAIL_NOTIFICATIONS:
            self._send_email(body, len(filtered_jobs))

        if settings.ENABLE_TELEGRAM_NOTIFICATIONS:
            self._send_telegram(body)

    def send_run_alerts(self, run: CrawlRun) -> None:
        """Send alerts for failed sources or zero-result runs."""
        if not self.notifications_enabled:
            return

        alerts: List[str] = []
        failed_sources = self._safe_load_json(run.sources_failed, [])
        if failed_sources:
            failures = "; ".join(
                f"{item.get('source')}: {item.get('error')}" for item in failed_sources
            )
            alerts.append(f"Source failures: {failures}")

        if run.inserted_new_count == 0:
            alerts.append("Zero new jobs were inserted in the latest crawl.")

        if not alerts:
            return

        body = "\n".join(alerts)
        if settings.ENABLE_EMAIL_NOTIFICATIONS:
            self._send_email(body, 0, subject_override="Job crawl alerts")

        if settings.ENABLE_TELEGRAM_NOTIFICATIONS:
            self._send_telegram(body)

    def _build_summary_body(self, jobs: List[Job]) -> str:
        lines = []
        for job in jobs:
            lines.append(
                f"{job.title} — {job.company} [{job.location}] (score {job.relevance_score:.2f})\n{job.url}"
            )
            if job.keywords_matched:
                lines.append(f"Matches: {job.keywords_matched}")
            lines.append("")
        return "\n".join(lines).strip()

    def _send_email(self, body: str, count: int, subject_override: str | None = None) -> None:
        if not all([settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.EMAIL_SENDER, settings.EMAIL_RECIPIENT]):
            logger.warning("Email notifications enabled but SMTP credentials are incomplete.")
            return

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject_override or f"{count} new high-match IT roles"
        msg["From"] = settings.EMAIL_SENDER
        msg["To"] = settings.EMAIL_RECIPIENT

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
                logger.info("Email notification sent to %s", settings.EMAIL_RECIPIENT)
        except Exception as exc:
            logger.error("Failed to send email notification: %s", exc)

    def _send_telegram(self, body: str) -> None:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram notifications enabled but credentials are missing.")
            return

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": body,
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(url, data=payload, timeout=10)
            if response.status_code != 200:
                logger.error("Telegram API responded with %s: %s", response.status_code, response.text)
            else:
                logger.info("Telegram notification sent.")
        except Exception as exc:
            logger.error("Failed to send Telegram notification: %s", exc)

    @staticmethod
    def _safe_load_json(value, default):
        try:
            return json.loads(value) if value else default
        except Exception:
            return default
