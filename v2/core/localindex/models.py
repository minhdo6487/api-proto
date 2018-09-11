# -*- coding: utf-8 -*-
import datetime, json, django
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from core.golfcourse.models import *
from v2.core.geohash.fields import GeohashField
from v2.core.geohash.managers import GeoManager
from .managers import *
from .utils import *
try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

class LocalIndex(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='geoname_golfcourse', blank=True, null=True, db_index=True)
    user = models.ForeignKey(User, related_name='geoname_user', blank=True, null=True, db_index=True)
    geoname = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    modified_at = models.DateTimeField(default=now, null=True, blank=True, editable=False)
    objects = LocalIndexManager()
    def __str__(self):
        name = self.golfcourse.name if self.golfcourse else self.user.username
        return "{0}--{1}".format(name, self.geoname)

class LocalName(models.Model):
    place = models.CharField(max_length=100,blank=True,null=True)
    location_x = models.FloatField()
    location_y = models.FloatField()
    name = models.CharField(max_length=150,blank=True,null=True)
    admin_code = models.CharField(max_length=20,blank=True,null=True)
    location = GeohashField(null=True, blank=True)
    objects = GeoManager()
    def __str__(self):
        return "{0}--{1}".format(self.admin_code, self.name)