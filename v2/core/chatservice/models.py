# -*- coding: utf-8 -*-
import datetime, json, django
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from core.golfcourse.models import *
from .managers import *
from .utils import *
try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

class UserChatPresence(models.Model):
    user = models.ForeignKey(User, related_name='userchat_presence', blank=True, null=True, db_index=True)
    room_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    modified_at = models.DateTimeField(default=now, null=True, blank=True)
    objects = UserChatPresenceManager()

    def __str__(self):
        name = self.user.user_profile.display_name if self.user.user_profile and self.user.user_profile.display_name else self.user.username
        return "{0}--{1}--{2}".format(name, self.room_id, self.status)

    def save(self, *args, **kwargs):
        self.modified_at = now()
        return super(UserChatPresence, self).save(*args, **kwargs)
