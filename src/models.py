from tortoise import fields, models


class MachineStatus(models.Model):
    id = fields.IntField(pk=True)
    client_id = fields.CharField(max_length=100)
    machine_id = fields.CharField(max_length=100)
    running_programs = fields.JSONField()  # ← CAMPO NECESSÁRIO
    last_seen = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "machine_status"
        schema = "monitoring"
