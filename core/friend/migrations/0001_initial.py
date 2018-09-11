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
            name='Friend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateField(editable=False, null=True)),
                ('from_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='friend_fromusers')),
                ('to_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='friend_tousers')),
            ],
            options={
                'ordering': ('-date_created', '-id'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FriendConnect',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_accepted', models.DateField(editable=False)),
                ('friend', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='fc_friends')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='fc_users')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FriendPostTrack',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
                ('to_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='post_track_friend')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='post_track_user')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FriendRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_request', models.DateField(editable=False)),
                ('from_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='fr_fromusers')),
                ('to_user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='fr_tousers')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='friend',
            unique_together=set([('from_user', 'to_user')]),
        ),
    ]
