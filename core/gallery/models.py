from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType


class Gallery(models.Model):
    picture = models.TextField(max_length=1000, blank=True)
    description = models.TextField(max_length=1000, blank=True, null=True)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    related_object = generic.GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return str(self.picture)
