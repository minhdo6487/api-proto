# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0003_auto_20171031_2050'),
    ]

    operations = [
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='from_date',
            field=models.DateField(blank=True, default=datetime.date(2017, 11, 1), db_index=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='to_date',
            field=models.DateField(blank=True, default=datetime.date(2017, 11, 1), null=True),
            preserve_default=True,
        ),
    ]
