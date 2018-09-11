# -*- coding: utf-8 -*-
import datetime, json, django
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from core.golfcourse.models import *
from core.booking.models import *

from core.booking.models import BookedGolfcourseEvent
from core.game.models import EventMember
from core.teetime.models import TeeTime

'''
Minh add 
@ booked GC event history
'''

class BookedGolfcourseEvent_History(models.Model):
    booked_gcevent = models.IntegerField(default=0, db_index=True)
    member = models.ForeignKey(EventMember, related_name='booked_gc_event_his', blank=True, null=True, db_index=True)
    discount = models.FloatField(default=0)
    total_cost = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)

    payment_type = models.CharField(max_length=1, choices=PAYMENT_CHOICES, default=NOPAY)
    book_type = models.CharField(max_length=1, choices=BOOK_CHOICES, default=ONLINE)
    payment_status = models.BooleanField(default=False)
    url = models.URLField(null=True, blank=True)
    qr_image = models.ImageField(upload_to="qr_codes/", null=True, blank=True, editable=False)
    qr_base64 = models.TextField(editable=False)
    qr_url = models.URLField(null=True, blank=True)

    created = models.DateTimeField(null=True, blank=True, editable=False)
    modified = models.DateTimeField(null=True, blank=True)
    reservation_code = models.TextField(editable=False, unique=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default=BOOKING_REQUEST)
    user_device = models.CharField(max_length=3, blank=True, null=True, default='web')

    cancel_on = models.DateTimeField(null=True, blank=True, editable=False)


    def save(self, *args, **kwargs):
        if not self.id:
            self.cancel_on = datetime.datetime.today()
        return super(BookedGolfcourseEvent_History, self).save(*args, **kwargs)