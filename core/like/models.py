from datetime import date

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


class Like(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    date = models.DateField(editable=False)
    count = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    like = generic.GenericForeignKey('content_type', 'object_id')

    def save(self, *args, **kwargs):
        if not self.id:
            self.date = date.today()
        return super(Like, self).save(*args, **kwargs)


class View(models.Model):
    count = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    related_object = generic.GenericForeignKey('content_type', 'object_id')