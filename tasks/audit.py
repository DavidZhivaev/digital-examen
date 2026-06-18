import json
import logging
import uuid
from datetime import datetime, timezone

audit_logger = logging.getLogger("app.audit")
audit_logger.setLevel(logging.INFO)

if not audit_logger.handlers:
    handler = logging.StreamHandler()
    audit_logger.addHandler(handler)


def log_audit(
    user_id: int,
    user_role: int,
    action: str,
    task_id: uuid.UUID | None = None,
    bank_id: int | None = None,
    subject_id: int | None = None,
    details: dict | None = None,
):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "logger": "app.audit",
        "event": "task_lifecycle_event",
        "actor": {
            "user_id": user_id,
            "role": user_role,
        },
        "action": action,
        "target": {
            "task_id": str(task_id) if task_id else None,
            "bank_id": bank_id,
            "subject_id": subject_id,
        },
        "details": details or {},
    }
    
    audit_logger.info(json.dumps(payload, ensure_ascii=False))