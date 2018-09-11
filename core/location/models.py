from django.db import models

NORTHERN = 'N'
CENTRAL = 'C'
SOUTHERN = 'S'
TYPE_CHOICES = (
    (NORTHERN, 'northern'),
    (CENTRAL, 'central'),
    (SOUTHERN, 'southern'))


class Country(models.Model):
    name = models.TextField()
    flag = models.CharField(max_length=500, blank=True, null=True)
    short_name = models.CharField(max_length=5, blank=True, null=True, db_index=True)
    def __str__(self):
        return self.name


class City(models.Model):
    name = models.TextField()
    region = models.CharField(max_length=1, choices=TYPE_CHOICES, default=SOUTHERN, null=True, blank=True)
    country = models.ForeignKey(Country, related_name='City')
    updated = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class District(models.Model):
    name = models.TextField()
    city = models.ForeignKey(City, related_name='District')

    def __str__(self):
        return self.name