# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0007_auto_20180110_0206'),
    ]

    operations = [
        migrations.AddField(
            model_name='golfcourseevent',
            name='payment_discount_value',
            field=models.FloatField(blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='golfcourseevent',
            name='payment_discount',
            field=models.CharField(default='A', max_length=20, choices=[('F', 'pay now'), ('N', 'pay later'), ('A', 'allow both method')]),
            preserve_default=True,
        ),
    ]
