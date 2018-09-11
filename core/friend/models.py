from datetime import date, datetime

from django.db import models
from django.contrib.auth.models import User


class Friend(models.Model):
    from_user = models.ForeignKey(User, related_name='friend_fromusers')
    to_user = models.ForeignKey(User, related_name='friend_tousers')
    date_created = models.DateField(editable=False, null=True)


    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ('-date_created', '-id')

    def save(self, *args, **kwargs):
        self.date_created = date.today()
        super(Friend, self).save(*args, **kwargs)

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='fr_fromusers')
    to_user = models.ForeignKey(User, related_name='fr_tousers')
    date_request = models.DateField(editable=False)

    def save(self, *args, **kwargs):
        self.date_request = date.today()
        super(FriendRequest, self).save(*args, **kwargs)


class FriendConnect(models.Model):
    user = models.ForeignKey(User, related_name='fc_users')
    friend = models.ForeignKey(User, related_name='fc_friends')
    date_accepted = models.DateField(editable=False)

    def save(self, *args, **kwargs):
        self.date_accepted = date.today()
        super(FriendConnect, self).save(*args, **kwargs)


class FriendPostTrack(models.Model):
    user = models.ForeignKey(User, related_name='post_track_user')
    to_user = models.ForeignKey(User, related_name='post_track_friend')
    timestamp = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.timestamp = datetime.now()
        super(FriendPostTrack, self).save(*args, **kwargs)

