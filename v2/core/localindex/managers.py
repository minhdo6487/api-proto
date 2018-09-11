# -*- coding: utf-8 -*-
import datetime
import time

from django.db import models
from django.db.models import Q
from geopy.distance import Distance
class LocalIndexManager(models.Manager):
    def __getattr__(self, attr, *args, **kwargs):
        #if attr in QUESTIONAIR_PROXY_METHODS:
        #    return getattr(self.get_queryset(), attr, None)
        super(EventQueueManager, self).__getattr__(*args, **kwargs)

    #def get_queryset(self):
    #    return RequestQuerySet(self.model)

    def get_nearby(self, **options):
        user_id = options.get('user_id', None)
        golfcourse_id = options.get('golfcourse_id', None)
        local = []
        if user_id:
            local += list(self.filter(user_id=user_id).values_list('geoname',flat=True))
        if golfcourse_id:
            local += list(self.filter(golfcourse_id=golfcourse_id).values_list('geoname', flat=True))
        local = list(set(local))
        qs = self.filter(geoname__in=local).values('user_id','golfcourse_id')
        return qs

class LocalNameManager(models.Manager):
    def __getattr__(self, attr, *args, **kwargs):
        #if attr in QUESTIONAIR_PROXY_METHODS:
        #    return getattr(self.get_queryset(), attr, None)
        super(LocalNameManager, self).__getattr__(*args, **kwargs)

    #def get_queryset(self):
    #    return RequestQuerySet(self.model)

    def get_geocode(self, *options):
        qs = self.filter(location__distance_lt=(tuple(options), Distance(miles=500))).order_by_distance()
        return qs