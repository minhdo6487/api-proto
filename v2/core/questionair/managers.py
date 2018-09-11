# -*- coding: utf-8 -*-
import datetime
import time

from django.db import models
from django.db.models import Q

QUESTIONAIR_PROXY_METHODS = (
    'get_questionair',
)


class QuestionairManager(models.Manager):
    def __getattr__(self, attr, *args, **kwargs):
        #if attr in QUESTIONAIR_PROXY_METHODS:
        #    return getattr(self.get_queryset(), attr, None)
        super(QuestionairManager, self).__getattr__(*args, **kwargs)

    #def get_queryset(self):
    #    return RequestQuerySet(self.model)

    def get_questionair(self, **options):
        qs = self.all().order_by('referer_object','-modified_at').distinct('referer_object')
        return qs