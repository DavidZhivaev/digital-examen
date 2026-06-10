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
    group_first = fields.JSONField(default=list)
    group_second = fields.JSONField(default=list)
    history = fields.JSONField(default=list)
    corpus = fields.IntField(default=1)

    class Meta:
        table = "classes"
        unique_together = (("parallel", "litera", "corpus"),)

    @property
    def display_name(self) -> str:
        return f"{self.parallel}{self.litera}"
