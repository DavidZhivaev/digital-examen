import uuid

from tortoise import fields, models


class User(models.Model):
    id = fields.IntField(pk=True)
    person_id = fields.CharField(max_length=36, unique=True, default=lambda: str(uuid.uuid4()))
    password_hash = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, unique=True)
    login = fields.CharField(max_length=255, unique=True)
    role = fields.IntField(default=1)
    register_at = fields.DatetimeField(auto_now_add=True)
    class_id = fields.IntField(null=True, source_field="class")
    class_group = fields.IntField(null=True)
    first_name = fields.CharField(max_length=255)
    last_name = fields.CharField(max_length=255)
    middle_name = fields.CharField(max_length=255, null=True)
    sex = fields.IntField(null=True)
    email_accept = fields.BooleanField(default=False)
    must_set_password = fields.BooleanField(default=False)
    last_do = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
