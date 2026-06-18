from tortoise import fields, models

class TaskBank(models.Model):
    id = fields.IntField(pk=True)
    subject = fields.ForeignKeyField("models.Subject", related_name="task_banks", on_delete=fields.CASCADE)
    parallel = fields.IntField()
    is_open = fields.BooleanField(default=False)
    visibility_percent = fields.IntField(default=100)
    positions_count = fields.IntField()
    created_by = fields.ForeignKeyField("models.User", related_name="created_task_banks", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "task_banks"

class TaskPosition(models.Model):
    id = fields.IntField(pk=True)
    bank = fields.ForeignKeyField("models.TaskBank", related_name="positions", on_delete=fields.CASCADE)
    order = fields.IntField()
    min_score = fields.FloatField(default=0.0)
    max_score = fields.FloatField(default=1.0)

    class Meta:
        table = "task_positions"
        unique_together = ("bank", "order")

class Task(models.Model):
    id = fields.UUIDField(pk=True)
    
    position = fields.ForeignKeyField("models.TaskPosition", related_name="tasks", on_delete=fields.CASCADE)
    author = fields.ForeignKeyField("models.User", related_name="tasks", on_delete=fields.CASCADE)
    
    text = fields.TextField()
    solution = fields.TextField(null=True)
    answer = fields.TextField(null=True)

    image_url = fields.CharField(max_length=512, null=True)
    image_scale = fields.FloatField(null=True)
    image_position = fields.CharField(max_length=20, null=True)

    status = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "tasks"