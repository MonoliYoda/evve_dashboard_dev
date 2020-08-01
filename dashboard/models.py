from django.db import models
from datetime import datetime


class StructureName(models.Model):
    structure_id = models.IntegerField()
    structure_name = models.CharField(max_length=100)

    def __str__(self):
        return self.structure_name


class CharacterName(models.Model):
    character_id = models.IntegerField()
    character_name = models.CharField(max_length=100)

    def __str__(self):
        return self.character_name


class ContractShipName(models.Model):
    contract_id = models.IntegerField()
    ship_name = models.CharField(max_length=100)

    def __str__(self):
        return self.contract_id


class StructureTimer(models.Model):
    tid = models.IntegerField()
    timer_corp = models.IntegerField()
    location = models.CharField(max_length=100)
    timer_type = models.CharField(max_length=100)
    structure_type_id = models.IntegerField()
    structure_type_name = models.CharField(max_length=100)
    structure_name = models.CharField(max_length=100)
    structure_corp = models.IntegerField()
    time = models.DateTimeField()
    notes = models.CharField(max_length=500)

    def __str__(self):
        return ' '.join(self.structure_name, self.tid)


class ContractBids(models.Model):
    contract_id = models.IntegerField()
    bids = models.TextField(null=True)
    last_updated = models.DateTimeField(default=datetime.now)
