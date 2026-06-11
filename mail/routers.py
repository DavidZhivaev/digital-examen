from fastapi import APIRouter, status

from core.config import settings
from core.permissions import min_perms
from mail.gmail_service import send_email
from mail.schemas import SendEmailRequest

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "service": "mail",
        "status": "ok",
        "enabled": settings.GMAIL_ENABLED,
    }


@router.post("/send", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.OPERATOR_ROLE)
async def send_mail(body: SendEmailRequest):
    await send_email(
        to=body.to,
        subject=body.subject,
        body=body.message,
        html=body.html,
    )
    return None