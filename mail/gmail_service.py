import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from fastapi import HTTPException, status

from core.config import settings


def _ensure_gmail_configured() -> None:
    if not settings.GMAIL_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email-сервис отключён",
        )
    if not settings.GMAIL_EMAIL or not settings.GMAIL_APP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email не настроен (GMAIL_EMAIL / GMAIL_APP_PASSWORD)",
        )


def _send_email_sync(*, to: str, subject: str, body: str, html: str | None = None) -> None:
    message = MIMEMultipart("alternative")
    message["From"] = formataddr((settings.GMAIL_FROM_NAME, settings.GMAIL_EMAIL))
    message["To"] = to
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain", "utf-8"))

    if html:
        message.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.GMAIL_SMTP_HOST, settings.GMAIL_SMTP_PORT, timeout=5) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
        smtp.sendmail(settings.GMAIL_EMAIL, [to], message.as_string())


async def send_email(*, to: str, subject: str, body: str, html: str | None = None) -> None:
    _ensure_gmail_configured()
    await asyncio.to_thread(
        _send_email_sync,
        to=to,
        subject=subject,
        body=body,
        html=html,
    )


async def send_password_email(*, to: str, subject: str, greeting: str, link: str) -> None:
    body = (
        f"{greeting}\n\n"
        f"Установите пароль по ссылке:\n{link}\n\n"
        f"Срок действия: {settings.PASSWORD_TOKEN_EXPIRE_HOURS} ч.\n"
    )

    html = (
        f"<p>{greeting}</p>"
        f'<p><a href="{link}">Установить пароль</a></p>'
        f"<p>Срок действия: {settings.PASSWORD_TOKEN_EXPIRE_HOURS} ч.</p>"
    )

    await send_email(to=to, subject=subject, body=body, html=html)


async def send_notification_email(
    *,
    to: str,
    subject: str,
    message: str,
    html: str | None = None,
) -> None:
    """
    Универсальные уведомления пользователям (система/класс/события).
    """
    await send_email(to=to, subject=subject, body=message, html=html)