# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('golfcourse', '0008_auto_20180110_1032'),
    ]

    operations = [
        migrations.RenameField(
            model_name='golfcourseevent',
            old_name='payment_discount_value',
            new_name='payment_discount_value_later',
        ),
        migrations.RemoveField(
            model_name='golfcourseevent',
            name='payment_discount',
        ),
        migrations.AddField(
            model_name='golfcourseevent',
            name='payment_discount_value_now',
            field=models.FloatField(blank=True, null=True),
            preserve_default=True,
        ),
    ]
