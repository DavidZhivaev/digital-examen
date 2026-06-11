from tortoise import fields, models


class Room(models.Model):
    id = fields.IntField(pk=True)

    corpus = fields.IntField()
    number = fields.IntField()

    rows = fields.IntField()
    columns = fields.IntField()

    it = fields.BooleanField(default=False)

    class Meta:
        table = "rooms"
        unique_together = (("corpus", "number", "it"),)