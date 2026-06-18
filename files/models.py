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