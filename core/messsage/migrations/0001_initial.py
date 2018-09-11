# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_send', models.DateTimeField()),
                ('date_read', models.DateTimeField()),
                ('date_show', models.DateTimeField()),
                ('content', models.TextField(max_length=2000)),
                ('from_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='mess_from')),
                ('to_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='mess_to')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
