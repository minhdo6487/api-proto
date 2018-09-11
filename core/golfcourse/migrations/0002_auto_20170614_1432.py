# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0001_initial'),
        ('playstay', '0001_initial'),
    ]

    operations = [
    	migrations.AddField(
            model_name='golfcourseeventhotel',
            name='hotel',
            field=models.ForeignKey(to='playstay.Hotel', related_name='event_hotel_info'),
            preserve_default=True,
        ),
    ]
