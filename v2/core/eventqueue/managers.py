# -*- coding: utf-8 -*-
import datetime
import time

from django.db import models
from django.db.models import Q

class EventQueueManager(models.Manager):
    def __getattr__(self, attr, *args, **kwargs):
        #if attr in QUESTIONAIR_PROXY_METHODS:
        #    return getattr(self.get_queryset(), attr, None)
        super(EventQueueManager, self).__getattr__(*args, **kwargs)

    #def get_queryset(self):
    #    return RequestQuerySet(self.model)

    def get_eventqueue(self, **options):
        qs = self.filter(is_created=False,**options)
        return qs