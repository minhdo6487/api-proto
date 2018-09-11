# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Camp',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('title', models.CharField(max_length=150)),
                ('body', models.CharField(max_length=320)),
                ('gender', models.CharField(default='-', max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('A', 'Another'), ('-', 'ALL')])),
                ('age_min', models.IntegerField(default=18)),
                ('age_max', models.IntegerField(default=70)),
                ('city_ids', models.CharField(default='', max_length=320)),
                ('sent_at', models.DateTimeField(default=None, null=True, blank=True)),
                ('user_id', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CampLog',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('schedule_id', models.PositiveIntegerField()),
                ('user_id', models.PositiveIntegerField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(max_length=150)),
                ('body', models.CharField(default='', max_length=320)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('timed_at', models.DateTimeField()),
                ('sent_at', models.DateTimeField(default=None, null=True, blank=True)),
                ('camp', models.ForeignKey(to='notify.Camp', related_name='camp_time')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
