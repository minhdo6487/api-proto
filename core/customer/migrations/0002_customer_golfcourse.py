# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0001_initial'),
        ('golfcourse', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='golfcourse',
            field=models.ForeignKey(null=True, to='golfcourse.GolfCourse', blank=True),
            preserve_default=True,
        ),
    ]
