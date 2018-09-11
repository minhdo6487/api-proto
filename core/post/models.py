from datetime import date

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


class Post(models.Model):
    user = models.ForeignKey(User, blank=False, null=False)
    title = models.TextField()
    content = models.TextField()
    link = models.TextField(blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0, blank=True, null=True)
    date_creation = models.DateTimeField(editable=False)
    date_modified = models.DateTimeField(editable=False, blank=True, null=True)

    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    category = generic.GenericForeignKey('content_type', 'object_id')

    def save(self, *args, **kwargs):
        # true if this is a new object (first save)
        is_new = self.pk is None
        if is_new:
            self.date_creation = date.today()
        else:
            self.date_modified = date.today()
        super(Post, self).save(*args, **kwargs)

    def __str__(self):
        return self.title