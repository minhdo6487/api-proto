# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Checkin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reservation_code', models.CharField(blank=True, null=True, max_length=100)),
                ('total_amount', models.PositiveIntegerField()),
                ('play_number', models.CharField(blank=True, null=True, max_length=100)),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('content_type', models.ForeignKey(null=True, to='contenttypes.ContentType', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
