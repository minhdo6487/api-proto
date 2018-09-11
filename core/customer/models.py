from django.db import models

from core.golfcourse.models import GolfCourse

# from core.checkin.models import create_checkin

class Customer(models.Model):
    name = models.CharField(max_length=100,db_index=True)
    email = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    avatar = models.CharField(max_length=200, null=True, blank=True)
    handicap = models.FloatField(null=True, blank=True)
    golfcourse = models.ForeignKey(GolfCourse, null=True, blank=True)

    def __str__(self):
        return self.email if self.email else ""
