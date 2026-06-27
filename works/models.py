import uuid

from tortoise import fields, models


def default_grading_scale() -> list[dict]:
    return [
        {"grade": 2, "min_points": 0, "min_clean_pluses": None},
        {"grade": 3, "min_points": 0, "min_clean_pluses": None},
        {"grade": 4, "min_points": 0, "min_clean_pluses": None},
        {"grade": 5, "min_points": 0, "min_clean_pluses": None},
    ]


class Work(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    title = fields.CharField(max_length=255)
    subject = fields.ForeignKeyField("models.Subject", related_name="works", on_delete=fields.CASCADE)
    task_bank = fields.ForeignKeyField(
        "models.TaskBank",
        related_name="works",
        null=True,
        on_delete=fields.SET_NULL,
    )

    task_count = fields.IntField()
    written_task_count = fields.IntField(default=0)
    variant_count = fields.IntField(null=True)
    scheduled_at = fields.DatetimeField()
    test_config_key = fields.CharField(max_length=255, null=True)
    send_notifications = fields.BooleanField(default=False)
    grading_scale = fields.JSONField(default=default_grading_scale)

    creator = fields.ForeignKeyField("models.User", related_name="created_works", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "works"
        indexes = (("subject_id", "scheduled_at"),)


class WorkRoom(models.Model):
    id = fields.IntField(pk=True)

    work = fields.ForeignKeyField("models.Work", related_name="rooms", on_delete=fields.CASCADE)
    room = fields.ForeignKeyField("models.Room", related_name="work_rooms", on_delete=fields.CASCADE)
    observer = fields.ForeignKeyField(
        "models.User",
        related_name="observed_work_rooms",
        null=True,
        on_delete=fields.SET_NULL,
    )

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "work_rooms"
        unique_together = (("work", "room"),)


class WorkParticipant(models.Model):
    id = fields.IntField(pk=True)

    work = fields.ForeignKeyField("models.Work", related_name="participants", on_delete=fields.CASCADE)
    student = fields.ForeignKeyField("models.User", related_name="work_participations", on_delete=fields.CASCADE)
    room = fields.ForeignKeyField("models.Room", related_name="work_participants", null=True, on_delete=fields.SET_NULL)

    seat = fields.CharField(max_length=16, null=True)
    work_number = fields.IntField()
    participant_code = fields.CharField(max_length=13, unique=True, index=True)
    variant_number = fields.IntField(null=True)
    variant_tasks = fields.JSONField(default=dict)
    blank_chain = fields.JSONField(default=dict)
    points = fields.JSONField(default=dict)
    clean_pluses = fields.IntField(default=0)
    percent = fields.FloatField(null=True)
    grade = fields.FloatField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "work_participants"
        unique_together = (("work", "student"), ("work", "work_number"))
        indexes = (("work_id", "student_id"), ("work_id", "participant_code"))


class WorkTestReviewer(models.Model):
    id = fields.IntField(pk=True)

    work = fields.ForeignKeyField("models.Work", related_name="test_reviewers", on_delete=fields.CASCADE)
    user = fields.ForeignKeyField("models.User", related_name="test_review_works", on_delete=fields.CASCADE)
    assigned_by = fields.ForeignKeyField(
        "models.User",
        related_name="assigned_test_reviewers",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "work_test_reviewers"
        unique_together = (("work", "user"),)


class WorkRecognitionItem(models.Model):
    id = fields.IntField(pk=True)

    work = fields.ForeignKeyField("models.Work", related_name="recognition_items", on_delete=fields.CASCADE)
    scan_id = fields.UUIDField(null=True, index=True)
    work_number = fields.IntField()
    participant_code = fields.CharField(max_length=13, null=True, index=True)
    position = fields.IntField()

    expected_chars = fields.CharField(max_length=255)
    suggested_text = fields.CharField(max_length=255, null=True)
    confirmed_text = fields.CharField(max_length=255, null=True)
    fragment_url = fields.CharField(max_length=512, null=True)

    status = fields.CharField(max_length=32, default="pending")
    assigned_to = fields.ForeignKeyField(
        "models.User",
        related_name="assigned_recognition_items",
        null=True,
        on_delete=fields.SET_NULL,
    )
    confirmed_by = fields.ForeignKeyField(
        "models.User",
        related_name="confirmed_recognition_items",
        null=True,
        on_delete=fields.SET_NULL,
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "work_recognition_items"
        indexes = (("work_id", "status"), ("work_id", "assigned_to_id"))
