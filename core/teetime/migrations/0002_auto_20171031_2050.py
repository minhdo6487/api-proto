# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('teetime', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingtime',
            name='date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='deal',
            name='effective_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='deal',
            name='expire_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='gc24pricebybooking',
            name='from_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='gc24pricebybooking',
            name='to_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teetimefreebuggysetting',
            name='from_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teetimefreebuggysetting',
            name='to_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teetimeshowbuggysetting',
            name='from_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teetimeshowbuggysetting',
            name='to_date',
            field=models.DateField(default=datetime.date(2017, 10, 31)),
            preserve_default=True,
        ),
    ]
