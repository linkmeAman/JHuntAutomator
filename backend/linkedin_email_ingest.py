import email
import logging
import os
import imaplib
from email import policy
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _extract_links_and_text(msg) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    body_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in {"text/plain", "text/html"}:
                try:
                    body_parts.append(part.get_content())
                except Exception:
                    continue
    else:
        try:
            body_parts.append(msg.get_content())
        except Exception:
            pass

    body = "\n".join([p if isinstance(p, str) else "" for p in body_parts])
    urls = []
    for token in body.split():
        if "linkedin.com" in token and token.startswith("http"):
            urls.append(token.strip(".,)\"'<>"))

    date_hdr = msg.get("Date")
    subject = msg.get("Subject", "").strip()
    first_url = urls[0] if urls else ""

    if first_url:
        jobs.append(
            {
                "title": subject or "LinkedIn Job Alert",
                "company": "",
                "location": "",
                "description": subject,
                "url": first_url,
                "source": "linkedin",
                "post_date": date_hdr,
                "remote": True,
                "source_meta": {"urls": urls, "subject": subject},
            }
        )
    return jobs


def parse_eml(raw_eml: str) -> List[Dict[str, Any]]:
    msg = email.message_from_string(raw_eml, policy=policy.default)
    return _extract_links_and_text(msg)


def fetch_via_imap(config: dict) -> List[Dict[str, Any]]:
    host = config.get("imap", {}).get("host", "")
    port = config.get("imap", {}).get("port", 993)
    username = config.get("imap", {}).get("username", "")
    password_env = config.get("imap", {}).get("password_env", "LINKEDIN_IMAP_PASSWORD")
    max_emails = config.get("max_emails_per_run", 30)

    if not host or not username:
        logger.warning("LinkedIn IMAP not configured; host/username missing.")
        return []

    password = os.getenv(password_env, "")
    if not password:
        logger.warning("LinkedIn IMAP password env %s not set.", password_env)
        return []

    jobs: List[Dict[str, Any]] = []
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(username, password)
        mail.select("inbox")
        search_criteria = config.get("query") or 'FROM "jobalerts-noreply@linkedin.com"'
        status, data = mail.search(None, "ALL")
        if status != "OK":
            logger.warning("LinkedIn IMAP search failed: %s", status)
            return []
        msg_ids = data[0].split()[:max_emails]
        for mid in msg_ids:
            status, msg_data = mail.fetch(mid, "(RFC822)")
            if status != "OK" or not msg_data:
                continue
            raw_email = msg_data[0][1].decode(errors="ignore")
            jobs.extend(parse_eml(raw_email))
        mail.logout()
    except Exception as exc:
        logger.error("LinkedIn IMAP fetch failed: %s", exc)
    return jobs
