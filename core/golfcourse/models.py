# -*- coding: utf-8 -*-
import datetime, json
from urllib.request import Request
from urllib.parse import urlencode

from GolfConnect.settings import XMPP_HOST, XMPP_PORT
from api.userMana.tasks import log_activity
from django.contrib.contenttypes.models import ContentType

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Avg
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.contrib.auth.models import User
from core.like.models import Like

from core.location.models import City, District, Country

from core.realtime.models import UserSubcribe
from core.user.models import UserActivity

RESORT = 'R'
HOTEL = 'H'
ANOTHER = 'A'
TYPE_CHOICES = (
    (RESORT, 'Resort'),
    (HOTEL, 'Hotel'),
    (ANOTHER, 'Another')
)

MEMBER = 'M'
NONMEMBER = 'N'
MEMBER_TYPE_CHOICES = (
    (MEMBER, 'Member Only'),
    (NONMEMBER, 'Non-Member')
)

LEVEL1 = '1'
LEVEL2 = '2'
LEVEL3 = '3'
EVENT_LEVEL = (
    (LEVEL1, 'Level 1'),
    (LEVEL2, 'Level 2'),
    (LEVEL3, 'Level 3')
)

ADMIN = 'A'
STAFF = 'S'
STAFF_TYPE_CHOICES = (
    (ADMIN, 'GolfCourse Admin'),
    (STAFF, 'GolfCourse Staff')
)
NET = 'net'
SYSTEM36 = 'system36'
HDCP_USGA = 'hdcus'
CALLAWAY = 'callaway'
STABLE_FORD = 'stable_ford'
PEORIA = 'peoria'
DOUBLE_PEORIA = 'db_peoria'
NORMAL = 'normal'
CALCULATION = (
    (NORMAL, 'normal'),
    (NET, 'net'),
    (SYSTEM36, 'system36'),
    (HDCP_USGA, 'hdcus'),
    (CALLAWAY, 'callaway'),
    (STABLE_FORD, 'stable_ford'),
    (PEORIA, 'peoria'),
    (DOUBLE_PEORIA, 'db_peoria')
)
GC_EVENT = 'GE'
PLAYER_EVENT = 'PE'
EVENT_TYPE = (
    (GC_EVENT, 'Golfcourse Event'),
    (PLAYER_EVENT, 'Player Event')
)

MY_EVENT_SCORE = 'myEvent'
LEADERBOARD_SCORE = 'leaderboard'
SCORE_TYPE = (
    (MY_EVENT_SCORE, 'My Event'),
    (LEADERBOARD_SCORE, 'Leaderboard')
)

SCRAMBLE = 'scramble'

RULE = (
    (SCRAMBLE, 'scramble'),
    (NORMAL, 'normal')
)

MORNING = 'M'
AFTERNOON = 'A'
EVENING = 'E'
PARTS_OF_DAY = (
    (MORNING, 'Morning'),
    (AFTERNOON, 'Afternoon'),
    (EVENING, 'Evening')
)

PAY_NOW = 'F'
PAY_LATER = 'N'
ALLOW_BOTH = 'A'
PAYMENT_DISCOUNT = (
    (PAY_NOW, 'pay now'),
    (PAY_LATER, 'pay later'),
    (ALLOW_BOTH, 'allow both method')
)

class GolfCourse(models.Model):
    """  Is a business entity which has Staff & Golf Courses
    """
    name = models.TextField(max_length=50, db_index=True)
    address = models.TextField(max_length=70)
    city = models.ForeignKey(City, related_name='golfcourse', blank=True, null=True)
    district = models.ForeignKey(District, related_name='golfcourse', blank=True, null=True)
    country = models.ForeignKey(Country, related_name='golfcourse', blank=True, null=True)
    description = models.TextField(max_length=100000, blank=True, null=True)
    description_en = models.TextField(max_length=100000, blank=True, null=True)
    picture = models.ImageField(upload_to='/Images/GolfCourse', blank=True)
    logo = models.CharField(max_length=200, blank=True, null=True)
    website = models.TextField(max_length=100)
    member_type = models.CharField(max_length=2, choices=MEMBER_TYPE_CHOICES, default=NONMEMBER)
    number_of_hole = models.IntegerField()
    longitude = models.FloatField()
    latitude = models.FloatField()
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default=RESORT)
    level = models.CharField(max_length=2, choices=EVENT_LEVEL, default=LEVEL1)
    phone = models.CharField(max_length=100, blank=True, null=True)
    short_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    contact_info = models.TextField(null=True, blank=True)
    owner_company = models.TextField(null=True, blank=True)

    rating = models.IntegerField(default=0, db_index=True)
    discount = models.IntegerField(default=0)
    open_hour = models.CharField(max_length=100, blank=True, null=True)
    cloth = models.TextField(blank=True, null=True)

    partner = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class SubGolfCourse(models.Model):
    """ Belong of Golfcourse the same with type of playing field or part of golfcourse
    """
    golfcourse = models.ForeignKey(GolfCourse, related_name="subgolfcourse")
    name = models.TextField(max_length=100, db_index=True)
    description = models.TextField(max_length=100000, blank=True, null=True)
    picture = models.ImageField(upload_to='Images/SubGolfCourse', blank=True, null=True)
    number_of_hole = models.IntegerField(default=0, blank=True, null=True)
    for_booking = models.BooleanField(default=True)

    def __str__(self):
        return self.golfcourse.name + "--" + self.name

    class Meta:
        ordering = ('-number_of_hole', 'name',)


class Hole(models.Model):
    subgolfcourse = models.ForeignKey(SubGolfCourse, related_name='hole')
    holeNumber = models.IntegerField()
    par = models.IntegerField()
    hdcp_index = models.IntegerField()
    picture = models.CharField(max_length=300, blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    lng = models.FloatField(blank=True, null=True)
    photo = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.subgolfcourse.golfcourse.name+ "--"+self.subgolfcourse.name + "--" + str(self.holeNumber)

    class Meta:
        ordering = ('holeNumber',)


class HoleInfo(models.Model):
    hole = models.ForeignKey(Hole, related_name='holeinfo')
    infotype = models.CharField(max_length=100)
    metersy = models.FloatField(null=True, blank=True)
    pixely = models.FloatField(null=True, blank=True)
    metersx = models.FloatField(null=True, blank=True)
    pixelx = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    x = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)


class TeeType(models.Model):
    subgolfcourse = models.ForeignKey(SubGolfCourse, related_name='teetype')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, blank=True, null=True)
    slope = models.FloatField()
    rating = models.FloatField()

    def __str__(self):
        return self.subgolfcourse.golfcourse.name+ "--"+self.subgolfcourse.name + '--' + self.name + '--' + self.color

    class Meta:
        ordering = ('color',)


class HoleTee(models.Model):
    hole = models.ForeignKey(Hole, related_name='holetee')
    tee_type = models.ForeignKey(TeeType, related_name='holetee')
    yard = models.IntegerField()

    def __str__(self):
       return self.tee_type.subgolfcourse.golfcourse.name + "--" + self.tee_type.subgolfcourse.name + "--"+self.tee_type.name + "--" + str(self.hole)


class GolfCourseSetting(models.Model):
    golfcourse = models.OneToOneField(GolfCourse, unique=True, related_name='golfcourse_settings')
    allowEditInfo = models.BooleanField(default=True)
    open_time = models.TimeField(default="6:00:00")
    close_time = models.TimeField(default="16:00:00")
    weekday_min = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    weekday_max = models.PositiveIntegerField(default=4, validators=[MaxValueValidator(4)])
    weekend_min = models.PositiveIntegerField(default=1, validators=[MinValueValidator(3)])
    weekend_max = models.PositiveIntegerField(default=4, validators=[MaxValueValidator(4)])
    weekend_price = models.DecimalField(default=0.0, max_digits=9, decimal_places=2)
    weekday_price = models.DecimalField(default=0.0, max_digits=9, decimal_places=2)

    class Meta:
        ordering = ('golfcourse',)

    def save(self, *args, **kwargs):
        super(GolfCourseSetting, self).save(*args, **kwargs)


def create_gc_setting(sender, instance, created, **kwargs):
    if created:
        GolfCourseSetting.objects.create(golfcourse=instance)


post_save.connect(create_gc_setting, sender=GolfCourse)


class Services(models.Model):
    """ List default service of all course
    """
    name = models.TextField(max_length=50, blank=True)
    description = models.TextField(max_length=100000, null=True)


class GolfCourseServices(models.Model):
    """ Service of 1 GolfCourse
    """
    golfcourse = models.ForeignKey(GolfCourse)
    services = models.ForeignKey(Services, related_name='services')
    provide = models.BooleanField(default=True)


class ClubSets(models.Model):
    """ List default clubset of all course
    """
    name = models.TextField(max_length=100)
    price = models.DecimalField(max_digits=9, decimal_places=2)


class GolfCourseClubSets(models.Model):
    """ Clubset of 1 GolfCourse
    """
    golfcourse = models.ForeignKey(GolfCourse)
    clubset = models.ForeignKey(ClubSets)
    price = models.DecimalField(max_digits=9, decimal_places=2)


# class Buggy(models.Model):
#    """ List default buggy of all course
#    """
#    type = models.PositiveIntegerField()
#    price = models.DecimalField(max_digits=9, decimal_places=2)

class GolfCourseBuggy(models.Model):
    """ Buggy of 1 GolfCourse
    """
    BUGGY_2_SEAT = 1
    BUGGY_4_SEAT = 2
    BUGGY_TYPE = (
        (BUGGY_2_SEAT, "Buggy 2 seat"),
        (BUGGY_4_SEAT, "Buggy 4 seat")
    )
    golfcourse = models.ForeignKey(GolfCourse, related_name='buggy_golfcourse')
    buggy = models.PositiveIntegerField(choices=BUGGY_TYPE, default=BUGGY_2_SEAT)
    from_date = models.DateField(blank=True, null=True, db_index=True, default=datetime.datetime.today().date())
    to_date = models.DateField(blank=True, null=True, default=datetime.datetime.today().date())
    price_9 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_18 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_27 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_36 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_standard_9 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_standard_18 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_standard_27 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_standard_36 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)


class GolfCourseCaddy(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='caddy_goldcourse')
    name = models.TextField(max_length=100)
    number = models.PositiveIntegerField(default=0)
    shift = models.IntegerField(default=1)
    price_9 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_18 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_27 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_36 = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('id',)


class GolfCourseStaff(models.Model):
    golfcourse = models.ForeignKey(GolfCourse)
    user = models.ForeignKey(User, related_name='golfstaff')
    role = models.CharField(max_length=2, choices=STAFF_TYPE_CHOICES, default=STAFF)
    description = models.TextField(max_length=999999, null=True)

    def __str__(self):
        return str(self.user.username)


class GolfCourseMember(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='member')
    user = models.ForeignKey(User, related_name='gc_member')
    role = models.CharField(max_length=10)
    expire_date = models.DateField(blank=True, null=True)


class GolfCourseEvent(models.Model):
    user = models.ForeignKey(User, related_name='event_creator', blank=True, null=True)
    date_created = models.DateTimeField(null=True, blank=True, editable=False)
    golfcourse = models.ForeignKey(GolfCourse, related_name='gc_event')
    name = models.TextField(db_index=True, blank=True, null=True, max_length=500)

    date_start = models.DateField(blank=True, null=True, db_index=True)
    date_end = models.DateField(blank=True, null=True)
    time = models.TimeField(blank=True, null=True)
    pod = models.CharField(choices=PARTS_OF_DAY, max_length=2, blank=True, null=True)

    event_level = models.CharField(max_length=2, choices=EVENT_LEVEL, default=LEVEL1, blank=True, null=True)
    calculation = models.CharField(max_length=20, choices=CALCULATION, default=NET)
    pass_code = models.CharField(max_length=100, blank=True, null=True)
    event_type = models.CharField(max_length=2, choices=EVENT_TYPE, default=PLAYER_EVENT)
    tee_type = models.ForeignKey(TeeType, blank=True, null=True)
    rule = models.CharField(max_length=20, choices=RULE, default=NORMAL)
    score_type = models.CharField(max_length=20, choices=SCORE_TYPE, default=MY_EVENT_SCORE)
    # Info for advertisement
    description = models.TextField(max_length=999999999, null=True, blank=True)
    description_en = models.TextField(max_length=999999999, null=True, blank=True)

    is_advertise = models.BooleanField(default=False)
    is_publish = models.BooleanField(default=False, db_index=True)
    has_result = models.BooleanField(default=False)

    from_hdcp = models.PositiveIntegerField(blank=True, null=True)
    to_hdcp = models.PositiveIntegerField(blank=True, null=True)

    banner = models.CharField(max_length=1000, blank=True, null=True)
    detail_banner = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=1000, blank=True, null=True)
    contact_email = models.CharField(max_length=500, blank=True, null=True)
    contact_phone = models.CharField(max_length=100, blank=True, null=True)
    result_url = models.CharField(max_length=500, blank=True, null=True)
    slug_url = models.CharField(max_length=100, blank=True, null=True)
    discount = models.FloatField(blank=True, null=True)
    price_range = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)

    allow_stay = models.BooleanField(default=False)

    # payment_discount = models.CharField(max_length=20, choices=PAYMENT_DISCOUNT, default=ALLOW_BOTH)
    # payment_discount_value = models.FloatField(blank=True, null=True)

    payment_discount_value_now = models.FloatField(blank=True, null=True)
    payment_discount_value_later = models.FloatField(blank=True, null=True)
    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.date_created = datetime.datetime.today()
        return super(GolfCourseEvent, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        # unique_together = ('name', 'golfcourse', 'date_start', 'event_type', 'user')
        ordering = ('-id',)


def update_event_location(sender, instance, created, **kwargs):
    if created and not instance.location:
        instance.location = instance.golfcourse.name
        instance.save()


def delete_related_object(sender, instance, **kwargs):
    from core.notice.models import Notice
    url = "http://{0}:{1}/myapi/delete-room/".format(XMPP_HOST, XMPP_PORT)
    data = urlencode({'event_id': [instance.id]})
    Request(url, data)
    gc_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
    Like.objects.filter(object_id=instance.id, content_type=gc_ctype).delete()
    Notice.objects.filter(object_id=instance.id, content_type=gc_ctype).delete()
    UserActivity.objects.filter(object_id=instance.id, content_type=gc_ctype).delete()


def update_data(sender, instance, **kwargs):
    if not instance.date_end:
        instance.date_end = instance.date_start
    if not instance.name:
        instance.name = instance.golfcourse.name


def push_owner_to_subcribe(sender, instance, created, **kwargs):
    if created:
        ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        UserSubcribe.objects.create(content_type=ctype, object_id=instance.id, user=[instance.user_id])


post_save.connect(push_owner_to_subcribe, sender=GolfCourseEvent)

pre_save.connect(update_data, sender=GolfCourseEvent)
post_save.connect(update_event_location, sender=GolfCourseEvent)
pre_delete.connect(delete_related_object, sender=GolfCourseEvent)

class GolfCourseEventHotel(models.Model):
    from core.playstay.models import Hotel
    event = models.ForeignKey(GolfCourseEvent, null=True, blank=True, related_name='event_hotel_info')
    hotel = models.ForeignKey(Hotel, related_name='event_hotel_info')
    checkin = models.DateField()
    checkout = models.DateField()
    def __str__(self):
        return self.event.name+ '--'+self.hotel.name

class GolfCourseEventAdvertise(models.Model):
    event = models.OneToOneField(GolfCourseEvent, null=True, blank=True, related_name='advertise_info')
    more_info = models.TextField(null=True, blank=True)
    more_info_en = models.TextField(null=True, blank=True)
    about = models.TextField(blank=True, null=True)
    about_en = models.TextField(blank=True, null=True)

    detail_banner = models.TextField(blank=True, null=True)
    sponsor_html = models.TextField(blank=True, null=True)
    schedule_html = models.TextField(blank=True, null=True)
    description_html = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.event.name


class GolfCourseEventMoreInfo(models.Model):
    event = models.ForeignKey(GolfCourseEvent, null=True, blank=True, related_name='event_more_info')
    icon = models.CharField(max_length=255, blank=True, null=True)
    info = models.CharField(max_length=255)
    def __str__(self):
        return self.event.name

class GolfCourseEventPriceInfo(models.Model):
    event = models.ForeignKey(GolfCourseEvent, null=True, blank=True, related_name='event_price_info')
    description = models.CharField(max_length=255, null=True, blank=True)
    info = models.CharField(max_length=255, null=True, blank=True)
    info_en = models.CharField(max_length=255, null=True, blank=True)
    display = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(default=0.0, max_digits=9, decimal_places=2)

    def __str__(self):
        return self.event.name + '--' + self.description

class GolfCourseEventSchedule(models.Model):
    event = models.ForeignKey(GolfCourseEvent, null=True, blank=True, related_name='event_schedule')
    date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('date',)

    def __str__(self):
        return self.event.name + "--" + self.title

class GolfCourseEventBanner(models.Model):
    event = models.ForeignKey(GolfCourseEvent, null=True, blank=True, related_name='event_banner')
    url = models.CharField(max_length=255)

    def __str__(self):
        return self.event.name

class GroupOfEvent(models.Model):
    event = models.ForeignKey(GolfCourseEvent, related_name='group_event', blank=True, null=True)
    from_index = models.FloatField()
    to_index = models.FloatField()
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('event', 'name',)
        ordering = ('from_index',)


class Flight(models.Model):
    event = models.ForeignKey(GolfCourseEvent, blank=True, null=True, related_name='flight')
    name = models.CharField(max_length=1000, blank=True, null=True)
    date_created = models.DateField(editable=False, blank=True, null=True)

    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.date_created = datetime.datetime.today()
        return super(Flight, self).save(*args, **kwargs)


def set_flight_name(sender, instance, created, **kwargs):
    if not instance.name:
        if instance.event:
            name = instance.event.name + '- Flight ' + str(instance.event.flight.count())
        else:
            name = 'Flight  ' + str(instance.id)
        instance.name = name
        instance.save()


post_save.connect(set_flight_name, sender=Flight)


class BonusParRule(models.Model):
    event = models.ForeignKey(GolfCourseEvent, related_name='bonus_par', blank=True, null=True)
    hole = models.ForeignKey(Hole)
    par = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ('hole',)


class EventPrize(models.Model):
    event = models.ForeignKey(GolfCourseEvent)
    player_name = models.CharField(blank=True, null=True, max_length=1000)
    prize_name = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)


class EventBlock(models.Model):
    user = models.ForeignKey(User)
    event = models.ForeignKey(GolfCourseEvent, related_name='event_block')
    date = models.DateField()
    reason = models.CharField(max_length=1000, blank=True, null=True)


class GolfCourseBookingSetting(models.Model):
    golfcourse = models.OneToOneField(GolfCourse, related_name='booking_setting', blank=True, null=True)
    cancel_hour = models.IntegerField(default=0)
    policy = models.TextField(null=True)
    policy_en = models.TextField(null=True)
    request_policy = models.TextField(null=True)
    request_policy_en = models.TextField(null=True)

    def __str__(self):
        return self.golfcourse.name


class GolfCourseReview(models.Model):
    golfcourse = models.ForeignKey(GolfCourse)
    user = models.ForeignKey(User, related_name='golfcourse_review')
    title = models.CharField(max_length=600, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    rating = models.IntegerField(default=0)

    date_created = models.DateField(editable=False, blank=True, null=True)

    class Meta:
        ordering = ('-date_created',)

    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.date_created = datetime.datetime.today()
        return super(GolfCourseReview, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.user.username)


def calc_rating_save(sender, instance, **kwargs):
    rating_avg = GolfCourseReview.objects.filter(golfcourse=instance.golfcourse).aggregate(Avg('rating'))[
        'rating__avg']
    if not rating_avg:
        rating_avg = 0
    instance.golfcourse.rating = round(rating_avg)
    instance.golfcourse.save()


def calc_rating_delete(sender, instance, **kwargs):
    rating_avg = \
    GolfCourseReview.objects.filter(golfcourse=instance.golfcourse).exclude(id=instance.id).aggregate(Avg('rating'))[
        'rating__avg']
    if not rating_avg:
        rating_avg = 0
    instance.golfcourse.rating = round(rating_avg)
    instance.golfcourse.save()


def log_review_activity(instance, **kwargs):
    ctype = ContentType.objects.get_for_model(GolfCourseReview)
    log_activity(instance.user.id, 'review_golfcourse', instance.id, ctype.id)


post_save.connect(calc_rating_save, sender=GolfCourseReview)
post_save.connect(log_review_activity, sender=GolfCourseReview)
pre_delete.connect(calc_rating_delete, sender=GolfCourseReview)
