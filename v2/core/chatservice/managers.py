# -*- coding: utf-8 -*-
import datetime
import time

from django.db import models
from django.db.models import Q

class UserChatPresenceManager(models.Manager):
    def __getattr__(self, attr, *args, **kwargs):
        #if attr in QUESTIONAIR_PROXY_METHODS:
        #    return getattr(self.get_queryset(), attr, None)
        super(UserChatPresenceManager, self).__getattr__(*args, **kwargs)

    #def get_queryset(self):
    #    return RequestQuerySet(self.model)

    def get_offline(self, **options):
        options.update({'status':'offline'})
        qs = self.filter(Q(**options)).exclude(room_id__contains='_activity')
        return qs

    def get_online(self, **options):
        options.update({'status':'online'})
        qs = self.filter(Q(**options)).exclude(room_id__contains='_activity')
        return qs