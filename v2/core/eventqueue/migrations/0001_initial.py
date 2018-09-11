# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventQueue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_email', models.EmailField(blank=True, null=True, max_length=255)),
                ('is_created', models.BooleanField(default=False)),
                ('is_pushnotify', models.BooleanField(default=False)),
                ('booking', models.ForeignKey(null=True, to='booking.BookedTeeTime', related_name='event_booking', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
