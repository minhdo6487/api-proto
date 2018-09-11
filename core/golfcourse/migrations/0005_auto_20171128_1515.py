# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0004_auto_20171101_0004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='from_date',
            field=models.DateField(null=True, db_index=True, default=datetime.date(2017, 11, 28), blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='to_date',
            field=models.DateField(null=True, default=datetime.date(2017, 11, 28), blank=True),
            preserve_default=True,
        ),
    ]
