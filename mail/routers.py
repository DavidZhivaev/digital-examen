from fastapi import APIRouter, Query

from core.config import settings
from core.permissions import min_perms
from mail.gmail_service import fetch_unread_emails, send_email
from mail.schemas import SendEmailRequest, UnreadEmailResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "service": "mail",
        "status": "ok",
        "gmail_configured": settings.GMAIL_ENABLED and bool(settings.GMAIL_EMAIL),
    }


@router.post("/send", status_code=204)
@min_perms(settings.OPERATOR_ROLE)
async def send_mail(body: SendEmailRequest):
    await send_email(to=body.to, subject=body.subject, body=body.body, html=body.html)


@router.get("/unread", response_model=list[UnreadEmailResponse])
@min_perms(settings.OPERATOR_ROLE)
async def get_unread(limit: int = Query(50, ge=1, le=200)):
    emails = await fetch_unread_emails(limit=limit)
    return [UnreadEmailResponse.model_validate(item) for item in emails]
