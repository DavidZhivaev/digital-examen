from tortoise import fields, models


class BlankIssue(models.Model):
    id = fields.IntField(pk=True)

    work = fields.ForeignKeyField("models.Work", related_name="blank_issues", on_delete=fields.CASCADE)
    participant = fields.ForeignKeyField(
        "models.WorkParticipant",
        related_name="blank_issues",
        null=True,
        on_delete=fields.SET_NULL,
    )
    code = fields.CharField(max_length=13, index=True)
    kind = fields.CharField(max_length=32)
    print_type = fields.CharField(max_length=32, default="single-sided")
    issued_by = fields.ForeignKeyField(
        "models.User",
        related_name="issued_blanks",
        null=True,
        on_delete=fields.SET_NULL,
    )
    payload = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "blank_issues"
        unique_together = (("work", "code"),)
        indexes = (("work_id", "kind"),)
