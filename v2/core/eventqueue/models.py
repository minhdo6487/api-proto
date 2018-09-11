# -*- coding: utf-8 -*-
import datetime, json, django
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from core.booking.models import *
from .managers import *
from .utils import *
from v2.api.eventMana.tasks import create_event_from_booking
try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

class EventQueue(models.Model):
    booking = models.ForeignKey(BookedTeeTime, related_name='event_booking', blank=True, null=True)
    user_email = models.EmailField(max_length=255, null=True, blank=True)
    is_created = models.BooleanField(default=False)
    is_pushnotify = models.BooleanField(default=False)
    objects = EventQueueManager()
    def __str__(self):
        return "{0}--{1}--{2}".format(self.booking.teetime.date, self.user_email, self.is_created)

post_save.connect(create_event_from_booking, sender=EventQueue)