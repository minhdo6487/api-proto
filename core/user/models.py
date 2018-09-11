import datetime, json

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete, pre_save
from urllib.request import Request, urlopen
from core.location.models import City, District, Country
from GolfConnect.settings import XMPP_HOST, XMPP_PORT, NOTIFY_JOIN_LEFT_EVENT
from v2.api.eventMana.tasks import create_event_from_user
try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

MALE = 'M'
FEMALE = 'F'
ANOTHER = 'A'
GENDER_CHOICES = (
    (MALE, 'Male'),
    (FEMALE, 'Female'),
    (ANOTHER, 'Another'))

SUNDAY = 'Sunday'
MONDAY = 'Monday'
TUESDAY = 'Tuesday'
WEDNESDAY = 'Wednesday'
THURSDAY = 'Thursday'
FRIDAY = 'Friday'
SATURDAY = 'Saturday'
DAILY_CHOICES = (
    (SUNDAY, 'Sunday'),
    (MONDAY, 'Monday'),
    (TUESDAY, 'Tuesday'),
    (WEDNESDAY, 'Wednesday'),
    (THURSDAY, 'Thursday'),
    (FRIDAY, 'Friday'),
    (SATURDAY, 'Saturday'))

MORNING = 'Morning'
AFTERNOON = 'Afternoon'
EVENING = 'Evening'
WEEKDAY = 'WeekDay'
WEEKEND = 'Weekend'
YEAR = 'year'
MONTH = 'month'
WEEK = 'week'
TIME_CHOICES = (
    (MORNING, 'Morning'),
    (AFTERNOON, 'Afternoon'),
    (YEAR, 'year'),
    (MONTH, 'month'),
    (WEEK, 'week'))

VN = 'V'
ENGLISH = 'E'
ANOTHER_L = 'A'
LAN_CHOICES = (
    (VN, 'VN'),
    (ENGLISH, 'EN'),
    (ANOTHER_L, 'Another'))

ALLOW = 'A'
DENY = 'D'
ACTION_CHOICE = (
    (ALLOW, 'Allow'),
    (DENY, 'Deny'))


FRIENDLY = 'Friendly'
WAGER = 'Wager'
TYPE_GAME = (
    (FRIENDLY, 'Friendly'),
    (WAGER, 'Wager'))

class Major(models.Model):
    """ Major
    """
    name = models.TextField()


class Degree(models.Model):
    """ Degree
    """
    name = models.TextField()


class UserProfile(models.Model):
    """ profile of user
    """
    user = models.OneToOneField(User, related_name='user_profile')
    deviceToken = models.CharField(max_length=100, blank=True, null=True)
    # GENERAL INFORMATION
    middle_name = models.TextField(max_length=20, blank=True, null=True)
    display_name = models.TextField(max_length=50, blank=True, null=True)
    first_name = models.TextField(max_length=50, blank=True, null=True)
    last_name = models.TextField(max_length=50, blank=True, null=True)
    # Date of birth
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default=MALE)
    # Current Location
    nationality = models.ForeignKey(Country, blank=True, null=True)
    city = models.ForeignKey(City, blank=True, null=True)
    district = models.ForeignKey(District, blank=True, null=True)
    address = models.TextField(max_length=30, blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    # PROFESSIONAL INFORMATION
    # Work related info
    job_title = models.TextField(max_length=140, blank=True, null=True)
    company_name = models.TextField(max_length=140, blank=True, null=True)
    # Business Area
    business_area = models.CharField(max_length=100, blank=True, null=True)

    university1 = models.TextField(max_length=140, blank=True, null=True)
    university2 = models.TextField(max_length=140, blank=True, null=True)
    # Email : base on user of django

    # TODO: change country code to a list
    mobile = models.CharField(max_length=15, blank=True, null=True)

    # GOLF INFORMATION
    handicap_36 = models.CharField(max_length=8, blank=True, null=True, default='0')
    handicap_us = models.CharField(max_length=8, blank=True, null=True, default='N/A')
    usual_golf_time = models.CharField(max_length=15, default=MORNING)
    avg_score  = models.FloatField(blank=True, null=True,default=0)
    type_golf_game = models.CharField(max_length=15, default=FRIENDLY, blank=True, null=True)
    # Year of playing
    year_experience = models.FloatField(blank=True, null=True)
    frequency_playing = models.FloatField(blank=True, null=True)
    frequency_time_playing = models.CharField(max_length=15, default=WEEKEND, blank=True, null=True)
    no_partner = models.PositiveSmallIntegerField(blank=True, null=True)

    profile_picture = models.CharField(max_length=500, blank=True, null=True)
    book_success_counter = models.IntegerField(default=0, blank=True, null=True)

    # PERSONAL INFORMATION
    interests = models.TextField(blank=True, null=True)
    personality = models.TextField(blank=True, null=True)
    fav_pros = models.TextField(blank=True, null=True)
    date_pass_change = models.DateField(blank=True, null=True)
    favor_quotation = models.TextField(max_length=99999, blank=True, null=True)

    # IS MEMBER OF GC24
    is_member = models.BooleanField(default=False)

    # VERSION OF MODEL
    version   = models.IntegerField(default=1,blank=True,null=True)

    class Meta:
        ordering = ('user',)

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_pass_change = datetime.date.today()
            self.favor_quotation = "Golf gives you an insight into human nature, your own as well as your opponent's."
        super(UserProfile, self).save(*args, **kwargs)

    def __str__(self):
        return self.user.username


# create a profile for newly created user
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if not instance.is_superuser is True:
            UserProfile.objects.create(user=instance)

def update_display_name(sender, instance, created, **kwargs):
    instance.display_name = (instance.first_name or '') + (instance.last_name or '')

# Connect create profile function to post_save signal of User model
# pre_save.connect(update_display_name, sender=UserProfile)
post_save.connect(create_user_profile, sender=User)
post_save.connect(create_event_from_user, sender=UserProfile)
class UserVersion(models.Model):
    user    = models.ForeignKey(User, related_name='userversion')
    version = models.FloatField(default=1.0)
    source  = models.CharField(max_length=50, default='ios')

class UserSetting(models.Model):
    user = models.OneToOneField(User, related_name='usersettings')
    # Display language
    language = models.CharField(max_length=1,
                                choices=LAN_CHOICES,
                                default=VN, null=False, blank=False)
    # to receive notification by email or not
    receive_email_notification = models.BooleanField(default=True)
    # public profile or not?
    public_profile = models.BooleanField(default=True)
    visible_search = models.BooleanField(default=True)
    receive_push_notification = models.BooleanField(default=True)

    class Meta:
        ordering = ('user',)

    def save(self, *args, **kwargs):
        super(UserSetting, self).save(*args, **kwargs)


# create a profile for newly created user
def create_user_setting(sender, instance, created, **kwargs):
    if created:
        nation = instance.nationality.short_name if instance.nationality else 'vn'
        lang = VN if nation.lower() == 'vn' else ENGLISH
        UserSetting.objects.create(user=instance.user, language=lang)

# Connect create setting function to post_save signal of User model
post_save.connect(create_user_setting, sender=UserProfile)


class UsualPlaying(models.Model):
    user = models.ForeignKey(User, related_name='usual_playing')
    usual_prac_day = models.CharField(max_length=15, choices=DAILY_CHOICES, default=SUNDAY)
    usual_golf_day = models.CharField(max_length=15, choices=DAILY_CHOICES, blank=True, null=True)


# create a profile for newly created user
def create_user_usual_playing(sender, instance, created, **kwargs):
    if created:
        if not instance.is_superuser is True:
            UsualPlaying.objects.create(user=instance)

# Connect create setting function to post_save signal of User model
post_save.connect(create_user_usual_playing, sender=User)


class MemberGolfCourse(models.Model):
    user = models.ForeignKey(User, related_name='member_golfcourse')
    golfcourse = models.CharField(max_length=300, blank=True, null=True)


# create a profile for newly created user
def create_member_golfcourse(sender, instance, created, **kwargs):
    if created:
        if not instance.is_superuser is True:
            MemberGolfCourse.objects.create(user=instance)

# Connect create setting function to post_save signal of User model
post_save.connect(create_member_golfcourse, sender=User)


class FavGolfCourse(models.Model):
    user = models.ForeignKey(User, related_name='fav_golfcourse')
    golfcourse = models.CharField(max_length=300, blank=True, null=True)


# create a profile for newly created user
def create_fav_golfcourse(sender, instance, created, **kwargs):
    if created:
        if not instance.is_superuser is True:
            FavGolfCourse.objects.create(user=instance)

# Connect create setting function to post_save signal of User model
post_save.connect(create_fav_golfcourse, sender=User)


class FavClubset(models.Model):
    user = models.ForeignKey(User, related_name='fav_clubset')
    clubset = models.CharField(max_length=200, blank=True, null=True)


# create a profile for newly created user
def create_fav_clubset(sender, instance, created, **kwargs):
    if created:
        if not instance.is_superuser is True:
            FavClubset.objects.create(user=instance)

# Connect create setting function to post_save signal of User model
post_save.connect(create_fav_clubset, sender=User)


class UserActivity(models.Model):
    user = models.ForeignKey(User, related_name='activities')
    verb = models.CharField(max_length=255, db_index=True)

    date_creation = models.DateTimeField(editable=False, db_index=True, default=now)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    related_object = generic.GenericForeignKey('content_type', 'object_id')

    public = models.BooleanField(default=True, db_index=True)

class UserDevice(models.Model):
    user = models.ForeignKey(User, related_name='device')
    device_id = models.CharField(max_length=255)
    push_token = models.CharField(max_length=255, blank=True, null=True)
    device_type = models.CharField(max_length=20, db_index=True)

    created_at       = models.DateTimeField(null=True, blank=True, editable=False)
    modified_at      = models.DateTimeField(null=True, blank=True)
    api_version      = models.PositiveSmallIntegerField(default=1,null=True,blank=True)
    
    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.created_at = datetime.datetime.utcnow()
        self.modified_at = datetime.datetime.utcnow()
        # self.datetime = datetime.datetime.combine(self.date, self.time)
        return super(UserDevice, self).save(*args, **kwargs)


class Invoice(models.Model):
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_code = models.CharField(max_length=100, blank=True, null=True)
    created = models.DateTimeField(null=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.created = datetime.datetime.utcnow()
        return super(Invoice, self).save(*args, **kwargs)

class UserLocation(models.Model):
    user = models.ForeignKey(User, related_name='location')
    lon = models.FloatField()
    lat = models.FloatField()
    modified_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        self.modified_at = datetime.datetime.utcnow()
        return super(UserLocation, self).save(*args, **kwargs)


class GroupChat(models.Model):
    modified_at = models.DateTimeField(null=True, blank=True)
    member_list = models.TextField(null=True,blank=True)
    group_id    = models.CharField(max_length=100, blank=True, null=True)
    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        self.modified_at = datetime.datetime.utcnow()
        return super(GroupChat, self).save(*args, **kwargs)
    def __str__(self):
        return self.group_id + '--'+self.member_list
class UserGroupChat(models.Model):
    user        = models.ForeignKey(User, related_name='group_member')
    groupchat   = models.ForeignKey(GroupChat, related_name='group_member')
    date_joined = models.DateTimeField(null=True, blank=True)
    invited_by  = models.ForeignKey(User, related_name='group_invited_by', null=True, blank=True, default=None)
    def save(self, *args, **kwargs):
        if not self.id:
            self.date_joined = datetime.datetime.utcnow()
        return super(UserGroupChat, self).save(*args, **kwargs)


def create_groupchat(sender, instance, created, **kwargs):
    if created:
        GroupChat.objects.filter(pk=instance.id).update(group_id='group_'+str(instance.id))

def left_groupchat(sender, instance, **kwargs):
    if instance.user_id and NOTIFY_JOIN_LEFT_EVENT == 1:       
        url = "http://{0}:{1}/myapi/notify-room/".format(XMPP_HOST, XMPP_PORT)
        data = {'event_id': str(instance.groupchat.group_id), 'message':'{} has left and will not receive new messages in this conversation'.format(instance.user.user_profile.display_name or instance.user.username)}
        req = Request(url, json.dumps(data).encode('utf8'))
        try:
            response = urlopen(req)
        except:
            pass
def join_grouchat(sender, instance, created, **kwargs):
    if created and NOTIFY_JOIN_LEFT_EVENT == 1:       
        url = "http://{0}:{1}/myapi/notify-room/".format(XMPP_HOST, XMPP_PORT)
        if instance.invited_by == instance.user:
            # No need to notify myself
            return
        from_user = instance.invited_by.user_profile.display_name or instance.invited_by.username or 'Someone'
        to_user = instance.user.user_profile.display_name or instance.user.username
        data = {'event_id': str(instance.groupchat.group_id), 'message':'{0} added {1} to this conversation'.format(from_user,to_user)}
        req = Request(url, json.dumps(data).encode('utf8'))
        try:
            response = urlopen(req)
        except:
            pass
# Connect create profile function to post_save signal of User model
post_save.connect(create_groupchat, sender=GroupChat)
pre_delete.connect(left_groupchat, sender=UserGroupChat)
post_save.connect(join_grouchat, sender=UserGroupChat)

class UserPrivacy(models.Model):
    user = models.ForeignKey(User, related_name='privacy_owner')
    target = models.ForeignKey(User, related_name='privacy_target')
    action = models.CharField(max_length=1, choices=ACTION_CHOICE, default=DENY)

def update_privacy(sender, instance, created, **kwargs):
    from api.userMana.tasks import block_user
    block_user.delay(instance.user.id)
# Connect create profile function to post_save signal of User model
post_save.connect(update_privacy, sender=UserPrivacy)