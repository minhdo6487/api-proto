# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookinghis', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bookedgolfcourseevent_history',
            name='booked_gcevent_id',
        ),
    ]
