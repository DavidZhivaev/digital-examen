import uuid

from tortoise import fields, models


class Work(models.Model):
    id = fields.IntField(pk=True)
    work_id = fields.CharField(
        max_length=36,
        unique=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_works",
        on_delete=fields.RESTRICT,
    )
    subject = fields.CharField(max_length=16)
    conduct_date = fields.DateField()
    work_type_id = fields.CharField(max_length=64)
    work_type_name = fields.CharField(max_length=255)
    questions = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "works"


class WorkParticipant(models.Model):
    id = fields.IntField(pk=True)
    work = fields.ForeignKeyField(
        "models.Work",
        related_name="participants",
        on_delete=fields.CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.User",
        related_name="work_participations",
        on_delete=fields.CASCADE,
    )
    notified = fields.BooleanField(default=False)
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "work_participants"
        unique_together = (("work", "user"),)


class WorkRoom(models.Model):
    id = fields.IntField(pk=True)
    work = fields.ForeignKeyField(
        "models.Work",
        related_name="work_rooms",
        on_delete=fields.CASCADE,
    )
    room = fields.ForeignKeyField(
        "models.Room",
        related_name="work_assignments",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "work_rooms"
        unique_together = (("work", "room"),)


class WorkSupervisor(models.Model):
    id = fields.IntField(pk=True)
    work = fields.ForeignKeyField(
        "models.Work",
        related_name="supervisors",
        on_delete=fields.CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.User",
        related_name="supervised_works",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "work_supervisors"
        unique_together = (("work", "user"),)


class WorkSeating(models.Model):
    id = fields.IntField(pk=True)
    work = fields.OneToOneField(
        "models.Work",
        related_name="seating",
        on_delete=fields.CASCADE,
    )
    plan_json = fields.TextField()
    generated_at = fields.DatetimeField(auto_now_add=True)
    generated_by = fields.ForeignKeyField(
        "models.User",
        related_name="generated_seatings",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = "work_seatings"
