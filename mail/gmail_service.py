import asyncio
import email
import imaplib
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from fastapi import HTTPException, status

from core.config import settings


def _ensure_gmail_configured() -> None:
    if not settings.GMAIL_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Почта не настроена. Укажите GMAIL_ENABLED=true и данные Gmail в .env",
        )
    if not settings.GMAIL_EMAIL or not settings.GMAIL_APP_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Укажите GMAIL_EMAIL и GMAIL_APP_PASSWORD в .env",
        )


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for content, charset in parts:
        if isinstance(content, bytes):
            decoded.append(content.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(content)
    return "".join(decoded)


def _send_email_sync(*, to: str, subject: str, body: str, html: str | None = None) -> None:
    message = MIMEMultipart("alternative")
    message["From"] = formataddr((settings.GMAIL_FROM_NAME, settings.GMAIL_EMAIL))
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        message.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.GMAIL_SMTP_HOST, settings.GMAIL_SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
        smtp.sendmail(settings.GMAIL_EMAIL, [to], message.as_string())


def _fetch_unread_sync(limit: int = 50) -> list[dict]:
    with imaplib.IMAP4_SSL(settings.GMAIL_IMAP_HOST, settings.GMAIL_IMAP_PORT) as imap:
        imap.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
        imap.select("INBOX")
        status_code, data = imap.search(None, "UNSEEN")
        if status_code != "OK":
            return []

        ids = data[0].split()
        ids = ids[-limit:]
        messages = []
        for msg_id in reversed(ids):
            status_code, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status_code != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            parsed = email.message_from_bytes(raw)
            body = ""
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/plain" and not part.get_filename():
                        payload = part.get_payload(decode=True) or b""
                        body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                        break
            else:
                payload = parsed.get_payload(decode=True) or b""
                body = payload.decode(parsed.get_content_charset() or "utf-8", errors="replace")

            messages.append(
                {
                    "uid": msg_id.decode(),
                    "from": _decode_mime_header(parsed.get("From")),
                    "to": _decode_mime_header(parsed.get("To")),
                    "subject": _decode_mime_header(parsed.get("Subject")),
                    "date": _decode_mime_header(parsed.get("Date")),
                    "body": body.strip(),
                }
            )
        return messages


async def send_email(*, to: str, subject: str, body: str, html: str | None = None) -> None:
    _ensure_gmail_configured()
    await asyncio.to_thread(
        _send_email_sync,
        to=to,
        subject=subject,
        body=body,
        html=html,
    )


async def fetch_unread_emails(limit: int = 50) -> list[dict]:
    _ensure_gmail_configured()
    return await asyncio.to_thread(_fetch_unread_sync, limit)


async def send_password_email(*, to: str, subject: str, greeting: str, link: str) -> None:
    body = (
        f"{greeting}\n\n"
        f"Перейдите по ссылке для установки пароля:\n{link}\n\n"
        f"Ссылка действует {settings.PASSWORD_TOKEN_EXPIRE_HOURS} ч.\n"
        f"Если вы не запрашивали это письмо, проигнорируйте его."
    )
    html = (
        f"<p>{greeting}</p>"
        f'<p><a href="{link}">Установить пароль</a></p>'
        f"<p>Ссылка действует {settings.PASSWORD_TOKEN_EXPIRE_HOURS} ч.</p>"
    )
    await send_email(to=to, subject=subject, body=body, html=html)
