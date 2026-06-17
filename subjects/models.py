from tortoise import fields, models


class Subject(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)

    creator = fields.ForeignKeyField(
        "models.User",
        related_name="created_subjects",
        on_delete=fields.CASCADE,
    )

    teachers = fields.ManyToManyField(
        "models.User",
        related_name="subjects_as_teacher",
        through="subject_teachers",
    )

    admins = fields.ManyToManyField(
        "models.User",
        related_name="subjects_as_admin",
        through="subject_admins",
    )

    class Meta:
        table = "subjects"