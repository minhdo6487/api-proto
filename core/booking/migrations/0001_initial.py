# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('teetime', '0003_auto_20171101_0004'),
        ('golfcourse', '0004_auto_20171101_0004'),
        ('game', '0002_auto_20170614_1432'),
        ('customer', '0002_customer_golfcourse'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BookedBuggy',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('quantity', models.PositiveIntegerField()),
                ('amount', models.DecimalField(default=0.0, decimal_places=2, max_digits=9)),
                ('buggy', models.ForeignKey(related_name='booked_buggy', to='golfcourse.GolfCourseBuggy')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedCaddy',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('amount', models.DecimalField(default=0.0, decimal_places=2, max_digits=9)),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('caddy', models.ForeignKey(related_name='booked_caddy', to='golfcourse.GolfCourseCaddy')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedClubset',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('quantity', models.PositiveIntegerField()),
                ('amount', models.DecimalField(default=0.0, decimal_places=2, max_digits=9)),
                ('clubset', models.ForeignKey(related_name='booked_clubset', to='golfcourse.GolfCourseClubSets')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedGolfcourseEvent',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('discount', models.FloatField(default=0)),
                ('total_cost', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('payment_type', models.CharField(max_length=1, default='N', choices=[('F', 'Full'), ('N', 'NoPay')])),
                ('book_type', models.CharField(max_length=1, default='O', choices=[('O', 'online'), ('P', 'Phone'), ('W', 'Walkin'), ('E', 'Email')])),
                ('payment_status', models.BooleanField(default=False)),
                ('url', models.URLField(null=True, blank=True)),
                ('qr_image', models.ImageField(null=True, upload_to='qr_codes/', blank=True, editable=False)),
                ('qr_base64', models.TextField(editable=False)),
                ('qr_url', models.URLField(null=True, blank=True)),
                ('created', models.DateTimeField(null=True, blank=True, editable=False)),
                ('modified', models.DateTimeField(null=True, blank=True)),
                ('reservation_code', models.TextField(unique=True, editable=False)),
                ('status', models.CharField(max_length=2, default='R', choices=[('I', 'Check In'), ('C', 'Cancel'), ('R', 'Booking Request'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid'), ('PR', 'Booking Process')])),
                ('user_device', models.CharField(max_length=3, null=True, default='web', blank=True)),
                ('member', models.ForeignKey(related_name='booked_gc_event', to='game.EventMember')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedGolfcourseEventDetail',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('price', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('booked_event', models.ForeignKey(related_name='booked_gc_event_detail', to='booking.BookedGolfcourseEvent')),
                ('price_info', models.ForeignKey(related_name='booked_gc_event_detail', to='golfcourse.GolfCourseEventPriceInfo')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPartner',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('status', models.CharField(max_length=2, default='PU', choices=[('S', 'ShowUp'), ('C', 'Cancel'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPartner_History',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('status', models.CharField(max_length=2, default='PU', choices=[('S', 'ShowUp'), ('C', 'Cancel'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPartnerThankyou',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('email', models.CharField(max_length=888)),
                ('modified_date', models.DateField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPayonlineLink',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('custName', models.CharField(max_length=255)),
                ('custAddress', models.CharField(max_length=255)),
                ('custMail', models.CharField(max_length=255)),
                ('custPhone', models.CharField(max_length=255)),
                ('totalAmount', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255, default='Please select your preferred card to pay')),
                ('receiveEmail', models.CharField(max_length=255, default='thao.vuong@ludiino.com')),
                ('paymentStatus', models.BooleanField(default=False, editable=False)),
                ('paymentLink', models.CharField(max_length=255, null=True, blank=True, editable=False)),
            ],
            options={
                'ordering': ['-id'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedTeeTime',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('reservation_code', models.TextField(unique=True, editable=False)),
                ('created', models.DateTimeField(null=True, blank=True, editable=False)),
                ('modified', models.DateTimeField(null=True, blank=True)),
                ('player_count', models.PositiveIntegerField(default=1)),
                ('player_checkin_count', models.PositiveIntegerField(default=0)),
                ('payment_type', models.CharField(max_length=1, default='N', choices=[('F', 'Full'), ('N', 'NoPay')])),
                ('status', models.CharField(max_length=2, default='R', choices=[('I', 'Check In'), ('C', 'Cancel'), ('R', 'Booking Request'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid'), ('PR', 'Booking Process')])),
                ('book_type', models.CharField(max_length=1, default='O', choices=[('O', 'online'), ('P', 'Phone'), ('W', 'Walkin'), ('E', 'Email')])),
                ('hole', models.PositiveSmallIntegerField(default=18)),
                ('total_cost', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('paid_amount', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('url', models.URLField(null=True, blank=True)),
                ('qr_image', models.ImageField(null=True, upload_to='qr_codes/', blank=True, editable=False)),
                ('qr_base64', models.TextField(editable=False)),
                ('qr_url', models.URLField(null=True, blank=True)),
                ('voucher_code', models.CharField(max_length=20, null=True, blank=True)),
                ('discount', models.FloatField(default=0)),
                ('payment_status', models.BooleanField(default=False)),
                ('company_address', models.CharField(max_length=100, null=True, blank=True)),
                ('invoice_address', models.CharField(max_length=100, null=True, blank=True)),
                ('invoice_name', models.CharField(max_length=100, null=True, blank=True)),
                ('tax_code', models.CharField(max_length=100, null=True, blank=True)),
                ('voucher_discount_amount', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('user_device', models.CharField(max_length=3, null=True, default='web', blank=True)),
                ('currencyCode', models.CharField(max_length=20, null=True, default='VND', blank=True)),
                ('currencyValue', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('back_link', models.CharField(max_length=255, null=True, blank=True)),
                ('note', models.TextField(null=True, blank=True)),
                ('golfcourse', models.ForeignKey(related_name='booked_teetime', to='golfcourse.GolfCourse')),
                ('teetime', models.ForeignKey(unique=True, related_name='booked_teetime', to='teetime.TeeTime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedTeeTime_History',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('booked_teetime', models.IntegerField(default=0, db_index=True)),
                ('reservation_code', models.TextField(editable=False)),
                ('created', models.DateTimeField(null=True, blank=True, editable=False)),
                ('modified', models.DateTimeField(null=True, blank=True)),
                ('player_count', models.PositiveIntegerField(default=1)),
                ('player_checkin_count', models.PositiveIntegerField(default=0)),
                ('payment_type', models.CharField(max_length=1, default='N', choices=[('F', 'Full'), ('N', 'NoPay')])),
                ('payment_status', models.BooleanField(default=False)),
                ('status', models.CharField(max_length=2, default='PU', choices=[('I', 'Check In'), ('C', 'Cancel'), ('R', 'Booking Request'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid'), ('PR', 'Booking Process')])),
                ('book_type', models.CharField(max_length=1, default='O', choices=[('O', 'online'), ('P', 'Phone'), ('W', 'Walkin'), ('E', 'Email')])),
                ('total_cost', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('paid_amount', models.DecimalField(default=0.0, decimal_places=2, max_digits=20)),
                ('url', models.URLField(null=True, blank=True)),
                ('qr_image', models.ImageField(null=True, upload_to='qr_codes/', blank=True, editable=False)),
                ('qr_base64', models.TextField(editable=False)),
                ('qr_url', models.URLField(null=True, blank=True)),
                ('cancel_on', models.DateTimeField(null=True, blank=True, editable=False)),
                ('golfcourse', models.ForeignKey(related_name='booked_teetime_his', to='golfcourse.GolfCourse')),
                ('teetime', models.ForeignKey(related_name='booked_teetime_his', to='teetime.TeeTime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookingSetting',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('code', models.CharField(max_length=100, unique=True, db_index=True)),
                ('value', models.CharField(max_length=1000)),
                ('created', models.DateTimeField(null=True, blank=True, editable=False)),
                ('modified', models.DateTimeField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GC24BookingVendor',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('booking_vendor', models.CharField(max_length=7, default='VTCPay', choices=[('123Pay', '123Pay'), ('VTCPay', 'VTCPay')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PayTransactionStore',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('payTransactionid', models.TextField(unique=True, null=True)),
                ('transactionId', models.TextField(unique=True, null=True)),
                ('transactionStatus', models.TextField(null=True, default='0')),
                ('totalAmount', models.TextField(null=True)),
                ('opAmount', models.TextField(null=True)),
                ('bankCode', models.TextField(null=True)),
                ('description', models.TextField(null=True)),
                ('clientIP', models.TextField(null=True, default='127.0.0.1')),
                ('vendor', models.TextField(null=True)),
                ('created', models.DateTimeField(null=True, blank=True, editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Voucher',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('is_used', models.BooleanField(db_index=True, default=False)),
                ('date_created', models.DateTimeField(null=True, blank=True, editable=False)),
                ('discount_amount', models.FloatField(default=0)),
                ('from_date', models.DateTimeField(null=True, db_index=True, blank=True)),
                ('to_date', models.DateTimeField(null=True, db_index=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='bookedpartner_history',
            name='bookedteetime',
            field=models.ForeignKey(related_name='book_partner_his', to='booking.BookedTeeTime_History'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpartner_history',
            name='customer',
            field=models.ForeignKey(null=True, blank=True, related_name='book_partner_his', to='customer.Customer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpartner_history',
            name='user',
            field=models.ForeignKey(null=True, blank=True, related_name='book_partner_his', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpartner',
            name='bookedteetime',
            field=models.ForeignKey(related_name='book_partner', to='booking.BookedTeeTime'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpartner',
            name='customer',
            field=models.ForeignKey(null=True, blank=True, related_name='book_partner', to='customer.Customer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpartner',
            name='user',
            field=models.ForeignKey(null=True, blank=True, related_name='book_partner', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedclubset',
            name='teetime',
            field=models.ForeignKey(related_name='booked_clubset', to='booking.BookedTeeTime'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedcaddy',
            name='teetime',
            field=models.ForeignKey(null=True, related_name='teetime_caddy', to='booking.BookedTeeTime'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedbuggy',
            name='teetime',
            field=models.ForeignKey(null=True, related_name='teetime_buggy', to='booking.BookedTeeTime'),
            preserve_default=True,
        ),
    ]
