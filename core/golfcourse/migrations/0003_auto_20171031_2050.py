# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0002_auto_20170614_1432'),
    ]

    operations = [
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='from_date',
            field=models.DateField(db_index=True, blank=True, default=datetime.date(2017, 10, 31), null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='to_date',
            field=models.DateField(blank=True, default=datetime.date(2017, 10, 31), null=True),
            preserve_default=True,
        ),
    ]
