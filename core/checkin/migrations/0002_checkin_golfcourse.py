# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checkin', '0001_initial'),
        ('golfcourse', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='checkin',
            name='golfcourse',
            field=models.ForeignKey(to='golfcourse.GolfCourse', related_name='checkin'),
            preserve_default=True,
        ),
    ]
