# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserChatPresence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_id', models.CharField(max_length=100, blank=True, db_index=True, null=True)),
                ('status', models.CharField(blank=True, null=True, max_length=20)),
                ('modified_at', models.DateTimeField(blank=True, null=True, default=django.utils.timezone.now)),
                ('user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='userchat_presence', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
