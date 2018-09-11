# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0002_auto_20170614_1432'),
        ('contenttypes', '0001_initial'),
        ('customer', '0002_customer_golfcourse'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EventMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('memberID', models.CharField(max_length=100, blank=True, db_index=True, null=True)),
                ('clubID', models.CharField(max_length=100, blank=True, db_index=True, null=True)),
                ('handicap', models.FloatField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=False)),
                ('is_join', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('A', 'Accept'), ('C', 'Cancel'), ('P', 'Pending'), ('H', 'Host')], max_length=2, default='P')),
                ('rank', models.IntegerField(blank=True, null=True)),
                ('gender', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('-id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_create', models.DateTimeField(blank=True, null=True)),
                ('date_play', models.DateField(db_index=True)),
                ('time_play', models.TimeField(blank=True, null=True)),
                ('bag_number', models.IntegerField(blank=True, null=True)),
                ('active', models.BooleanField(default=False)),
                ('score_card', models.TextField(blank=True, null=True, max_length=300)),
                ('is_finish', models.BooleanField(default=False)),
                ('is_quit', models.BooleanField(default=False)),
                ('handicap', models.FloatField(blank=True, null=True, default=0)),
                ('handicap_36', models.FloatField(blank=True, null=True, default=0)),
                ('hdc_36', models.FloatField(blank=True, null=True)),
                ('hdc_us', models.FloatField(blank=True, null=True)),
                ('hdcp', models.FloatField(blank=True, null=True)),
                ('hdc_callaway', models.FloatField(blank=True, null=True)),
                ('hdc_stable_ford', models.FloatField(blank=True, null=True)),
                ('hdc_peoria', models.FloatField(blank=True, null=True)),
                ('hdc_net', models.FloatField(blank=True, null=True)),
                ('gross_score', models.PositiveIntegerField(default=0)),
                ('adj', models.PositiveIntegerField(blank=True, null=True)),
                ('group_link', models.CharField(blank=True, null=True, max_length=40)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('reservation_code', models.CharField(blank=True, null=True, max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GameFlight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Score',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stroke', models.IntegerField()),
                ('ob', models.PositiveIntegerField(blank=True, null=True)),
                ('putt', models.PositiveIntegerField(blank=True, null=True, default=0)),
                ('chip', models.PositiveIntegerField(blank=True, null=True)),
                ('bunker', models.PositiveIntegerField(blank=True, null=True)),
                ('water', models.PositiveIntegerField(blank=True, null=True)),
                ('fairway', models.BooleanField(default=False)),
                ('on_green', models.BooleanField(default=False)),
                ('game', models.ForeignKey(null=True, to='game.Game', related_name='score', blank=True)),
            ],
            options={
                'ordering': ('hole__holeNumber',),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='score',
            name='hole',
            field=models.ForeignKey(to='golfcourse.Hole', related_name='score'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='score',
            name='tee_type',
            field=models.ForeignKey(to='golfcourse.TeeType'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='score',
            unique_together=set([('game', 'hole', 'tee_type')]),
        ),
        migrations.AddField(
            model_name='gameflight',
            name='flight',
            field=models.ForeignKey(to='golfcourse.Flight', related_name='game_flight'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gameflight',
            name='game',
            field=models.OneToOneField(to='game.Game', related_name='game_flight'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gameflight',
            name='member',
            field=models.ForeignKey(to='game.EventMember', related_name='game_flight'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='game',
            name='content_type',
            field=models.ForeignKey(null=True, to='contenttypes.ContentType', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='game',
            name='event_member',
            field=models.ForeignKey(null=True, to='game.EventMember', related_name='game', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='game',
            name='golfcourse',
            field=models.ForeignKey(to='golfcourse.GolfCourse', related_name='game'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='game',
            name='recorder',
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='game_recorder', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventmember',
            name='customer',
            field=models.ForeignKey(null=True, to='customer.Customer', related_name='event_member', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventmember',
            name='event',
            field=models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='event_member', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventmember',
            name='group',
            field=models.ForeignKey(null=True, to='golfcourse.GroupOfEvent', related_name='event_member', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventmember',
            name='user',
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='event_member', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='eventmember',
            unique_together=set([('event', 'memberID', 'clubID', 'user', 'customer')]),
        ),
    ]
