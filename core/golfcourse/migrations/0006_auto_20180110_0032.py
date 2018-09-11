# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0005_auto_20171128_1515'),
    ]

    operations = [
        migrations.AddField(
            model_name='golfcourseevent',
            name='payment_discount',
            field=models.CharField(choices=[(10, 'pay now'), (5, 'pay later')], max_length=20, default=5),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='from_date',
            field=models.DateField(db_index=True, blank=True, null=True, default=datetime.date(2018, 1, 10)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='golfcoursebuggy',
            name='to_date',
            field=models.DateField(null=True, blank=True, default=datetime.date(2018, 1, 10)),
            preserve_default=True,
        ),
    ]
