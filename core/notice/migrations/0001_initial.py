# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notice_type', models.CharField(max_length=10, db_index=True, choices=[('I', 'Invitation'), ('B', 'Booking'), ('IA', 'Invite Accept'), ('IC', 'Invite Cancel'), ('IN', 'Inform')])),
                ('date_create', models.DateTimeField()),
                ('date_modify', models.DateTimeField()),
                ('date_read', models.DateTimeField(blank=True, null=True)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('is_show', models.BooleanField(db_index=True, default=False)),
                ('detail', models.CharField(blank=True, max_length=1000)),
                ('detail_en', models.CharField(blank=True, null=True, max_length=1000)),
                ('send_email', models.BooleanField(default=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('content_type', models.ForeignKey(null=True, to='contenttypes.ContentType', blank=True)),
                ('from_user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='notifications_sent', blank=True)),
                ('to_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='notifications_received')),
            ],
            options={
                'ordering': ('-id',),
            },
            bases=(models.Model,),
        ),
    ]
