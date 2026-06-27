from tortoise import fields, models


class AuditEvent(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField(null=True, index=True)
    person_id = fields.CharField(max_length=36, null=True)
    role = fields.IntField(null=True)
    method = fields.CharField(max_length=12)
    path = fields.CharField(max_length=512)
    status = fields.IntField()
    action = fields.CharField(max_length=255)
    details = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "audit_events"
        indexes = (("user_id", "created_at"),)

