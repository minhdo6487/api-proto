# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnswerChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_vi', models.CharField(max_length=8000)),
                ('question_en', models.CharField(max_length=8000)),
                ('code_name', models.CharField(max_length=8000)),
                ('type_question', models.CharField(choices=[('input', 'input'), ('choice', 'choice')], max_length=255, blank=True, null=True, default='input')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Questionair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('package_name', models.CharField(max_length=255)),
                ('referer_object', models.CharField(choices=[('UserProfile', 'UserProfile'), ('NotificationSetting', 'NotificationSetting')], max_length=255, blank=True, null=True, default='UserProfile')),
                ('modified_at', models.DateTimeField(editable=False, db_index=True, default=django.utils.timezone.now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuestionChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice_vi', models.CharField(max_length=8000)),
                ('choice_en', models.CharField(max_length=8000)),
                ('is_default', models.BooleanField(default=False)),
                ('question', models.ForeignKey(to='questionair.Question', related_name='question_choice')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='question',
            name='package',
            field=models.ForeignKey(to='questionair.Questionair', related_name='question'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answerchoice',
            name='choice',
            field=models.ForeignKey(null=True, to='questionair.QuestionChoice', related_name='answer_choice', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answerchoice',
            name='question',
            field=models.ForeignKey(to='questionair.Question', related_name='question_answer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answerchoice',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='user_answer_choice'),
            preserve_default=True,
        ),
    ]
