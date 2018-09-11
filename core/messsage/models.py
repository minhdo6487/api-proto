from django.db import models
from django.contrib.auth.models import User


class Message(models.Model):
    date_send = models.DateTimeField()
    date_read = models.DateTimeField()
    date_show = models.DateTimeField()
    from_user = models.ForeignKey(User, related_name='mess_from')
    to_user = models.ForeignKey(User, related_name='mess_to')
    content = models.TextField(max_length=2000)