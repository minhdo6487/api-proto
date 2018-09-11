import datetime
from pytz import timezone, country_timezones
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.timezone import utc
from django.db.models.signals import pre_save, post_save, pre_delete
from django.db.models import Q
from django.dispatch import receiver
from django.db.models import Max
from core.golfcourse.models import GolfCourse
from api.dealMana.tasks import handle_realtime_booking_deal, stop_job_real_time_deal_now, notify_discount, notify_online_discount
from celery.task.control import revoke
from utils.django.models import get_or_none
BLOCK = 'B'
DEFAULT = 'D'
ANOTHER = 'A'
DELETED = 'DEL'

ACTIVE = 'A'
GUEST_TYPE_CHOICE = (
    (BLOCK, 'Block'),
    (ACTIVE, 'Active'),
)

WEEKEND = 'weekend'
WEEKDAY = 'weekday'
HOLIDAY = 'holiday'
DATE_TYPE_CHOICE = (
    (WEEKDAY, 'Weekend'),
    (WEEKEND, 'Weekday'),
    (HOLIDAY, 'Holiday'),
    (ANOTHER, 'Another')
)
MON = 'Mon'
TUE = 'Tue'
WED = 'Wed'
THU = 'Thu'
FRI = 'Fri'
SAT = 'Sat'
SUN = 'Sun'
DATE_CHOICE = (
    (MON, 'Mon'),
    (TUE, 'Tue'),
    (WED, 'Wed'),
    (THU, 'Thu'),
    (FRI, 'Fri'),
    (SAT, 'Sat'),
    (SUN, 'Sun'))


class TeeTime(models.Model):
    time = models.TimeField(db_index=True)
    date = models.DateField(db_index=True)
    # datetime      = models.DateTimeField()
    golfcourse = models.ForeignKey(GolfCourse, related_name='teetime')
    description = models.CharField(max_length=1000, blank=True)
    # subgolfcourse = models.ForeignKey(SubGolfCourse, related_name='teetime')
    is_block = models.BooleanField(default=False, db_index=True)
    is_hold = models.BooleanField(default=False, db_index=True)
    is_booked = models.BooleanField(default=False, db_index=True)
    is_request = models.BooleanField(default=False, db_index=True)
    min_player = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    max_player = models.PositiveIntegerField(null=True, validators=[MinValueValidator(1)])
    hold_expire = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(null=True, blank=True, editable=False)
    modified = models.DateTimeField(null=True, blank=True)
    available = models.BooleanField(default=True, db_index=True)
    allow_payonline = models.BooleanField(default=True, db_index=True)
    allow_paygc = models.BooleanField(default=True, db_index=True)

    # class Meta:
    #     unique_together = ('date', 'time', 'golfcourse')
    def __str__(self):
        return "{0}-{1} {2}".format(self.date, self.time, self.golfcourse.short_name)
    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.created = datetime.datetime.utcnow().replace(tzinfo=utc)
        self.modified = datetime.datetime.utcnow().replace(tzinfo=utc)
        # self.datetime = datetime.datetime.combine(self.date, self.time)
        return super(TeeTime, self).save(*args, **kwargs)


class GuestType(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='guest_type')
    level = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=100, db_index=True)
    description = models.CharField(max_length=1000, blank=True, null=True)
    color = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=2, choices=GUEST_TYPE_CHOICE, default=ACTIVE)


# class GolfCourseRanking(models.Model):
#     golfcourse  = models.ForeignKey(GolfCourse, related_name='guest_type')
#     rank        = models.PositiveSmallIntegerField(default=0)
#     description = models.CharField(max_length=1000, blank=True, null=True)

#   Setting teetime by GolfCourse
class GCSetting(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='gc_setting', unique=True)
    # maximun number teetime can be duplicate (date, time) by one golfcourse
    max_duplicate = models.PositiveSmallIntegerField(default=0)


class TeeTimePrice(models.Model):
    teetime = models.ForeignKey(TeeTime, related_name='teetime_price')
    guest_type = models.ForeignKey(GuestType, related_name='teetime_price')
    hole = models.PositiveSmallIntegerField(default=9)
    price = models.FloatField(default=0)
    price_standard = models.FloatField(default=0)
    cash_discount = models.FloatField(default=0)
    online_discount = models.FloatField(default=0)
    is_publish = models.BooleanField(default=False, db_index=True)
    gifts = models.CharField(max_length=500, blank=True, null=True)
    food_voucher = models.BooleanField(default=False)
    buggy = models.BooleanField(default=False)
    caddy = models.BooleanField(default=False)

    class Meta:
        unique_together = ('teetime', 'guest_type', 'hole')
def get_LongThanh_golfcourse():
    try:
        return GolfCourse.objects.get(short_name='Long Thanh').id
    except:
        return None
CONTENT_HELP_TEXT = ' '.join(['<p>Example: from_date: <strong>2016-09-15</strong>, to_date: <strong>2016-09-23</strong>',
                              'from_time: <strong>13:00</strong>, to_time: <strong>15:00</strong><br/>',
                              '2016-09-20 Long Thanh has teetime from 6:00 to 16:00.',
                              'Just teetime from 13:00 to 15:00 have <strong>Free/Show</strong> buggy.',
                              'Remain will be not'])
class TeetimeFreeBuggySetting(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='teetime_free_buggy_setting',default=get_LongThanh_golfcourse, help_text=CONTENT_HELP_TEXT)
    from_date = models.DateField(default=datetime.date.today())
    to_date = models.DateField(default=datetime.date.today())
    from_time = models.TimeField(default=datetime.time.min)
    to_time = models.TimeField(default=datetime.time.max)
    free = models.BooleanField(default=False)
    def __str__(self):
        return self.golfcourse.name + str(self.from_date) + str(self.to_date)

@receiver(post_save, sender=TeetimeFreeBuggySetting, dispatch_uid="update_buggy_teetime_setting")
def update_buggy_teetime_setting(sender, instance, **kwargs):
    filter_condition = {
        'teetime__golfcourse_id': instance.golfcourse.id,
        'teetime__date__gte': instance.from_date,
        'teetime__date__lte': instance.to_date,
        'teetime__time__gte': instance.from_time,
        'teetime__time__lte': instance.to_time,
    }
    teetime_price = TeeTimePrice.objects.filter(Q(**filter_condition))
    if not teetime_price.exists():
        return
    for tp in teetime_price:
        tp.buggy = instance.free
        tp.save()

class TeetimeShowBuggySetting(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='teetime_show_buggy_setting',default=get_LongThanh_golfcourse, help_text=CONTENT_HELP_TEXT)
    from_date = models.DateField(default=datetime.date.today())
    to_date = models.DateField(default=datetime.date.today())
    from_time = models.TimeField(default=datetime.time.min)
    to_time = models.TimeField(default=datetime.time.max)
    show = models.BooleanField(default=False)
    def __str__(self):
        return self.golfcourse.name + str(self.from_date) + str(self.to_date)

################### Not calculate for end deal yet
class Deal(models.Model):
    deal_code = models.CharField(max_length=500, db_index=True)
    golfcourse = models.ForeignKey(GolfCourse, related_name='deal')
    effective_date = models.DateField(default=datetime.date.today())
    effective_time = models.TimeField(default=datetime.time.min)
    expire_date = models.DateField(default=datetime.date.today())
    expire_time = models.TimeField(default=datetime.time.max)
    end_date = models.DateField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    hole = models.CharField(max_length=20, default='0')
    active = models.BooleanField(default=False)
    is_base = models.BooleanField(default=False)
    def __str__(self):
        return self.deal_code + "--" + self.golfcourse.name

class TimeRangeType(models.Model):
    type_name = models.CharField(max_length=500)
    from_time = models.TimeField(default=datetime.time.min, db_index=True)
    to_time = models.TimeField(default=datetime.time.max, db_index=True)
    golfcourse = models.ForeignKey(GolfCourse, related_name='timerange')
    deal = models.ForeignKey(Deal, related_name='deal', null=True)

class BookingTime(models.Model):
    deal = models.ForeignKey(Deal, related_name='bookingtime')
    date = models.DateField(default=datetime.date.today())
    from_time = models.TimeField()
    to_time = models.TimeField()

@receiver(post_save, sender=BookingTime, dispatch_uid="start_job_bookingtime")
def start_job_bookingtime(sender, instance, **kwargs):
    if instance.deal.active and not instance.deal.is_base:
        handle_realtime_booking_deal(instance)

class JobBookingTime(models.Model):
    bookingtime = models.ForeignKey(BookingTime, related_name='job_bookingtime')
    schedule_task_id = models.CharField(max_length=500)
    schedule_end_task_id = models.CharField(max_length=500, null=True, blank=True)

class DealEffective_TimeRange(models.Model):
    bookingtime = models.ForeignKey(BookingTime, related_name='timerange')
    timerange = models.ForeignKey(TimeRangeType, related_name='timerange')
    date = models.DateField(blank=True, null=True)
    discount = models.FloatField(default=0)

@receiver(post_save, sender=DealEffective_TimeRange, dispatch_uid="update_discount_from_deal")
def update_discount(sender, instance, **kwargs):
    if not instance.bookingtime.deal.is_base:
        return
    max_date = TeeTime.objects.filter(golfcourse=instance.bookingtime.deal.golfcourse, date__gte=instance.date).aggregate(Max('date'))['date__max']
    this_date = instance.date
    delta = datetime.timedelta(days=7)
    if not max_date:
        return
    while this_date <= max_date:
        teetime = TeeTime.objects.filter(golfcourse=instance.bookingtime.deal.golfcourse, date=this_date).values('id')
        teetime_id = [k['id'] for k in teetime]
        teetime_price = TeeTimePrice.objects.filter(teetime__in=teetime_id)
        for t in teetime_price:
            t.online_discount=instance.discount
            t.save()
        this_date += delta
@receiver(post_save, sender=Deal, dispatch_uid="start_job_bookingtime_deal")
def start_job_bookingtime_deal(sender, instance, **kwargs):
    if instance.active and not instance.is_base:
        list_bookingtime = instance.bookingtime.all()
        if list_bookingtime:
            for lb in list_bookingtime:
                handle_realtime_booking_deal(lb)
    elif not instance.active:
        list_bt = instance.bookingtime.all()
        list_bookingtime = [l.id for l in list_bt]
        if list_bookingtime:
            job_schedule = JobBookingTime.objects.filter(bookingtime__in=list_bookingtime)
            if job_schedule.exists():
                for job in job_schedule:
                    if job.schedule_task_id:
                        revoke(job.schedule_task_id, terminate=True)
                    if job.schedule_end_task_id:
                        revoke(job.schedule_end_task_id, terminate=True)
                    job.delete()
            now = datetime.datetime.utcnow()
            for lb in list_bookingtime:
                bookingtime = get_or_none(BookingTime, pk=lb)
                stop_job_real_time_deal_now.apply_async(args=[lb],eta=now)
class DealEffective_TeeTime(models.Model):
    bookingtime = models.ForeignKey(BookingTime, related_name='bookingtime')
    timerange = models.PositiveSmallIntegerField(default=0)
    hole = models.CharField(max_length=20, default='0')
    teetime = models.ForeignKey(TeeTime, related_name='teetime_deal')
    date = models.DateField(blank=True, null=True)
    discount = models.FloatField(default=0)
    modified = models.DateTimeField(null=True, blank=True)
    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        tz = timezone(country_timezones(self.bookingtime.deal.golfcourse.country.short_name)[0])
        now = datetime.datetime.utcnow()
        current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
        from_time = (datetime.datetime.combine(current_tz.date(), current_tz.time()) + datetime.timedelta(seconds=1)).time()
        from_date = current_tz.date()
        filter_deal = {
                'teetime': self.teetime.id,
                'bookingtime__deal__active': True,
                'bookingtime__deal__is_base': False,
                'bookingtime__date': from_date,
                'bookingtime__from_time__lte': from_time,
                'bookingtime__to_time__gte': from_time
        }

        filter_exclude1 = {
            'bookingtime__deal__effective_date': from_date,
            'bookingtime__deal__effective_time__gte': from_time 
        }
        filter_exclude2 = {
            'bookingtime__deal__expire_date': from_date,
            'bookingtime__deal__expire_time__lte': from_time 
        }
        dealteetime = DealEffective_TeeTime.objects.filter(Q(**filter_deal)).exclude(Q(**filter_exclude1) | Q(**filter_exclude2)).order_by('-modified')
        if dealteetime.exists():
            d = dealteetime.first()
            channel = 'booking-' + str(d.teetime.date)
            notify_discount(d.teetime.id, d.discount, channel)
        self.modified = datetime.datetime.utcnow().replace(tzinfo=utc)
        return super(DealEffective_TeeTime, self).save(*args, **kwargs)

@receiver(pre_delete, sender=DealEffective_TeeTime, dispatch_uid="stop_job_real_time_deal_teetime_now")
def stop_job_real_time_deal_teetime_now(sender, instance, **kwargs):
    tz = timezone(country_timezones(instance.bookingtime.deal.golfcourse.country.short_name)[0])
    now = datetime.datetime.utcnow()
    current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
    from_time = (datetime.datetime.combine(current_tz.date(), current_tz.time()) + datetime.timedelta(seconds=1)).time()
    from_date = current_tz.date()
    filter_deal = {
            'teetime': instance.teetime.id,
            'bookingtime__deal__active': True,
            'bookingtime__deal__is_base': False,
            'bookingtime__date': from_date,
            'bookingtime__from_time__lte': from_time,
            'bookingtime__to_time__gte': from_time
    }

    filter_exclude1 = {
        'bookingtime__deal__effective_date': from_date,
        'bookingtime__deal__effective_time__gte': from_time 
    }
    filter_exclude2 = {
        'bookingtime__deal__expire_date': from_date,
        'bookingtime__deal__expire_time__lte': from_time 
    }
    filter_exclude3 = {
        'bookingtime': instance.bookingtime.id
    }
    dealteetime = DealEffective_TeeTime.objects.filter(Q(**filter_deal)).exclude(Q(**filter_exclude1) | Q(**filter_exclude2) | Q(**filter_exclude3)).order_by('-modified')
    if dealteetime.exists():
        d = dealteetime.first()
        channel = 'booking-' + str(d.teetime.date)
        notify_discount(d.teetime.id, d.discount, channel)
    else:
        tt = TeeTimePrice.objects.filter(teetime_id=instance.teetime.id,is_publish=True,hole=18).first()
        if tt:
            channel = 'booking-' + str(tt.teetime.date)
            notify_discount(tt.teetime.id, tt.online_discount, channel)

class RecurringTeetime(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='recurringteetime')
    recurring_freq = models.PositiveSmallIntegerField(default=0)
    publish_period = models.PositiveSmallIntegerField(default=0)


class Gc24TeeTimePrice(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='gc24_teetime_price')
    date = models.DateField(blank=True, null=True, db_index=True)
    price_9_wd = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_18_wd = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_27_wd = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_36_wd = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_9_wk = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_18_wk = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_27_wk = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    price_36_wk = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)

    created = models.DateTimeField(null=True, blank=True, editable=False)
    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.created = datetime.datetime.utcnow().replace(tzinfo=utc)
            if not self.date:
                self.date = datetime.datetime.utcnow().replace(tzinfo=utc)
        return super(Gc24TeeTimePrice, self).save(*args, **kwargs)

    def __str__(self):
        return self.golfcourse.name + str(self.date)

class GC24DiscountOnline(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='gc24_discount_online')
    discount = models.FloatField(default=0)
    created = models.DateTimeField(null=True, blank=True, editable=False)
    def save(self, *args, **kwargs):
        self.created = datetime.date.today()
        return super(GC24DiscountOnline, self).save(*args, **kwargs)
    def __str__(self):
        return self.golfcourse.name + " " +str(self.created)

@receiver(post_save, sender=GC24DiscountOnline, dispatch_uid="update_discount_online")
def update_discount_online(sender, instance, **kwargs):
    teetime = TeeTime.objects.filter(golfcourse=instance.golfcourse, date__gte=instance.created).order_by('-id').values('id')
    teetime_id = [k['id'] for k in teetime]
    list_tid = []
    teetime_price = TeeTimePrice.objects.filter(teetime__in=teetime_id)
    for t in teetime_price:
        if t.teetime.id not in list_tid:
            channel = 'booking-' + str(t.teetime.date)
            notify_online_discount.delay(t.teetime.id, instance.discount, channel)
            list_tid.append(t.teetime.id)
        t.cash_discount=instance.discount
        t.save()

class GCKeyPrice(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='gc_key_price')
    mon_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    tue_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    wed_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    thu_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    fri_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    sat_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    sun_price = models.DecimalField(max_digits=9, decimal_places=2,default=0.00)
    created = models.DateTimeField(null=True, blank=True, editable=False)
    def save(self, *args, **kwargs):
        self.created = datetime.date.today()
        return super(GCKeyPrice, self).save(*args, **kwargs)
    def __str__(self):
        return self.golfcourse.name + " " +str(self.created)

@receiver(post_save, sender=GCKeyPrice, dispatch_uid="update_key_price")
def update_key_price(sender, instance, **kwargs):
    teetime = TeeTime.objects.filter(golfcourse=instance.golfcourse, date__gte=instance.created).values('id')
    teetime_id = [k['id'] for k in teetime]
    teetime_price = TeeTimePrice.objects.filter(teetime__in=teetime_id, hole=18)
    if teetime_price.exists():
        key = "{0}_price"
        for t in teetime_price:
            day = t.teetime.date.strftime("%a").lower()
            price = getattr(instance,key.format(day))
            t.price=price
            t.save()
# def set_default_values(sender, instance, **kwargs):
#     if not instance.id:
#         if instance.type == 'D':
#             try:
#                 temp = sender.objects.get(golfcourse=instance.golfcourse, subgolfcourse=instance.subgolfcourse,
#                                           type='D')
#                 sender.objects.filter(Q(golfcourse=instance.golfcourse), Q(subgolfcourse=instance.subgolfcourse),
#                                       Q(date_start__gte=instance.date_start),
#                                       Q(date_end__lte=instance.date_end), ~Q(type='D)')).delete()
#                 if instance != temp:
#                     instance.id = temp.id
#                 if instance.cancel_hour is None:
#                     instance.cancel_hour = temp.cancel_hour
#                 if instance.pay_online_discount is None:
#                     instance.pay_online_discount = temp.pay_online_discount
#                 if instance.pay_atgolf_discount is None:
#                     instance.pay_atgolf_discount = temp.pay_atgolf_discount
#             except TeeTimeSetting.DoesNotExist:
#                 pass
#         default_setting = instance.golfcourse.golfcourse_settings
#         if instance.time_start is None:
#             instance.time_start = default_setting.open_time
#         if instance.time_end is None:
#             instance.time_end = default_setting.close_time
#         if instance.date_start is None:
#             instance.date_start = datetime.date.today()


# pre_save.connect(set_default_values, TeeTimeSetting)

class PriceType(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='price_type')
    from_time = models.TimeField()
    to_time = models.TimeField(blank=True, null=True)
    description = models.CharField(max_length=500)
    status = models.CharField(max_length=2, choices=GUEST_TYPE_CHOICE, default=ACTIVE)


class PriceMatrixLog(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='price_matrix_log')
    effective_date = models.DateField(blank=True, null=True)
    hole = models.PositiveSmallIntegerField(default=9)
    created = models.DateTimeField(null=True, blank=True, editable=False)
    modified = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.created = datetime.datetime.utcnow().replace(tzinfo=utc)
        self.modified = datetime.datetime.utcnow().replace(tzinfo=utc)
        return super(PriceMatrixLog, self).save(*args, **kwargs)

    class Meta:
        ordering = ('-effective_date',)
        unique_together = ('effective_date', 'golfcourse', 'hole')


class PriceMatrix(models.Model):
    matrix_log = models.ForeignKey(PriceMatrixLog, related_name='price_matrix')
    guest_type = models.ForeignKey(GuestType, related_name='price_matrix')
    price_type = models.ForeignKey(PriceType, related_name='price_matrix')
    price = models.FloatField(default=0)
    date_type = models.CharField(max_length=10, choices=DATE_TYPE_CHOICE)
    date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ('price_type', 'guest_type', 'date_type', 'date')


class Holiday(models.Model):
    date = models.DateField()


class CrawlTeeTime(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='crawl_teetime')
    date = models.DateField(blank=True, null=True, db_index=True)
    time= models.TimeField(blank=True, null=True, db_index=True)
    price = models.FloatField(default=0)
    higher_price = models.FloatField(default=0)
    is_sent = models.BooleanField(default=False)
    created = models.DateTimeField(null=True, blank=True, editable=False)

class GC24PriceByBooking(models.Model):
        golfcourse  = models.ForeignKey(GolfCourse, related_name='gc24pricebooking')
        from_date = models.DateField(default=datetime.date.today())
        to_date = models.DateField(default=datetime.date.today())
        def __str__(self):
            return self.golfcourse.name + "--" +str(self.from_date) + "--" + str(self.to_date)
class GC24PriceByBooking_Detail(models.Model):
        gc24price = models.ForeignKey(GC24PriceByBooking, related_name='gc24pricebooking')
        date = models.CharField(max_length=3,choices=DATE_CHOICE,default=MON)
        from_time = models.TimeField(default=datetime.time.min)
        to_time = models.TimeField(default=datetime.time.max) 
        price_9 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        price_18 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        price_27 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        price_36 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        def __str__(self):
            return self.gc24price.golfcourse.name + "--"+ self.date + "--" +str(self.from_time) + "--" + str(self.to_time)
class GC24PriceByDeal(models.Model):
        deal = models.ForeignKey(Deal, related_name="gc24price")
        date = models.CharField(max_length=3,choices=DATE_CHOICE,default=MON)
        from_time = models.TimeField(default=datetime.time.min)
        to_time = models.TimeField(default=datetime.time.max) 
        price_9 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        price_18 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        price_27 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        price_36 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
        def __str__(self):
            return self.deal.golfcourse.name + "--" + self.deal.deal_code + "--" + self.date + "--" +str(self.from_time) + "--" + str(self.to_time)


class PaymentMethodSetting(models.Model):
        golfcourse = models.ForeignKey(GolfCourse, related_name='payment_method_setting')
        date = models.CharField(max_length=3,choices=DATE_CHOICE,default=MON)
        allow_payonline = models.BooleanField(default=True, db_index=True)
        allow_paygc = models.BooleanField(default=True, db_index=True)
        apply_now = models.BooleanField(default=True, db_index=True)
        created = models.DateTimeField(null=True, blank=True, editable=False)
        def save(self, *args, **kwargs):
            self.created = datetime.date.today()
            return super(PaymentMethodSetting, self).save(*args, **kwargs)
        def __str__(self):
            return "{0}--{1}".format(self.golfcourse.short_name, self.date)

@receiver(post_save, sender=PaymentMethodSetting, dispatch_uid="update_setting_paymentmethod")
def update_setting_paymentmethod(sender, instance, **kwargs):
    if not instance.apply_now:
        return
    teetime = TeeTime.objects.filter(golfcourse=instance.golfcourse, date__gte=instance.created)
    if teetime.exists():
        for tt in teetime:
            tt_date = tt.date.strftime("%a")
            if instance.date.lower() == tt_date.lower():
                tt.allow_paygc = instance.allow_paygc
                tt.allow_payonline = instance.allow_payonline
                tt.save()

class ArchivedTeetime(models.Model):
    teetime_id = models.PositiveIntegerField()
    time = models.TimeField()
    date = models.DateField()
    description = models.CharField(max_length=100)
    is_block = models.BooleanField(default=False)
    is_hold = models.BooleanField(default=False)
    is_booked = models.BooleanField(default=False)
    is_request = models.BooleanField(default=False)
    min_player = models.PositiveSmallIntegerField()
    available = models.BooleanField(default=False)
    allow_payonline = models.BooleanField(default=False)
    allow_paygc = models.BooleanField(default=False)
    golfcourse_name = models.CharField(max_length=255)
    golfcourse_website = models.CharField(max_length=255)
    golfcourse_contact = models.CharField(max_length=255)
    golfcourse_id = models.PositiveIntegerField()
    golfcourse_short_name = models.CharField(max_length=255)
    golfcourse_country = models.CharField(max_length=255)
    golfcourse_address = models.CharField(max_length=255)
    price = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    price_9 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    price_18 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    price_27 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    price_36 = models.DecimalField(default=0.0, max_digits=20, decimal_places=2)
    discount = models.FloatField()
    discount_online = models.FloatField()
    gifts = models.CharField(max_length=255)
    food_voucher = models.BooleanField(default=False)
    buggy = models.BooleanField(default=False)
    caddy = models.BooleanField(default=False)
    rank = models.IntegerField()
    created = models.DateTimeField(null=True, blank=True, editable=False)
    def save(self, *args, **kwargs):
        self.created = datetime.date.today()
        return super(ArchivedTeetime, self).save(*args, **kwargs)
    def __str__(self):
        return "{0}--{1}--{2}".format(self.golfcourse_short_name, self.date, self.time)