# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone
import v2.core.geohash.fields


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LocalIndex',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('geoname', models.CharField(max_length=500, blank=True, db_index=True, null=True)),
                ('modified_at', models.DateTimeField(editable=False, blank=True, null=True, default=django.utils.timezone.now)),
                ('golfcourse', models.ForeignKey(null=True, to='golfcourse.GolfCourse', related_name='geoname_golfcourse', blank=True)),
                ('user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='geoname_user', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LocalName',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('place', models.CharField(blank=True, null=True, max_length=100)),
                ('location_x', models.FloatField()),
                ('location_y', models.FloatField()),
                ('name', models.CharField(blank=True, null=True, max_length=150)),
                ('admin_code', models.CharField(blank=True, null=True, max_length=20)),
                ('location', v2.core.geohash.fields.GeohashField(max_length=12, blank=True, db_index=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
