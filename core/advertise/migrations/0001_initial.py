# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Advertise',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.DateTimeField()),
                ('to_date', models.DateTimeField()),
                ('notice_type', models.CharField(choices=[('L1', 'Left 1'), ('L2', 'Left 2'), ('L3', 'Left 3'), ('UF', 'User Feed')], max_length=2, default='L1')),
                ('image', models.ImageField(upload_to='fixtures', max_length=140, blank=True, default='')),
                ('link', models.TextField(max_length=200)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
