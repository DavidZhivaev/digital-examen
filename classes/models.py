from tortoise import fields, models


class SchoolClass(models.Model):
    id = fields.IntField(pk=True)

    teacher = fields.ForeignKeyField(
        "models.User",
        related_name="homeroom_classes",
        null=True,
        on_delete=fields.SET_NULL,
    )

    parallel = fields.IntField()
    litera = fields.CharField(max_length=8)
    corpus = fields.IntField(default=1)

    class Meta:
        table = "classes"
        unique_together = (("parallel", "litera", "corpus"),)

    @property
    def display_name(self) -> str:
        return f"{self.parallel}{self.litera}"


class StudentClassHistory(models.Model):
    id = fields.IntField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="class_history",
        on_delete=fields.CASCADE,
    )

    school_class = fields.ForeignKeyField(
        "models.SchoolClass",
        related_name="student_history",
        on_delete=fields.CASCADE,
    )

    group = fields.IntField()  # 1 или 2

    joined_at = fields.DatetimeField(auto_now_add=True)
    left_at = fields.DatetimeField(null=True)

    class Meta:
        table = "student_class_history"