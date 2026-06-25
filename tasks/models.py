import secrets
import string

from tortoise import fields, models


TASK_CODE_ALPHABET = string.digits + string.ascii_uppercase


def generate_task_code() -> str:
    return "".join(secrets.choice(TASK_CODE_ALPHABET) for _ in range(6))


class TaskBank(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255, default="Банк задач")
    subject = fields.ForeignKeyField("models.Subject", related_name="task_banks", on_delete=fields.CASCADE)
    parallel = fields.IntField()

    is_global = fields.BooleanField(default=True)
    is_open = fields.BooleanField(default=False)
    visibility_percent = fields.IntField(default=100)
    positions_count = fields.IntField()
    created_by = fields.ForeignKeyField("models.User", related_name="created_task_banks", on_delete=fields.CASCADE)

    access_teachers = fields.ManyToManyField(
        "models.User",
        related_name="accessible_task_banks",
        through="task_bank_teachers",
    )

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "task_banks"

class TaskPosition(models.Model):
    id = fields.IntField(pk=True)
    bank = fields.ForeignKeyField("models.TaskBank", related_name="positions", on_delete=fields.CASCADE)
    order = fields.IntField()
    min_score = fields.FloatField(default=0.0)
    max_score = fields.FloatField(default=12.0)
    criteria_text = fields.TextField(null=True)
    scoring = fields.JSONField(default=list)

    class Meta:
        table = "task_positions"
        unique_together = ("bank", "order")

class Task(models.Model):
    id = fields.UUIDField(pk=True)
    code = fields.CharField(max_length=6, unique=True, index=True, default=generate_task_code)

    position = fields.ForeignKeyField(
        "models.TaskPosition",
        related_name="tasks",
        on_delete=fields.CASCADE
    )

    author = fields.ForeignKeyField(
        "models.User",
        related_name="tasks",
        on_delete=fields.CASCADE
    )

    text = fields.TextField()
    solution = fields.TextField(null=True)
    answer = fields.TextField(null=True)

    version = fields.IntField(default=1)

    image_url = fields.CharField(max_length=512, null=True)
    image_scale = fields.FloatField(null=True)
    image_position = fields.CharField(max_length=20, null=True)

    status = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    is_deleted = fields.BooleanField(default=False)
    deleted_at = fields.DatetimeField(null=True)
    deleted_by = fields.ForeignKeyField(
        "models.User",
        related_name="deleted_tasks",
        null=True,
        on_delete=fields.SET_NULL
    )

    class Meta:
        table = "tasks"


class TaskRevision(models.Model):
    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField(
        "models.Task",
        related_name="revisions",
        on_delete=fields.CASCADE
    )

    version = fields.IntField()

    text = fields.TextField()
    solution = fields.TextField(null=True)
    answer = fields.TextField(null=True)

    image_url = fields.CharField(
        max_length=512,
        null=True
    )
    image_scale = fields.FloatField(
        null=True
    )
    image_position = fields.CharField(
        max_length=20,
        null=True
    )
    status = fields.IntField()
    changed_by = fields.ForeignKeyField(
        "models.User",
        related_name="task_revisions",
        on_delete=fields.SET_NULL,
        null=True
    )

    created_at = fields.DatetimeField(
        auto_now_add=True
    )

    class Meta:
        table = "task_revisions"
        unique_together = (
            "task",
            "version"
        )


class TaskReview(models.Model):
    id = fields.IntField(pk=True)

    task = fields.ForeignKeyField(
        "models.Task",
        related_name="reviews",
        on_delete=fields.CASCADE
    )

    moderator = fields.ForeignKeyField(
        "models.User",
        related_name="task_reviews",
        on_delete=fields.SET_NULL,
        null=True
    )

    action = fields.CharField(
        max_length=32
    )

    comment = fields.TextField(null=True)
    created_at = fields.DatetimeField(
        auto_now_add=True
    )

    class Meta:
        table = "task_reviews"
