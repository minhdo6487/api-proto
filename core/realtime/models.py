import datetime
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

__author__ = 'toantran'
from django.db import models



class TimeStamp(models.Model):
    channel = models.TextField()
    time = models.DateTimeField()

    def save(self, *args, **kwargs):
        """
        custom save method to send email and push notification
        """
        self.time = datetime.datetime.now()
        return super(TimeStamp, self).save(*args, **kwargs)

class UserSubcribe(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    user = models.CommaSeparatedIntegerField(max_length=255)