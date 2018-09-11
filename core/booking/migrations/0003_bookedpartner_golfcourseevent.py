# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0002_customer_golfcourse'),
        ('booking', '0002_clonebookedteetime'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookedPartner_GolfcourseEvent',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('bookedgolfcourse', models.ForeignKey(to='booking.BookedGolfcourseEvent', related_name='book_partner_gcevent')),
                ('customer', models.ForeignKey(to='customer.Customer', related_name='book_partner_gcevent', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
