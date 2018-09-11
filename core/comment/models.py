

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db.models.signals import post_save
from core.realtime.models import UserSubcribe

import datetime

class Comment(models.Model):
    user = models.ForeignKey(User, blank=False, null=False)
    content = models.TextField()

    date_creation = models.DateTimeField(editable=False)
    date_modified = models.DateField(editable=False, blank=True, null=True)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ('-id',)

    def __str__(self):
        return self.content

    def save(self, *args, **kwargs):
        # true if this is a new object (first save)
        is_new = self.pk is None
        if is_new:
            self.date_creation = datetime.datetime.now()
        else:
            self.date_modified = datetime.date.today()
        # self.date_creation = datetime.date.today()
        super(Comment, self).save(*args, **kwargs)

def push_user_to_subcribe(sender, instance, created, **kwargs):
    if created:
        try:
            user_subcribe = UserSubcribe.objects.get(content_type=instance.content_type,
                                                                    object_id=instance.object_id)
            subcribe_list = eval(user_subcribe.user)
            if instance.user_id not in subcribe_list:
                subcribe_list.append(instance.user_id)
                user_subcribe.user = subcribe_list
                user_subcribe.save(update_fields=['user'])
        except Exception:
            UserSubcribe.objects.create(content_type=instance.content_type,
                                        object_id=instance.object_id,
                                        user=[instance.user_id])

post_save.connect(push_user_to_subcribe, sender=Comment)