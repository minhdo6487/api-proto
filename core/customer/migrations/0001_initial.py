# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, db_index=True)),
                ('email', models.CharField(max_length=100)),
                ('phone_number', models.CharField(blank=True, null=True, max_length=20)),
                ('avatar', models.CharField(blank=True, null=True, max_length=200)),
                ('handicap', models.FloatField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
