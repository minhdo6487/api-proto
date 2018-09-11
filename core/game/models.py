import datetime

from api.noticeMana.tasks import send_notification
from core.notice.models import Notice
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_delete

from api.userMana.tasks import log_activity
from core.customer.models import Customer
from core.golfcourse.models import GolfCourse, Hole, TeeType, GolfCourseEvent, GroupOfEvent, Flight
from core.realtime.models import UserSubcribe
from core.user.models import UserActivity
from utils.rest.handicap import handicap36, normal_handicap, course_handicap, adjusted_gross_scores, \
    handicap_differential, handicap_index, \
    Callaway, StableFord, Peoria
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from GolfConnect.settings import XMPP_HOST, XMPP_PORT, NOTIFY_JOIN_LEFT_EVENT
import json

ACCEPT = 'A'
CANCEL = 'C'
PENDING = 'P'
HOST = 'H'
TYPE_CHOICES = (
    (ACCEPT, 'Accept'),
    (CANCEL, 'Cancel'),
    (PENDING, 'Pending'),
    (HOST, 'Host')
)


class EventMember(models.Model):
    user = models.ForeignKey(User, blank=True, null=True, related_name='event_member')
    customer = models.ForeignKey(Customer, blank=True, null=True, related_name='event_member')
    event = models.ForeignKey(GolfCourseEvent, blank=True, null=True, related_name='event_member')
    group = models.ForeignKey(GroupOfEvent, blank=True, null=True, related_name='event_member')
    memberID = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    clubID = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    handicap = models.FloatField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_join = models.BooleanField(default=False)
    status = models.CharField(max_length=2, choices=TYPE_CHOICES, default=PENDING)  # INVITE STATUS
    rank = models.IntegerField(blank=True, null=True)
    gender = models.BooleanField(default=True)

    def __str__(self):
        if self.user:
            return self.user.username
        else:
            return self.customer.name

    class Meta:
        unique_together = ('event', 'memberID', 'clubID', 'user', 'customer')
        ordering = ('-id',)


def left_event_member(sender, instance, **kwargs):
    try:
        if instance.user_id and NOTIFY_JOIN_LEFT_EVENT == 1:       
            url = "http://{0}:{1}/myapi/notify-room/".format(XMPP_HOST, XMPP_PORT)
            data = {'event_id': str(instance.event.id), 'message':'{} declined to join this event'.format(instance.user.user_profile.display_name or instance.user.username)}
            req = Request(url, json.dumps(data).encode('utf8'))
        
            response = urlopen(req)
    except:
        pass

pre_delete.connect(left_event_member, sender=EventMember)
# Connect create profile function to post_save signal of MemberEvent model
# post_save.connect(log_join_event, sender=EventMember)
def create_owner_in_event_member(sender, instance, created, **kwargs):
    if created and instance.event_type == 'PE':
        EventMember.objects.create(user=instance.user, event=instance, status='H')


def push_invited_player_to_subcribe(sender, instance, created, **kwargs):
    if created and instance.user_id and NOTIFY_JOIN_LEFT_EVENT == 1:
        ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        try:
            user_subcribe = UserSubcribe.objects.get(content_type=ctype, object_id=instance.event_id)
            subcribe_list = eval(user_subcribe.user)
            if instance.user_id not in subcribe_list:
                subcribe_list.append(instance.user_id)
                user_subcribe.user = subcribe_list
                user_subcribe.save(update_fields=['user'])
        except Exception:
            pass
    
    if instance.status == 'A' and instance.user_id:
        ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        user_activity = UserActivity.objects.filter(verb='join_event', user_id=instance.user_id, object_id=instance.event.id,
                                           content_type=ctype).first()
        if not user_activity:
            UserActivity.objects.create(verb='join_event', user_id=instance.user_id, object_id=instance.event.id,
                                               content_type=ctype)
            if NOTIFY_JOIN_LEFT_EVENT == 1:
                url = "http://{0}:{1}/myapi/notify-room/".format(XMPP_HOST, XMPP_PORT)
                data = {'event_id': str(instance.event.id), 'message':'{} joined this event'.format(instance.user.user_profile.display_name)}
                print ('push notification', url,json.dumps(data).encode('utf8') )
                req = Request(url, json.dumps(data).encode('utf8'))
                try:
                    response = urlopen(req)
                except:
                    pass


post_save.connect(push_invited_player_to_subcribe, sender=EventMember)
post_save.connect(create_owner_in_event_member, sender=GolfCourseEvent)


class Game(models.Model):
    golfcourse = models.ForeignKey(GolfCourse, related_name='game')
    date_create = models.DateTimeField(blank=True, null=True)
    date_play = models.DateField(db_index=True)
    time_play = models.TimeField(null=True, blank=True)
    recorder = models.ForeignKey(User, null=True, blank=True, related_name='game_recorder')
    bag_number = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=False)
    score_card = models.TextField(max_length=300, null=True, blank=True)
    event_member = models.ForeignKey(EventMember, blank=True, null=True, related_name='game')
    is_finish = models.BooleanField(default=False)
    is_quit = models.BooleanField(default=False)
    # score calculation
    handicap = models.FloatField(null=True, blank=True, default=0)
    handicap_36 = models.FloatField(null=True, blank=True, default=0)
    hdc_36 = models.FloatField(null=True, blank=True)  # system 36
    hdc_us = models.FloatField(null=True, blank=True)  # usga
    hdcp = models.FloatField(null=True, blank=True)  # normal
    hdc_callaway = models.FloatField(null=True, blank=True)  # callaway
    hdc_stable_ford = models.FloatField(null=True, blank=True)  # stable ford
    hdc_peoria = models.FloatField(null=True, blank=True)  # peoria
    hdc_net = models.FloatField(null=True, blank=True)  # gross - handicap
    gross_score = models.PositiveIntegerField(default=0)
    adj = models.PositiveIntegerField(null=True, blank=True)

    # map player in a group
    group_link = models.CharField(max_length=40, null=True, blank=True)

    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    related_object = generic.GenericForeignKey('content_type', 'object_id')
    reservation_code = models.CharField(max_length=100, blank=True, null=True)

    # def __str__(self):
    #     return self.golfcourse, self.event_member, self.active, self.is_finish

    def save(self, *args, **kwargs):
        """ On save, update timestamps
        """
        if not self.id:
            self.date_create = datetime.datetime.now()
        return super(Game, self).save(*args, **kwargs)

    def calculate_handicap(self, hdcus=False, callaway=False, stable_ford=False, peoria=False, system36=False,
                           normal=False, hdc_net=False):
        handicap = self.handicap
        scores = self.score.all().only('tee_type')[:1]
        strokes = list(Score.objects.filter(game_id=self.id).values_list('stroke', flat=True))
        # strokes = []

        # for score in scores:
        #     strokes.append(score.stroke)
        #     pars.append(score.hole.par)

        tee_type = scores[0].tee_type
        pars = list(Hole.objects.filter(subgolfcourse_id=tee_type.subgolfcourse_id).values_list('par', flat=True))
        slope_rating = tee_type.slope
        course_rating = tee_type.rating
        gross = sum(strokes)
        user = self.event_member.user
        if hdcus and self.score.count() == 18:
            hdc_us = 40
            if handicap:
                hdc_us = handicap
            elif user and user.user_profile.handicap_us and user.user_profile.handicap_us != 'N/A':
                hdc_us = float(user.user_profile.handicap_us)
            course_hdc = course_handicap(hdc_us, slope_rating)
            self.adj, adjust_stroke = adjusted_gross_scores(strokes, course_hdc, pars)
            self.hdc_us = handicap_differential(self.adj, hdc_us, pars, course_rating,
                                                slope_rating)
        if not self.handicap:
            self.handicap = 0
        # Compute 'callaway'
        if callaway:
            c = Callaway()
            self.hdc_callaway = c.calculate(strokes, pars)

        # Compute 'stable_ford'
        if stable_ford:
            s = StableFord()
            self.hdc_stable_ford = s.calculate(strokes, pars)

        # Compute 'peoria'
        if peoria:
            if self.event_member.event and self.event_member.event.bonus_par.exists():
                p = Peoria()
                bonus_pars = self.event.bonus_par.all()
                special = []
                i = 0
                for b in bonus_pars:
                    if b.par == 1:
                        special.append(i)
                    i += 1
                self.hdc_peoria = p.calculate(strokes, pars, special)

        # Compute 'system36'
        if system36:
            hdc_36 = handicap36(strokes, pars)
            self.handicap_36 = hdc_36
            self.hdc_36 = gross - hdc_36

        # Compute normalgroup_link
        if normal:
            hdcp = normal_handicap(strokes, pars)
            if handicap:
                hdcp = hdcp - handicap
            self.hdcp = hdcp

        # Compute hdc net

        if hdc_net:
            self.hdc_net = gross - self.handicap
        # Compute gross
        self.gross_score = gross

        # Save object
        self.save(
            update_fields=['handicap', 'handicap_36', 'hdc_36', 'hdc_us', 'hdcp', 'hdc_callaway', 'hdc_stable_ford',
                           'hdc_stable_ford', 'hdc_peoria', 'hdc_net', 'gross_score', 'adj'])

    def update_hdcp_index(self):
        user = self.event_member.user
        if not user or self.active is False:
            return
        members = EventMember.objects.filter(user=user)
        games = Game.objects.filter(event_member__in=members, is_finish=True, active=True).order_by('-date_play')[:20]
        if len(games) >= 5:
            handicap_differentials = []
            for game in games:
                strokes = list(Score.objects.filter(game_id=game.id).values_list('stroke', flat=True))
                valid = True
                count = 1
                for stroke in strokes:
                    count += 1
                    if stroke == 0:
                        valid = False
                        break
                if not valid:
                    continue
                if game.score.count() != 18:
                    continue
                if game.hdc_us and game.score.count() == 18:
                    handicap_differentials.append(game.hdc_us)
            handicap_differentials.sort()
            if not len(handicap_differentials) >= 5:
                user.user_profile.handicap_us = 'N/A'
                user.user_profile.save()
                return
            if handicap_differentials:
                hdcp_index = handicap_index(handicap_differentials)
                user.user_profile.handicap_us = hdcp_index
                user.user_profile.save()
        else:
            user.user_profile.handicap_us = 'N/A'
            user.user_profile.save()
            return

    def calculate_handicap_v2(self, first_part, hdcus=False, callaway=False, stable_ford=False, peoria=False, system36=False,
                           normal=False, hdc_net=False):
        handicap = self.handicap
        scores = self.score.all().only('tee_type')[:1]
        strokes = list(Score.objects.filter(game_id=self.id).values_list('stroke', flat=True).order_by('hole_id'))

        # for score in scores:
        #     strokes.append(score.stroke)
        #     pars.append(score.hole.par)
        """
        first_part
            - game_id for first time
        """
        tee_type = scores[0].tee_type
        pars = list(Hole.objects.filter(subgolfcourse_id=tee_type.subgolfcourse_id).values_list('par', flat=True))

        if first_part != "":
            strokes_firstgame = list(Score.objects.filter(game_id=int(first_part)).values_list('stroke', flat=True))
            teetype_firstgame = list(Score.objects.filter(game_id=int(first_part)).values_list('tee_type_id', flat=True))[0]
            hole_firstgame = Score.objects.filter(game_id=int(first_part)).values('hole_id')
            par_firstgame = list(Hole.objects.filter(pk__in = hole_firstgame).values_list("par", flat=True))
            pars = par_firstgame + pars
        elif len(Score.objects.filter(game_id=self.id).values('hole_id')) == 18:
            hole_game_cont = Score.objects.filter(game_id= self.id).values('hole_id')[9:]
            par_game_cont = list(Hole.objects.filter(pk__in=hole_game_cont).values_list("par", flat=True))
            pars = pars + par_game_cont
        else:
            par_firstgame = []

        slope_rating = tee_type.slope
        course_rating = tee_type.rating
        gross = sum(strokes)
        user = self.event_member.user
        if hdcus and self.score.count() == 18:
            hdc_us = 40
            if handicap:
                hdc_us = handicap
            elif user and user.user_profile.handicap_us and user.user_profile.handicap_us != 'N/A':
                hdc_us = float(user.user_profile.handicap_us)
            course_hdc = course_handicap(hdc_us, slope_rating)
            self.adj, adjust_stroke = adjusted_gross_scores(strokes, course_hdc, pars )
            self.hdc_us = handicap_differential(self.adj, hdc_us, pars, course_rating,
                                                slope_rating)
        if not self.handicap:
            self.handicap = 0
        # Compute 'callaway'
        if callaway:
            c = Callaway()
            self.hdc_callaway = c.calculate(strokes, pars)

        # Compute 'stable_ford'
        if stable_ford:
            s = StableFord()
            self.hdc_stable_ford = s.calculate(strokes, pars)

        # Compute 'peoria'
        if peoria:
            if self.event_member.event and self.event_member.event.bonus_par.exists():
                p = Peoria()
                bonus_pars = self.event.bonus_par.all()
                special = []
                i = 0
                for b in bonus_pars:
                    if b.par == 1:
                        special.append(i)
                    i += 1
                self.hdc_peoria = p.calculate(strokes, pars, special)

        # Compute 'system36'
        if system36:
            hdc_36 = handicap36(strokes, pars)
            self.handicap_36 = hdc_36
            self.hdc_36 = gross - hdc_36

        # Compute normalgroup_link
        if normal:
            hdcp = normal_handicap(strokes, pars)
            if handicap:
                hdcp = hdcp - handicap
            self.hdcp = hdcp

        # Compute hdc net

        if hdc_net:
            self.hdc_net = gross - self.handicap
        # Compute gross
        self.gross_score = gross

        # Save object
        self.save(
            update_fields=['handicap', 'handicap_36', 'hdc_36', 'hdc_us', 'hdcp', 'hdc_callaway', 'hdc_stable_ford',
                           'hdc_stable_ford', 'hdc_peoria', 'hdc_net', 'gross_score', 'adj'])


def log_scoring_activity(sender, instance, created, **kwargs):
    if instance.event_member.user:
        ctype = ContentType.objects.get_for_model(Game)
        public = instance.is_finish & instance.active
        log_activity(instance.event_member.user_id, 'create_game', instance.id, ctype.id, public)


def send_notif_to_player(sender, instance, created, **kwargs):
    if instance.event_member.user and \
                    instance.event_member.user != instance.recorder and \
                    instance.is_finish and \
                    not instance.active:
        user = instance.event_member.user
        name = instance.recorder.user_profile.display_name
        golfcourse_name = instance.golfcourse.name
        date = instance.date_create.strftime('%d-%m-%Y')
        detail_en = '{name} has recorded your game at {golfcourse_name} on {date}'.format(name=name,
                                                                                          golfcourse_name=golfcourse_name,
                                                                                          date=date)
        detail = '{name} đã ghi điểm cho bạn ở sân {golfcourse_name} vào ngày {date}'.format(name=name,
                                                                                             golfcourse_name=golfcourse_name,
                                                                                             date=date)

        ctype = ContentType.objects.get_for_model(Game)
        _, created = Notice.objects.get_or_create(content_type=ctype,
                                     object_id=instance.id,
                                     to_user=user,
                                     notice_type='G',
                                     from_user=instance.recorder,
                                     detail_en=detail_en,
                                     detail=detail,
                                     send_email=False)
        if created:
            translate_message = {
                'alert_vi': detail,
                'alert_en': detail_en
            }
            send_notification.delay([user.id], detail_en, translate_message)


def delete_game_related_object(sender, instance, **kwargs):
    from core.notice.models import Notice
    gc_ctype = ContentType.objects.get_for_model(Game)
    Notice.objects.filter(object_id=instance.id, content_type=gc_ctype).delete()

post_save.connect(log_scoring_activity, sender=Game)
post_save.connect(send_notif_to_player, sender=Game)
pre_delete.connect(delete_game_related_object, sender=Game)


class GameFlight(models.Model):
    flight = models.ForeignKey(Flight, related_name='game_flight')
    member = models.ForeignKey(EventMember, related_name='game_flight')
    game = models.OneToOneField(Game, related_name='game_flight')


class Score(models.Model):
    game = models.ForeignKey(Game, related_name='score', null=True, blank=True)
    hole = models.ForeignKey(Hole, related_name='score')
    tee_type = models.ForeignKey(TeeType)
    stroke = models.IntegerField()

    # optional
    ob = models.PositiveIntegerField(null=True, blank=True)
    putt = models.PositiveIntegerField(default=0, null=True, blank=True)
    chip = models.PositiveIntegerField(null=True, blank=True)
    bunker = models.PositiveIntegerField(null=True, blank=True)
    water = models.PositiveIntegerField(null=True, blank=True)
    fairway = models.BooleanField(default=False)
    on_green = models.BooleanField(default=False)

    class Meta:
        ordering = ('hole__holeNumber',)
        unique_together = ('game', 'hole', 'tee_type')
