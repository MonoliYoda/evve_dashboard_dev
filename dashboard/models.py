from django.db import models


class LocationName(models.Model):
    location_id = models.IntegerField()
    location_name = models.CharField(max_length=100)


class CharacterName(models.Model):
    character_id = models.IntegerField()
    character_name = models.CharField(max_length=100)


class ContractShipName(models.Model):
    contract_id = models.IntegerField()
    ship_name = models.CharField(max_length=100)


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


class PlanetName(models.Model):
    planet_id = models.IntegerField()
    planet_name = models.CharField(max_length=100)
