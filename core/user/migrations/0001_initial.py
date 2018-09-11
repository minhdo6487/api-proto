# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('location', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Degree',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FavClubset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clubset', models.CharField(blank=True, null=True, max_length=200)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='fav_clubset')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FavGolfCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('golfcourse', models.CharField(blank=True, null=True, max_length=300)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='fav_golfcourse')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupChat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modified_at', models.DateTimeField(blank=True, null=True)),
                ('member_list', models.TextField(blank=True, null=True)),
                ('group_id', models.CharField(blank=True, null=True, max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(blank=True, null=True, max_length=100)),
                ('company_name', models.CharField(blank=True, null=True, max_length=100)),
                ('address', models.TextField(blank=True, null=True)),
                ('tax_code', models.CharField(blank=True, null=True, max_length=100)),
                ('created', models.DateTimeField(editable=False, blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Major',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MemberGolfCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('golfcourse', models.CharField(blank=True, null=True, max_length=300)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='member_golfcourse')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('verb', models.CharField(max_length=255, db_index=True)),
                ('date_creation', models.DateTimeField(editable=False, db_index=True, default=django.utils.timezone.now)),
                ('object_id', models.PositiveIntegerField()),
                ('public', models.BooleanField(db_index=True, default=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='activities')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(max_length=255)),
                ('push_token', models.CharField(blank=True, null=True, max_length=255)),
                ('device_type', models.CharField(max_length=20, db_index=True)),
                ('created_at', models.DateTimeField(editable=False, blank=True, null=True)),
                ('modified_at', models.DateTimeField(blank=True, null=True)),
                ('api_version', models.PositiveSmallIntegerField(blank=True, null=True, default=1)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserGroupChat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_joined', models.DateTimeField(blank=True, null=True)),
                ('groupchat', models.ForeignKey(to='user.GroupChat', related_name='group_member')),
                ('invited_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='group_invited_by', blank=True, default=None)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='group_member')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lon', models.FloatField()),
                ('lat', models.FloatField()),
                ('modified_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='location')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserPrivacy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('A', 'Allow'), ('D', 'Deny')], max_length=1, default='D')),
                ('target', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='privacy_target')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='privacy_owner')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deviceToken', models.CharField(blank=True, null=True, max_length=100)),
                ('middle_name', models.TextField(blank=True, null=True, max_length=20)),
                ('display_name', models.TextField(blank=True, null=True, max_length=50)),
                ('dob', models.DateField(blank=True, null=True)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('A', 'Another')], max_length=1, default='M')),
                ('address', models.TextField(blank=True, null=True, max_length=30)),
                ('location', models.CharField(blank=True, null=True, max_length=500)),
                ('description', models.TextField(blank=True, null=True)),
                ('job_title', models.TextField(blank=True, null=True, max_length=140)),
                ('company_name', models.TextField(blank=True, null=True, max_length=140)),
                ('business_area', models.CharField(blank=True, null=True, max_length=100)),
                ('university1', models.TextField(blank=True, null=True, max_length=140)),
                ('university2', models.TextField(blank=True, null=True, max_length=140)),
                ('mobile', models.CharField(blank=True, null=True, max_length=15)),
                ('handicap_36', models.CharField(max_length=8, blank=True, null=True, default='0')),
                ('handicap_us', models.CharField(max_length=8, blank=True, null=True, default='N/A')),
                ('usual_golf_time', models.CharField(max_length=15, default='Morning')),
                ('avg_score', models.FloatField(blank=True, null=True, default=100)),
                ('type_golf_game', models.CharField(max_length=15, blank=True, null=True, default='Friendly')),
                ('year_experience', models.FloatField(blank=True, null=True)),
                ('frequency_playing', models.FloatField(blank=True, null=True)),
                ('frequency_time_playing', models.CharField(max_length=15, blank=True, null=True, default='Weekend')),
                ('no_partner', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('profile_picture', models.CharField(blank=True, null=True, max_length=500)),
                ('book_success_counter', models.IntegerField(blank=True, null=True, default=0)),
                ('interests', models.TextField(blank=True, null=True)),
                ('personality', models.TextField(blank=True, null=True)),
                ('fav_pros', models.TextField(blank=True, null=True)),
                ('date_pass_change', models.DateField(blank=True, null=True)),
                ('favor_quotation', models.TextField(blank=True, null=True, max_length=99999)),
                ('is_member', models.BooleanField(default=False)),
                ('version', models.IntegerField(blank=True, null=True, default=1)),
                ('city', models.ForeignKey(null=True, to='location.City', blank=True)),
                ('district', models.ForeignKey(null=True, to='location.District', blank=True)),
                ('nationality', models.ForeignKey(null=True, to='location.Country', blank=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, related_name='user_profile')),
            ],
            options={
                'ordering': ('user',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(choices=[('V', 'VN'), ('E', 'EN'), ('A', 'Another')], max_length=1, default='V')),
                ('receive_email_notification', models.BooleanField(default=True)),
                ('public_profile', models.BooleanField(default=True)),
                ('visible_search', models.BooleanField(default=True)),
                ('receive_push_notification', models.BooleanField(default=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, related_name='usersettings')),
            ],
            options={
                'ordering': ('user',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.FloatField(default=1.0)),
                ('source', models.CharField(max_length=50, default='ios')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='userversion')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UsualPlaying',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usual_prac_day', models.CharField(choices=[('Sunday', 'Sunday'), ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday')], max_length=15, default='Sunday')),
                ('usual_golf_day', models.CharField(max_length=15, blank=True, null=True, choices=[('Sunday', 'Sunday'), ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday')])),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='usual_playing')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
