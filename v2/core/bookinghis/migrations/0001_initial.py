# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0002_auto_20170614_1432'),
        ('booking', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookedGolfcourseEvent_History',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('booked_gcevent', models.IntegerField(default=0, db_index=True)),
                ('discount', models.FloatField(default=0)),
                ('total_cost', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('payment_type', models.CharField(default='N', max_length=1, choices=[('F', 'Full'), ('N', 'NoPay')])),
                ('book_type', models.CharField(default='O', max_length=1, choices=[('O', 'online'), ('P', 'Phone'), ('W', 'Walkin'), ('E', 'Email')])),
                ('payment_status', models.BooleanField(default=False)),
                ('url', models.URLField(blank=True, null=True)),
                ('qr_image', models.ImageField(upload_to='qr_codes/', editable=False, blank=True, null=True)),
                ('qr_base64', models.TextField(editable=False)),
                ('qr_url', models.URLField(blank=True, null=True)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('modified', models.DateTimeField(blank=True, null=True)),
                ('reservation_code', models.TextField(editable=False, unique=True)),
                ('status', models.CharField(default='R', max_length=2, choices=[('I', 'Check In'), ('C', 'Cancel'), ('R', 'Booking Request'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid'), ('PR', 'Booking Process')])),
                ('user_device', models.CharField(default='web', max_length=3, blank=True, null=True)),
                ('cancel_on', models.DateTimeField(editable=False, blank=True, null=True)),
                ('booked_gcevent_id', models.ForeignKey(to='booking.BookedGolfcourseEvent', related_name='booked_gc_event_his', blank=True, null=True)),
                ('member', models.ForeignKey(to='game.EventMember', related_name='booked_gc_event_his', blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
