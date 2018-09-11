from django.db import models


class Category(models.Model):
    name = models.TextField()
    name_vi = models.TextField()
    is_forum = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)