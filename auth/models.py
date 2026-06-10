from tortoise import fields, models


class Session(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="sessions", on_delete=fields.CASCADE)
    refresh_token_hash = fields.CharField(max_length=64)
    device_name = fields.CharField(max_length=255, null=True)
    user_agent = fields.CharField(max_length=512, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField()
    revoked_at = fields.DatetimeField(null=True)

    class Meta:
        table = "sessions"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class PasswordToken(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="password_tokens", on_delete=fields.CASCADE)
    token_hash = fields.CharField(max_length=64)
    purpose = fields.CharField(max_length=20)
    expires_at = fields.DatetimeField()
    used_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "password_tokens"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
