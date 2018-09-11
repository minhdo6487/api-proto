# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0006_auto_20180110_0032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='golfcourseevent',
            name='payment_discount',
            field=models.CharField(choices=[('10', 'pay now'), ('5', 'pay later')], default='5', max_length=20),
            preserve_default=True,
        ),
    ]
