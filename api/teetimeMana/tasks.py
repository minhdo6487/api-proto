import os
import datetime
from pytz import timezone, country_timezones

from django.db.models import Max
from django.core.mail import send_mail

from core.teetime.models import GCKeyPrice, \
    PaymentMethodSetting, \
    GC24PriceByBooking_Detail, \
    TeeTimePrice, \
    TeeTime, \
    RecurringTeetime

from celery import shared_task, task
from utils.rest.sendemail import send_email
from django.db.models import Q
from GolfConnect.settings import CURRENT_ENV, ADMIN_EMAIL_RECIPIENT


@task(name='compare_price_and_notice')
def compare_price_and_notice(teetime_list_id):
    message_template = '[<b>{golfcourse}</b>] Teetime on <b>{date}</b> at <b>{time}</b> with hole <b>{hole}</b> has price <b>{price}</b> lower than gc24 price <b>{higher_price}</b>'
    message_template_2 = '[<b>{golfcourse}</b>] Teetime on <b>{date}</b> at <b>{time}</b> with hole <b>{hole}</b> doesn\'t have GC24 price'
    message = []
    if not teetime_list_id:
        return
    teetime_list = TeeTime.objects.filter(id__in=teetime_list_id)
    for teetime in teetime_list:
        teetime_price_list = TeeTimePrice.objects.filter(teetime_id=teetime.id).order_by('hole')
        teetime_standard = TeeTimePrice.objects.filter(teetime_id=teetime.id, hole=18).first()
        if not teetime_price_list.exists() or not teetime_standard:
            continue
        cash_discount = teetime_standard.cash_discount
        online_discount = teetime_standard.online_discount
        for teetime_price in teetime_price_list:
            booked_day = teetime_price.teetime.date.strftime("%a")
            price = teetime_price.price * (100 - cash_discount - online_discount) / 100
            filter_condition = {
                'gc24price__golfcourse': teetime_price.teetime.golfcourse,
                'gc24price__from_date__lte': teetime_price.teetime.date,
                'gc24price__to_date__gte': teetime_price.teetime.date,
                'date': booked_day,
                'from_time__lte': teetime_price.teetime.time,
                'to_time__gte': teetime_price.teetime.time
            }
            gc24price = GC24PriceByBooking_Detail.objects.filter(Q(**filter_condition)).first()
            if not gc24price:
                m = message_template_2.format(golfcourse=teetime_price.teetime.golfcourse.name,
                                              date=teetime_price.teetime.date, time=teetime_price.teetime.time,
                                              hole=teetime_price.hole)
                message.append(m)
            else:
                key = "price_{0}"
                gc24_price = getattr(gc24price, key.format(teetime_price.hole))
                if price <= gc24_price:
                    m = message_template.format(golfcourse=teetime_price.teetime.golfcourse.name,
                                                date=teetime_price.teetime.date, time=teetime_price.teetime.time,
                                                hole=teetime_price.hole, price=int(price), higher_price=int(gc24_price))
                    message.append(m)
    if not message:
        return
    message = '<br>'.join(message)
    email_title = '[{0}] Import Higher Price Alert'.format(CURRENT_ENV.upper())
    if ADMIN_EMAIL_RECIPIENT:
        send_email(email_title, message, ADMIN_EMAIL_RECIPIENT)


@task(name='monthly_archive_teetime')
def monthly_archive_teetime(teetime_data):
    from core.teetime.models import ArchivedTeetime, TeeTime
    import json
    if not teetime_data:
        return
    for tt in teetime_data:
        ArchivedTeetime.objects.create(**tt)
        TeeTime.objects.get(id=tt.teetime_id).delete()


@shared_task
def import_teetime_recurring_queue():
    re_teetime = RecurringTeetime.objects.all()
    if not re_teetime:
        return

    email_data = []
    for rt in re_teetime:
        tz = timezone(country_timezones(rt.golfcourse.country.short_name)[0])
        now = datetime.datetime.utcnow()
        current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
        #### Check next date: publish: move date, recurring: move back and plus 7
        ### Get the max date of teetime exists
        max_date = TeeTime.objects.filter(golfcourse=rt.golfcourse).aggregate(Max('date'))['date__max']
        if not max_date:
            continue
        if not rt.publish_period and not rt.recurring_freq:
            continue
        if (current_tz.date() + datetime.timedelta(days=rt.publish_period)) < max_date:
            continue
        list_date = []
        for i in range(1, rt.recurring_freq + 1):
            next_date = max_date + datetime.timedelta(days=i)
            get_date = next_date - datetime.timedelta(days=7)
            tt = TeeTime.objects.filter(golfcourse=rt.golfcourse, date=get_date)
            if tt.exists():
                list_date.append(next_date)
                for t in tt:
                    teetime_price = TeeTimePrice.objects.filter(teetime=t)
                    t.date = next_date
                    t.is_hold = False
                    t.is_block = False
                    t.is_booked = False
                    t.is_request = False
                    t.id = None
                    t.save()
                    for tp in teetime_price:
                        tp.teetime = t
                        tp.id = None
                        tp.is_publish = True
                        tp.save()
        if list_date:
            data = {rt.golfcourse.name: list_date}
            email_data.append(data)

    # send_email(email_data)
    if not email_data:
        return

    template = "Import {0} at [{1}]"
    message = ""
    for d in email_data:
        for k, v in d.items():
            message += template.format(k, ', '.join(map(str, v))) + "\n"

    if ADMIN_EMAIL_RECIPIENT:
        send_mail('Import teetime date {} - env {}'.format(datetime.date.today(), CURRENT_ENV),
                  message,
                  'GolfConnect24 <no-reply@golfconnect24.com>',
                  ADMIN_EMAIL_RECIPIENT,
                  fail_silently=True)
