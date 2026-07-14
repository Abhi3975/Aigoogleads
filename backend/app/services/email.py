"""Email dispatch (SMTP via aiosmtplib).

If SMTP is not configured, sending is skipped and logged — the app degrades
gracefully in local/dev without a mail server.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_email(*, to: str, subject: str, html: str, text: str | None = None) -> bool:
    if not settings.SMTP_HOST:
        logger.info("email_skipped_no_smtp", to=to, subject=subject)
        return False

    from email.message import EmailMessage

    import aiosmtplib

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text or "This message requires an HTML-capable client.")
    message.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_PORT == 587,
        )
        return True
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("email_send_failed", to=to, error=str(exc))
        return False
