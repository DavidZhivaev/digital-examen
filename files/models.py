from tortoise import fields, models

class UploadedFile(models.Model):
    id = fields.UUIDField(pk=True)
    original_name = fields.CharField(max_length=255)
    file_path = fields.CharField(max_length=512)
    mime_type = fields.CharField(max_length=100, null=True)
    
    uploaded_by = fields.ForeignKeyField("models.User", related_name="uploaded_files", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "uploaded_files"


class WorkScan(models.Model):
    id = fields.UUIDField(pk=True)
    work_id = fields.UUIDField(index=True)
    work_number = fields.IntField()
    participant_code = fields.CharField(max_length=13, null=True, index=True)
    blank_code = fields.CharField(max_length=13, null=True, index=True)
    next_blank_code = fields.CharField(max_length=13, null=True)
    results = fields.JSONField(null=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "work_scans"
        unique_together = (("work_id", "work_number", "blank_code"),)
