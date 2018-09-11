# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import core.teetime.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchivedTeetime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('teetime_id', models.PositiveIntegerField()),
                ('time', models.TimeField()),
                ('date', models.DateField()),
                ('description', models.CharField(max_length=100)),
                ('is_block', models.BooleanField(default=False)),
                ('is_hold', models.BooleanField(default=False)),
                ('is_booked', models.BooleanField(default=False)),
                ('is_request', models.BooleanField(default=False)),
                ('min_player', models.PositiveSmallIntegerField()),
                ('available', models.BooleanField(default=False)),
                ('allow_payonline', models.BooleanField(default=False)),
                ('allow_paygc', models.BooleanField(default=False)),
                ('golfcourse_name', models.CharField(max_length=255)),
                ('golfcourse_website', models.CharField(max_length=255)),
                ('golfcourse_contact', models.CharField(max_length=255)),
                ('golfcourse_id', models.PositiveIntegerField()),
                ('golfcourse_short_name', models.CharField(max_length=255)),
                ('golfcourse_country', models.CharField(max_length=255)),
                ('golfcourse_address', models.CharField(max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_9', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_18', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_27', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_36', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('discount', models.FloatField()),
                ('discount_online', models.FloatField()),
                ('gifts', models.CharField(max_length=255)),
                ('food_voucher', models.BooleanField(default=False)),
                ('buggy', models.BooleanField(default=False)),
                ('caddy', models.BooleanField(default=False)),
                ('rank', models.IntegerField()),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookingTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('from_time', models.TimeField()),
                ('to_time', models.TimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CrawlTeeTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, db_index=True, null=True)),
                ('time', models.TimeField(blank=True, db_index=True, null=True)),
                ('price', models.FloatField(default=0)),
                ('higher_price', models.FloatField(default=0)),
                ('is_sent', models.BooleanField(default=False)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='crawl_teetime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Deal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deal_code', models.CharField(max_length=500, db_index=True)),
                ('effective_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('effective_time', models.TimeField(default=datetime.time(0, 0))),
                ('expire_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('expire_time', models.TimeField(default=datetime.time(23, 59, 59, 999999))),
                ('end_date', models.DateField(blank=True, null=True)),
                ('end_time', models.TimeField(blank=True, null=True)),
                ('hole', models.CharField(max_length=20, default='0')),
                ('active', models.BooleanField(default=False)),
                ('is_base', models.BooleanField(default=False)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='deal')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DealEffective_TeeTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timerange', models.PositiveSmallIntegerField(default=0)),
                ('hole', models.CharField(max_length=20, default='0')),
                ('date', models.DateField(blank=True, null=True)),
                ('discount', models.FloatField(default=0)),
                ('modified', models.DateTimeField(blank=True, null=True)),
                ('bookingtime', models.ForeignKey(to='teetime.BookingTime', related_name='bookingtime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DealEffective_TimeRange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, null=True)),
                ('discount', models.FloatField(default=0)),
                ('bookingtime', models.ForeignKey(to='teetime.BookingTime', related_name='timerange')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GC24DiscountOnline',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount', models.FloatField(default=0)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='gc24_discount_online')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GC24PriceByBooking',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('to_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='gc24pricebooking')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GC24PriceByBooking_Detail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.CharField(choices=[('Mon', 'Mon'), ('Tue', 'Tue'), ('Wed', 'Wed'), ('Thu', 'Thu'), ('Fri', 'Fri'), ('Sat', 'Sat'), ('Sun', 'Sun')], max_length=3, default='Mon')),
                ('from_time', models.TimeField(default=datetime.time(0, 0))),
                ('to_time', models.TimeField(default=datetime.time(23, 59, 59, 999999))),
                ('price_9', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_18', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_27', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_36', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('gc24price', models.ForeignKey(to='teetime.GC24PriceByBooking', related_name='gc24pricebooking')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GC24PriceByDeal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.CharField(choices=[('Mon', 'Mon'), ('Tue', 'Tue'), ('Wed', 'Wed'), ('Thu', 'Thu'), ('Fri', 'Fri'), ('Sat', 'Sat'), ('Sun', 'Sun')], max_length=3, default='Mon')),
                ('from_time', models.TimeField(default=datetime.time(0, 0))),
                ('to_time', models.TimeField(default=datetime.time(23, 59, 59, 999999))),
                ('price_9', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_18', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_27', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('price_36', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('deal', models.ForeignKey(to='teetime.Deal', related_name='gc24price')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Gc24TeeTimePrice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, db_index=True, null=True)),
                ('price_9_wd', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_18_wd', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_27_wd', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_36_wd', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_9_wk', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_18_wk', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_27_wk', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_36_wk', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='gc24_teetime_price')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GCKeyPrice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mon_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('tue_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('wed_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('thu_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('fri_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('sat_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('sun_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='gc_key_price')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GCSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_duplicate', models.PositiveSmallIntegerField(default=0)),
                ('golfcourse', models.ForeignKey(unique=True, to='golfcourse.GolfCourse', related_name='gc_setting')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GuestType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.PositiveSmallIntegerField(default=0)),
                ('name', models.CharField(max_length=100, db_index=True)),
                ('description', models.CharField(blank=True, null=True, max_length=1000)),
                ('color', models.CharField(blank=True, null=True, max_length=100)),
                ('status', models.CharField(choices=[('B', 'Block'), ('A', 'Active')], max_length=2, default='A')),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='guest_type')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Holiday',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='JobBookingTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('schedule_task_id', models.CharField(max_length=500)),
                ('schedule_end_task_id', models.CharField(blank=True, null=True, max_length=500)),
                ('bookingtime', models.ForeignKey(to='teetime.BookingTime', related_name='job_bookingtime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PaymentMethodSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.CharField(choices=[('Mon', 'Mon'), ('Tue', 'Tue'), ('Wed', 'Wed'), ('Thu', 'Thu'), ('Fri', 'Fri'), ('Sat', 'Sat'), ('Sun', 'Sun')], max_length=3, default='Mon')),
                ('allow_payonline', models.BooleanField(db_index=True, default=True)),
                ('allow_paygc', models.BooleanField(db_index=True, default=True)),
                ('apply_now', models.BooleanField(db_index=True, default=True)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='payment_method_setting')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PriceMatrix',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.FloatField(default=0)),
                ('date_type', models.CharField(max_length=10, choices=[('weekday', 'Weekend'), ('weekend', 'Weekday'), ('holiday', 'Holiday'), ('A', 'Another')])),
                ('date', models.DateField(blank=True, null=True)),
                ('guest_type', models.ForeignKey(to='teetime.GuestType', related_name='price_matrix')),
            ],
            options={
                'ordering': ('price_type', 'guest_type', 'date_type', 'date'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PriceMatrixLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_date', models.DateField(blank=True, null=True)),
                ('hole', models.PositiveSmallIntegerField(default=9)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('modified', models.DateTimeField(blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='price_matrix_log')),
            ],
            options={
                'ordering': ('-effective_date',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PriceType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_time', models.TimeField()),
                ('to_time', models.TimeField(blank=True, null=True)),
                ('description', models.CharField(max_length=500)),
                ('status', models.CharField(choices=[('B', 'Block'), ('A', 'Active')], max_length=2, default='A')),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='price_type')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RecurringTeetime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recurring_freq', models.PositiveSmallIntegerField(default=0)),
                ('publish_period', models.PositiveSmallIntegerField(default=0)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='recurringteetime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeeTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.TimeField(db_index=True)),
                ('date', models.DateField(db_index=True)),
                ('description', models.CharField(blank=True, max_length=1000)),
                ('is_block', models.BooleanField(db_index=True, default=False)),
                ('is_hold', models.BooleanField(db_index=True, default=False)),
                ('is_booked', models.BooleanField(db_index=True, default=False)),
                ('is_request', models.BooleanField(db_index=True, default=False)),
                ('min_player', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], default=1)),
                ('max_player', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], null=True)),
                ('hold_expire', models.DateTimeField(blank=True, null=True)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('modified', models.DateTimeField(blank=True, null=True)),
                ('available', models.BooleanField(db_index=True, default=True)),
                ('allow_payonline', models.BooleanField(db_index=True, default=True)),
                ('allow_paygc', models.BooleanField(db_index=True, default=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='teetime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeetimeFreeBuggySetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('to_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('from_time', models.TimeField(default=datetime.time(0, 0))),
                ('to_time', models.TimeField(default=datetime.time(23, 59, 59, 999999))),
                ('free', models.BooleanField(default=False)),
                ('golfcourse', models.ForeignKey(help_text='<p>Example: from_date: <strong>2016-09-15</strong>, to_date: <strong>2016-09-23</strong> from_time: <strong>13:00</strong>, to_time: <strong>15:00</strong><br/> 2016-09-20 Long Thanh has teetime from 6:00 to 16:00. Just teetime from 13:00 to 15:00 have <strong>Free/Show</strong> buggy. Remain will be not', to='golfcourse.GolfCourse', related_name='teetime_free_buggy_setting', default=core.teetime.models.get_LongThanh_golfcourse)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeeTimePrice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hole', models.PositiveSmallIntegerField(default=9)),
                ('price', models.FloatField(default=0)),
                ('price_standard', models.FloatField(default=0)),
                ('cash_discount', models.FloatField(default=0)),
                ('online_discount', models.FloatField(default=0)),
                ('is_publish', models.BooleanField(db_index=True, default=False)),
                ('gifts', models.CharField(blank=True, null=True, max_length=500)),
                ('food_voucher', models.BooleanField(default=False)),
                ('buggy', models.BooleanField(default=False)),
                ('caddy', models.BooleanField(default=False)),
                ('guest_type', models.ForeignKey(to='teetime.GuestType', related_name='teetime_price')),
                ('teetime', models.ForeignKey(to='teetime.TeeTime', related_name='teetime_price')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeetimeShowBuggySetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('to_date', models.DateField(default=datetime.date(2017, 6, 14))),
                ('from_time', models.TimeField(default=datetime.time(0, 0))),
                ('to_time', models.TimeField(default=datetime.time(23, 59, 59, 999999))),
                ('show', models.BooleanField(default=False)),
                ('golfcourse', models.ForeignKey(help_text='<p>Example: from_date: <strong>2016-09-15</strong>, to_date: <strong>2016-09-23</strong> from_time: <strong>13:00</strong>, to_time: <strong>15:00</strong><br/> 2016-09-20 Long Thanh has teetime from 6:00 to 16:00. Just teetime from 13:00 to 15:00 have <strong>Free/Show</strong> buggy. Remain will be not', to='golfcourse.GolfCourse', related_name='teetime_show_buggy_setting', default=core.teetime.models.get_LongThanh_golfcourse)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TimeRangeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_name', models.CharField(max_length=500)),
                ('from_time', models.TimeField(db_index=True, default=datetime.time(0, 0))),
                ('to_time', models.TimeField(db_index=True, default=datetime.time(23, 59, 59, 999999))),
                ('deal', models.ForeignKey(null=True, to='teetime.Deal', related_name='deal')),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='timerange')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='teetimeprice',
            unique_together=set([('teetime', 'guest_type', 'hole')]),
        ),
        migrations.AlterUniqueTogether(
            name='pricematrixlog',
            unique_together=set([('effective_date', 'golfcourse', 'hole')]),
        ),
        migrations.AddField(
            model_name='pricematrix',
            name='matrix_log',
            field=models.ForeignKey(to='teetime.PriceMatrixLog', related_name='price_matrix'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='pricematrix',
            name='price_type',
            field=models.ForeignKey(to='teetime.PriceType', related_name='price_matrix'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='dealeffective_timerange',
            name='timerange',
            field=models.ForeignKey(to='teetime.TimeRangeType', related_name='timerange'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='dealeffective_teetime',
            name='teetime',
            field=models.ForeignKey(to='teetime.TeeTime', related_name='teetime_deal'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookingtime',
            name='deal',
            field=models.ForeignKey(to='teetime.Deal', related_name='bookingtime'),
            preserve_default=True,
        ),
    ]
