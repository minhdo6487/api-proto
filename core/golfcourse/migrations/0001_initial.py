# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('location', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonusParRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('par', models.PositiveSmallIntegerField()),
            ],
            options={
                'ordering': ('hole',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ClubSets',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(max_length=100)),
                ('price', models.DecimalField(decimal_places=2, max_digits=9)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventBlock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('reason', models.CharField(blank=True, null=True, max_length=1000)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventPrize',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player_name', models.CharField(blank=True, null=True, max_length=1000)),
                ('prize_name', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Flight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, null=True, max_length=1000)),
                ('date_created', models.DateField(editable=False, blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(max_length=50, db_index=True)),
                ('address', models.TextField(max_length=70)),
                ('description', models.TextField(blank=True, null=True, max_length=100000)),
                ('description_en', models.TextField(blank=True, null=True, max_length=100000)),
                ('picture', models.ImageField(upload_to='/Images/GolfCourse', blank=True)),
                ('logo', models.CharField(blank=True, null=True, max_length=200)),
                ('website', models.TextField(max_length=100)),
                ('member_type', models.CharField(choices=[('M', 'Member Only'), ('N', 'Non-Member')], max_length=2, default='N')),
                ('number_of_hole', models.IntegerField()),
                ('longitude', models.FloatField()),
                ('latitude', models.FloatField()),
                ('type', models.CharField(choices=[('R', 'Resort'), ('H', 'Hotel'), ('A', 'Another')], max_length=2, default='R')),
                ('level', models.CharField(choices=[('1', 'Level 1'), ('2', 'Level 2'), ('3', 'Level 3')], max_length=2, default='1')),
                ('phone', models.CharField(blank=True, null=True, max_length=100)),
                ('short_name', models.CharField(max_length=100, blank=True, db_index=True, null=True)),
                ('contact_info', models.TextField(blank=True, null=True)),
                ('owner_company', models.TextField(blank=True, null=True)),
                ('rating', models.IntegerField(db_index=True, default=0)),
                ('discount', models.IntegerField(default=0)),
                ('open_hour', models.CharField(blank=True, null=True, max_length=100)),
                ('cloth', models.TextField(blank=True, null=True)),
                ('partner', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'ordering': ('name',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseBookingSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancel_hour', models.IntegerField(default=0)),
                ('policy', models.TextField(null=True)),
                ('policy_en', models.TextField(null=True)),
                ('request_policy', models.TextField(null=True)),
                ('request_policy_en', models.TextField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseBuggy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('buggy', models.PositiveIntegerField(choices=[(1, 'Buggy 2 seat'), (2, 'Buggy 4 seat')], default=1)),
                ('from_date', models.DateField(null=True, blank=True, db_index=True, default=datetime.date(2017, 6, 14))),
                ('to_date', models.DateField(blank=True, null=True, default=datetime.date(2017, 6, 14))),
                ('price_9', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_18', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_27', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_36', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_standard_9', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_standard_18', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_standard_27', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_standard_36', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseCaddy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(max_length=100)),
                ('number', models.PositiveIntegerField(default=0)),
                ('shift', models.IntegerField(default=1)),
                ('price_9', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_18', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_27', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('price_36', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
            ],
            options={
                'ordering': ('id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseClubSets',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=9)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(editable=False, blank=True, null=True)),
                ('name', models.TextField(max_length=500, blank=True, db_index=True, null=True)),
                ('date_start', models.DateField(blank=True, db_index=True, null=True)),
                ('date_end', models.DateField(blank=True, null=True)),
                ('time', models.TimeField(blank=True, null=True)),
                ('pod', models.CharField(max_length=2, blank=True, null=True, choices=[('M', 'Morning'), ('A', 'Afternoon'), ('E', 'Evening')])),
                ('event_level', models.CharField(choices=[('1', 'Level 1'), ('2', 'Level 2'), ('3', 'Level 3')], max_length=2, blank=True, null=True, default='1')),
                ('calculation', models.CharField(choices=[('normal', 'normal'), ('net', 'net'), ('system36', 'system36'), ('hdcus', 'hdcus'), ('callaway', 'callaway'), ('stable_ford', 'stable_ford'), ('peoria', 'peoria'), ('db_peoria', 'db_peoria')], max_length=20, default='net')),
                ('pass_code', models.CharField(blank=True, null=True, max_length=100)),
                ('event_type', models.CharField(choices=[('GE', 'Golfcourse Event'), ('PE', 'Player Event')], max_length=2, default='PE')),
                ('rule', models.CharField(choices=[('scramble', 'scramble'), ('normal', 'normal')], max_length=20, default='normal')),
                ('score_type', models.CharField(choices=[('myEvent', 'My Event'), ('leaderboard', 'Leaderboard')], max_length=20, default='myEvent')),
                ('description', models.TextField(blank=True, null=True, max_length=999999999)),
                ('description_en', models.TextField(blank=True, null=True, max_length=999999999)),
                ('is_advertise', models.BooleanField(default=False)),
                ('is_publish', models.BooleanField(db_index=True, default=False)),
                ('has_result', models.BooleanField(default=False)),
                ('from_hdcp', models.PositiveIntegerField(blank=True, null=True)),
                ('to_hdcp', models.PositiveIntegerField(blank=True, null=True)),
                ('banner', models.CharField(blank=True, null=True, max_length=1000)),
                ('detail_banner', models.TextField(blank=True, null=True)),
                ('website', models.CharField(blank=True, null=True, max_length=1000)),
                ('contact_email', models.CharField(blank=True, null=True, max_length=500)),
                ('contact_phone', models.CharField(blank=True, null=True, max_length=100)),
                ('result_url', models.CharField(blank=True, null=True, max_length=500)),
                ('slug_url', models.CharField(blank=True, null=True, max_length=100)),
                ('discount', models.FloatField(blank=True, null=True)),
                ('price_range', models.CharField(blank=True, null=True, max_length=100)),
                ('location', models.CharField(blank=True, null=True, max_length=500)),
                ('allow_stay', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('-id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEventAdvertise',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('more_info', models.TextField(blank=True, null=True)),
                ('more_info_en', models.TextField(blank=True, null=True)),
                ('about', models.TextField(blank=True, null=True)),
                ('about_en', models.TextField(blank=True, null=True)),
                ('detail_banner', models.TextField(blank=True, null=True)),
                ('sponsor_html', models.TextField(blank=True, null=True)),
                ('schedule_html', models.TextField(blank=True, null=True)),
                ('description_html', models.TextField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEventBanner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEventHotel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('checkin', models.DateField()),
                ('checkout', models.DateField()),
                ('event', models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='event_hotel_info', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEventMoreInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icon', models.CharField(blank=True, null=True, max_length=255)),
                ('info', models.CharField(max_length=255)),
                ('event', models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='event_more_info', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEventPriceInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, null=True, max_length=255)),
                ('info', models.CharField(blank=True, null=True, max_length=255)),
                ('info_en', models.CharField(blank=True, null=True, max_length=255)),
                ('display', models.CharField(blank=True, null=True, max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('event', models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='event_price_info', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseEventSchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, null=True)),
                ('title', models.CharField(max_length=255)),
                ('details', models.TextField(blank=True, null=True)),
                ('event', models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='event_schedule', blank=True)),
            ],
            options={
                'ordering': ('date',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=10)),
                ('expire_date', models.DateField(blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='member')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='gc_member')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, null=True, max_length=600)),
                ('content', models.TextField(blank=True, null=True)),
                ('rating', models.IntegerField(default=0)),
                ('date_created', models.DateField(editable=False, blank=True, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='golfcourse_review')),
            ],
            options={
                'ordering': ('-date_created',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseServices',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provide', models.BooleanField(default=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allowEditInfo', models.BooleanField(default=True)),
                ('open_time', models.TimeField(default='6:00:00')),
                ('close_time', models.TimeField(default='16:00:00')),
                ('weekday_min', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], default=1)),
                ('weekday_max', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(4)], default=4)),
                ('weekend_min', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(3)], default=1)),
                ('weekend_max', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(4)], default=4)),
                ('weekend_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('weekday_price', models.DecimalField(decimal_places=2, max_digits=9, default=0.0)),
                ('golfcourse', models.OneToOneField(to='golfcourse.GolfCourse', related_name='golfcourse_settings')),
            ],
            options={
                'ordering': ('golfcourse',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GolfCourseStaff',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('A', 'GolfCourse Admin'), ('S', 'GolfCourse Staff')], max_length=2, default='S')),
                ('description', models.TextField(max_length=999999, null=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='golfstaff')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupOfEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_index', models.FloatField()),
                ('to_index', models.FloatField()),
                ('name', models.CharField(max_length=100)),
                ('event', models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='group_event', blank=True)),
            ],
            options={
                'ordering': ('from_index',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Hole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('holeNumber', models.IntegerField()),
                ('par', models.IntegerField()),
                ('hdcp_index', models.IntegerField()),
                ('picture', models.CharField(blank=True, null=True, max_length=300)),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lng', models.FloatField(blank=True, null=True)),
                ('photo', models.CharField(blank=True, null=True, max_length=500)),
            ],
            options={
                'ordering': ('holeNumber',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HoleInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('infotype', models.CharField(max_length=100)),
                ('metersy', models.FloatField(blank=True, null=True)),
                ('pixely', models.FloatField(blank=True, null=True)),
                ('metersx', models.FloatField(blank=True, null=True)),
                ('pixelx', models.FloatField(blank=True, null=True)),
                ('y', models.FloatField(blank=True, null=True)),
                ('x', models.FloatField(blank=True, null=True)),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lon', models.FloatField(blank=True, null=True)),
                ('hole', models.ForeignKey(to='golfcourse.Hole', related_name='holeinfo')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HoleTee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yard', models.IntegerField()),
                ('hole', models.ForeignKey(to='golfcourse.Hole', related_name='holetee')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Services',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(blank=True, max_length=50)),
                ('description', models.TextField(max_length=100000, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubGolfCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(max_length=100, db_index=True)),
                ('description', models.TextField(blank=True, null=True, max_length=100000)),
                ('picture', models.ImageField(upload_to='Images/SubGolfCourse', blank=True, null=True)),
                ('number_of_hole', models.IntegerField(blank=True, null=True, default=0)),
                ('for_booking', models.BooleanField(default=True)),
                ('golfcourse', models.ForeignKey(to='golfcourse.GolfCourse', related_name='subgolfcourse')),
            ],
            options={
                'ordering': ('-number_of_hole', 'name'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('color', models.CharField(blank=True, null=True, max_length=7)),
                ('slope', models.FloatField()),
                ('rating', models.FloatField()),
                ('subgolfcourse', models.ForeignKey(to='golfcourse.SubGolfCourse', related_name='teetype')),
            ],
            options={
                'ordering': ('color',),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='holetee',
            name='tee_type',
            field=models.ForeignKey(to='golfcourse.TeeType', related_name='holetee'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='hole',
            name='subgolfcourse',
            field=models.ForeignKey(to='golfcourse.SubGolfCourse', related_name='hole'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='groupofevent',
            unique_together=set([('event', 'name')]),
        ),
        migrations.AddField(
            model_name='golfcourseservices',
            name='services',
            field=models.ForeignKey(to='golfcourse.Services', related_name='services'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseeventbanner',
            name='event',
            field=models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='event_banner', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseeventadvertise',
            name='event',
            field=models.OneToOneField(null=True, to='golfcourse.GolfCourseEvent', related_name='advertise_info', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseevent',
            name='golfcourse',
            field=models.ForeignKey(to='golfcourse.GolfCourse', related_name='gc_event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseevent',
            name='tee_type',
            field=models.ForeignKey(null=True, to='golfcourse.TeeType', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseevent',
            name='user',
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='event_creator', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseclubsets',
            name='clubset',
            field=models.ForeignKey(to='golfcourse.ClubSets'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourseclubsets',
            name='golfcourse',
            field=models.ForeignKey(to='golfcourse.GolfCourse'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcoursecaddy',
            name='golfcourse',
            field=models.ForeignKey(to='golfcourse.GolfCourse', related_name='caddy_goldcourse'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcoursebuggy',
            name='golfcourse',
            field=models.ForeignKey(to='golfcourse.GolfCourse', related_name='buggy_golfcourse'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcoursebookingsetting',
            name='golfcourse',
            field=models.OneToOneField(null=True, to='golfcourse.GolfCourse', related_name='booking_setting', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourse',
            name='city',
            field=models.ForeignKey(null=True, to='location.City', related_name='golfcourse', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourse',
            name='country',
            field=models.ForeignKey(null=True, to='location.Country', related_name='golfcourse', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='golfcourse',
            name='district',
            field=models.ForeignKey(null=True, to='location.District', related_name='golfcourse', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flight',
            name='event',
            field=models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='flight', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventprize',
            name='event',
            field=models.ForeignKey(to='golfcourse.GolfCourseEvent'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventblock',
            name='event',
            field=models.ForeignKey(to='golfcourse.GolfCourseEvent', related_name='event_block'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventblock',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bonusparrule',
            name='event',
            field=models.ForeignKey(null=True, to='golfcourse.GolfCourseEvent', related_name='bonus_par', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bonusparrule',
            name='hole',
            field=models.ForeignKey(to='golfcourse.Hole'),
            preserve_default=True,
        ),
    ]
