# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('golfcourse', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookedPackageAdditional',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, null=True, max_length=50)),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('quantity', models.PositiveIntegerField(default=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPackageGolfcourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, null=True, max_length=50)),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('no_round', models.PositiveIntegerField(default=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPackageHotel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, null=True, max_length=50)),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('quantity', models.PositiveIntegerField(default=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookedPackageTour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(max_length=100)),
                ('customer_phone', models.CharField(max_length=20)),
                ('customer_email', models.CharField(max_length=100)),
                ('total_cost', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('discount', models.FloatField(default=0)),
                ('paid_amount', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('payment_type', models.CharField(choices=[('F', 'Full'), ('N', 'NoPay')], max_length=1, default='N')),
                ('payment_status', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('I', 'Check In'), ('C', 'Cancel'), ('R', 'Booking Request'), ('PP', 'Pending paid'), ('PU', 'Pending unpaid')], max_length=2, default='R')),
                ('voucher', models.CharField(blank=True, null=True, max_length=50)),
                ('checkin_date', models.DateField()),
                ('checkout_date', models.DateField()),
                ('note', models.TextField(blank=True, null=True)),
                ('qr_code', models.CharField(blank=True, null=True, max_length=32)),
                ('qr_url', models.TextField(blank=True, null=True, max_length=100)),
                ('reservation_code', models.TextField(editable=False, unique=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('currencyCode', models.CharField(max_length=20, blank=True, null=True, default='VND')),
                ('currencyValue', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('date_created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('date_modified', models.DateTimeField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Hotel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('description_en', models.TextField(blank=True, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('website', models.CharField(blank=True, null=True, max_length=100)),
                ('phone_number', models.CharField(blank=True, null=True, max_length=50)),
                ('star', models.IntegerField(default=3)),
                ('golfcourse_distance', models.IntegerField(default=0)),
                ('downtown_distance', models.IntegerField(default=0)),
                ('airport_distance', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HotelGolfcourseDistance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_name', models.TextField(blank=True, null=True)),
                ('distance', models.IntegerField(default=0)),
                ('golfcourse', models.ForeignKey(null=True, to='golfcourse.GolfCourse', related_name='distance_golfcourse', blank=True)),
                ('hotel', models.ForeignKey(null=True, to='playstay.Hotel', related_name='distance_hotel', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HotelImages',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.TextField()),
                ('hotel', models.ForeignKey(null=True, to='playstay.Hotel', related_name='hotel_images', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HotelRoom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_person', models.IntegerField(default=2)),
                ('name', models.CharField(max_length=100)),
                ('hotel', models.ForeignKey(null=True, to='playstay.Hotel', related_name='hotel_room', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageAdditionalFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('gc_price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageGolfCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('round', models.IntegerField(default=1)),
                ('hole', models.IntegerField(default=18)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='package_golfcourse')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageGolfcourseFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('gc_price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('package_golfcourse', models.ForeignKey(null=True, to='playstay.PackageGolfCourse', related_name='package_golfcourse', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageHotelRoomFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('gc_price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('hotel_room', models.ForeignKey(to='playstay.HotelRoom', related_name='package_hotel')),
            ],
            options={
                'ordering': ('price',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageTour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('day', models.PositiveSmallIntegerField(default=1)),
                ('no_round', models.PositiveSmallIntegerField(default=1)),
                ('hole', models.PositiveIntegerField(default=18)),
                ('is_destination', models.BooleanField(default=False)),
                ('register_count', models.PositiveIntegerField(default=0)),
                ('discount', models.FloatField(default=0)),
                ('date_created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('date_modified', models.DateTimeField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageTourDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('html_homepage', models.TextField(blank=True, null=True)),
                ('package_tour', models.ForeignKey(to='playstay.PackageTour', related_name='package_detail')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageTourFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('display_price', models.DecimalField(decimal_places=2, max_digits=20, default=0.0)),
                ('package_tour', models.ForeignKey(null=True, to='playstay.PackageTour', related_name='fees', blank=True)),
            ],
            options={
                'ordering': ('display_price',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageTourReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, null=True, max_length=100)),
                ('rating', models.FloatField(default=5)),
                ('comment', models.TextField(blank=True, null=True)),
                ('title', models.CharField(max_length=100)),
                ('date_created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('date_modified', models.DateTimeField(blank=True, null=True)),
                ('package_tour', models.ForeignKey(to='playstay.PackageTour', related_name='package_review')),
                ('user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='package_review', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageTourServices',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_free', models.BooleanField(default=False)),
                ('package_tour', models.ForeignKey(null=True, to='playstay.PackageTour', related_name='services', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PackageTourSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(blank=True, null=True)),
                ('max_register', models.PositiveIntegerField(default=0)),
                ('package_tour', models.ForeignKey(to='playstay.PackageTour', related_name='package_setting')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ParentPackageTour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('rating', models.FloatField(default=0)),
                ('is_destination', models.BooleanField(default=False)),
                ('register_count', models.PositiveIntegerField(default=0)),
                ('thumbnail', models.TextField(blank=True, null=True)),
                ('from_date', models.DateField(blank=True, null=True)),
                ('to_date', models.DateField(blank=True, null=True)),
                ('slug', models.CharField(blank=True, null=True, max_length=100)),
                ('term_condition', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('display_price', models.DecimalField(decimal_places=0, max_digits=20, default=0)),
                ('discount', models.FloatField(default=0)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('is_publish', models.BooleanField(default=True)),
                ('date_created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('date_modified', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ('display_price',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Services',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('small_icon', models.TextField(blank=True, null=True)),
                ('large_icon', models.TextField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='packagetourservices',
            name='service',
            field=models.ForeignKey(null=True, to='playstay.Services', related_name='package_services', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='packagetourservices',
            unique_together=set([('service', 'package_tour')]),
        ),
        migrations.AddField(
            model_name='packagetour',
            name='parent',
            field=models.ForeignKey(null=True, to='playstay.ParentPackageTour', related_name='package_tour', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='packagehotelroomfee',
            name='package_service',
            field=models.ForeignKey(null=True, to='playstay.PackageTourFee', related_name='package_hotel', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='packagehotelroomfee',
            unique_together=set([('hotel_room', 'package_service')]),
        ),
        migrations.AddField(
            model_name='packagegolfcoursefee',
            name='package_service',
            field=models.ForeignKey(null=True, to='playstay.PackageTourFee', related_name='package_golfcourse', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='packagegolfcoursefee',
            unique_together=set([('package_golfcourse', 'package_service')]),
        ),
        migrations.AddField(
            model_name='packageadditionalfee',
            name='package_service',
            field=models.ForeignKey(null=True, to='playstay.PackageTourFee', related_name='package_additional', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='packageadditionalfee',
            name='service',
            field=models.ForeignKey(null=True, to='playstay.Services', related_name='package_additional', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='packageadditionalfee',
            unique_together=set([('service', 'package_service')]),
        ),
        migrations.AddField(
            model_name='bookedpackagetour',
            name='package_tour',
            field=models.ForeignKey(to='playstay.PackageTour', related_name='booked_package'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackagetour',
            name='user',
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='booked_package', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackagehotel',
            name='booked_package',
            field=models.ForeignKey(null=True, to='playstay.BookedPackageTour', related_name='booked_hotel', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackagehotel',
            name='package_hotel_room',
            field=models.ForeignKey(to='playstay.PackageHotelRoomFee', related_name='booked_hotel'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackagegolfcourse',
            name='booked_package',
            field=models.ForeignKey(null=True, to='playstay.BookedPackageTour', related_name='booked_golfcourse', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackagegolfcourse',
            name='package_golfcourse',
            field=models.ForeignKey(to='playstay.PackageGolfcourseFee', related_name='booked_golfcourse'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackageadditional',
            name='booked_package',
            field=models.ForeignKey(null=True, to='playstay.BookedPackageTour', related_name='booked_additional', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookedpackageadditional',
            name='package_additional',
            field=models.ForeignKey(to='playstay.PackageAdditionalFee', related_name='booked_additional'),
            preserve_default=True,
        ),
    ]
