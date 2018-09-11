from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from core.golfcourse.models import GolfCourse


class Checkin(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='checkin')
    reservation_code = models.CharField(max_length=100, blank=True, null=True)
    total_amount = models.PositiveIntegerField()
    play_number = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateField()
    time = models.TimeField()
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    player = generic.GenericForeignKey('content_type', 'object_id')