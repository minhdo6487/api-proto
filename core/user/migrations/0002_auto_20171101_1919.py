# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='first_name',
            field=models.TextField(blank=True, null=True, max_length=50),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='last_name',
            field=models.TextField(blank=True, null=True, max_length=50),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='avg_score',
            field=models.FloatField(blank=True, default=0, null=True),
            preserve_default=True,
        ),
    ]
