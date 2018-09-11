import calendar
import json

import collections

from api.noticeMana.tasks import get_from_xmpp
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from rest_framework import serializers

from api.commentMana.serializers import CommentSerializer
from api.inviteMana.serializers import InvitedPeopleSerialier
from core.comment.models import Comment
from core.user.models import UserProfile
from core.game.models import EventMember, HOST
from core.golfcourse.models import GolfCourseEvent, GroupOfEvent, BonusParRule, SubGolfCourse, EventPrize, \
    GolfCourse, GolfCourseEventSchedule, GolfCourseEventMoreInfo, GolfCourseEventBanner, GolfCourseEventPriceInfo, GolfCourseEventHotel
from core.like.models import Like, View
import datetime
from django.utils.timezone import utc, pytz

EVENT_CTYPE = ContentType.objects.get_for_model(GolfCourseEvent)
TODAY = datetime.date.today()


class GroupOfEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupOfEvent
        fields = ('id', 'event', 'from_index', 'to_index', 'name')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(GroupOfEventSerializer, self).to_native(obj)
            is_delete = True
            if EventMember.objects.filter(group=obj).exists():
                is_delete = False
            serializers.update({
                'delete': is_delete
            })
            return serializers


class BonusParSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusParRule
        fields = ('event', 'hole', 'par')


class GolfCourseEventSerializer(serializers.ModelSerializer):
    group = GroupOfEventSerializer(many=True, required=False, source='group_event', allow_add_remove=True)
    bonus_par = BonusParSerializer(many=True, required=False)

    class Meta:
        model = GolfCourseEvent
        fields = ('id', 'user', 'date_created', 'golfcourse', 'name', 'date_start', 'date_end', 'rule', 'time',
                  'description', 'calculation', 'group', 'bonus_par', 'event_type', 'pass_code', 'tee_type',
                  'is_publish', 'score_type', 'pod', 'payment_discount_value_now', 'payment_discount_value_later')

    @staticmethod
    def validate_tee_type(attrs, source):
        if attrs[source]:
            subgolfcourse = SubGolfCourse.objects.filter(golfcourse=attrs['golfcourse'])[0]
            if attrs[source].subgolfcourse != subgolfcourse:
                raise serializers.ValidationError('tee_type does not exist')
        return attrs

    def to_native(self, obj):
        if obj:
            serializers = super(GolfCourseEventSerializer, self).to_native(obj)
            if obj.tee_type:
                serializers.update({'tee_color': obj.tee_type.color,
                                    'subgolfcourse': obj.tee_type.subgolfcourse.id,
                                    'subgolfcourse_name': obj.tee_type.subgolfcourse.name})
            if obj.pass_code:
                serializers.update({'has_pass': True})
            else:
                serializers.update({'has_pass': False})
            user_profile = UserProfile.objects.only('display_name').get(user_id=obj.user_id)
            golfcourse = GolfCourse.objects.only('name').get(id=obj.golfcourse_id)
            serializers.update({'display_name': user_profile.display_name,
                                'golfcourse_name': golfcourse.name})
            del serializers['pass_code']

            ###
            serializers_add = AdvertiseEventSerializer(obj)

            func_time = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").replace(tzinfo=utc).isoformat()

            if serializers_add.data.get('contact_phone'):
                serializers.update({"register_info": user_profile.display_name + " -- " + serializers_add.data.get('contact_phone')})
            else:
                serializers.update({"register_info": user_profile.display_name})

            serializers.update({
                "event_price_info" : serializers_add.data.get('event_price_info'),
                "contact_email": serializers_add.data.get('contact_email'),
                "contact_phone": serializers_add.data.get('contact_phone'),
                "date_start": func_time(str(serializers.get('date_start'))),
                "date_end": func_time(str(serializers.get('date_end'))),
                "view_count": serializers_add.data.get('view_count'),
                "join_count": serializers_add.data.get('join_count'),
                "like_count": serializers_add.data.get('like_count')
            })

            return serializers

class GolfCourseEventPriceInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventPriceInfo
        ordering = ('id',)

class GolfCourseEventHotelInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventHotel
        ordering = ('id',)
    def to_native(self, obj):
        if obj:
            serializers = super(GolfCourseEventHotelInfoSerializer, self).to_native(obj)
            if obj.hotel:
                serializers.update({'hotel_name': obj.hotel.name,
                                    'hotel_address': obj.hotel.address})
            return serializers

class PublicGolfCourseEventSerializer(serializers.ModelSerializer):
    event_price_info = GolfCourseEventPriceInfoSerializer(many=True, source='event_price_info', allow_add_remove=True)
    hotel_info = GolfCourseEventHotelInfoSerializer(many=True, source='event_hotel_info', allow_add_remove=True)
    class Meta:
        model = GolfCourseEvent
        fields = ('id', 'golfcourse', 'name', 'date_start', 'date_end',
                  'description', 'rule', 'user', 'score_type', 'event_type', 'banner', 'price_range', 'discount',
                  'event_price_info', 'hotel_info', 'allow_stay', 'payment_discount_value_now', 'payment_discount_value_later')

    def to_native(self, obj):
        if obj:
            serializers = super(PublicGolfCourseEventSerializer, self).to_native(obj)
            time = serializers['date_start'].strftime('%d/%m')
            if serializers['date_end'] != serializers['date_start']:
                time += ' - ' + serializers['date_end'].strftime('%d/%m')
            gc = GolfCourse.objects.only('name').get(id=obj.golfcourse_id)
            join_count = EventMember.objects.filter(event=obj, customer__isnull=True).count()
            like_count = Like.objects.filter(content_type=EVENT_CTYPE, object_id=obj.id).aggregate(Sum('count'))[
                'count__sum']
            if not like_count:
                like_count = 0
            # cmt_serializer = CommentSerializer(comments)
            partners = obj.event_member.all().exclude(status=HOST).exclude(customer__isnull=False)
            partners_serializers = InvitedPeopleSerialier(partners, many=True)
            (count, uread) = get_from_xmpp('', obj.id)
            if not serializers['description']:
                serializers['description'] = None
            serializers.update({'date': time, 'golfcourse_name': gc.name,
                                'join_count': join_count,
                                'like_count': like_count,
                                'invite_people': partners_serializers.data,
                                'name': obj.user.user_profile.display_name,
                                'event_name': obj.name,
                                'email': obj.user.username,
                                'time': obj.time,
                                'pic': obj.user.user_profile.profile_picture,
                                'gender': obj.user.user_profile.gender,
                                'from_user_id': obj.user_id,
                                'date_creation': calendar.timegm(obj.date_created.timetuple()),
                                'comment_count': count})
            if obj.pass_code:
                serializers.update({'has_pass': True})
            else:
                serializers.update({'has_pass': False})

            return serializers


class GolfCourseEventScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventSchedule

    def to_native(self, obj):
        serializers = super(GolfCourseEventScheduleSerializer, self).to_native(obj)
        data = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(serializers['details'])
        serializers['details'] = data.items()
        return serializers


class GolfCourseEventMoreInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventMoreInfo

class GolfCourseEventBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventBanner


class AdvertiseEventSerializer(serializers.ModelSerializer):
    event_price_info = GolfCourseEventPriceInfoSerializer(many=True, source='event_price_info', allow_add_remove=True)
    hotel_info = GolfCourseEventHotelInfoSerializer(many=True, source='event_hotel_info', allow_add_remove=True)
    class Meta:
        model = GolfCourseEvent
        fields = ('id', 'golfcourse', 'name', 'date_start', 'date_end', 'location',
                  'description', 'banner', 'website', 'contact_email', 'contact_phone', 'result_url', 'discount',
                  'price_range','event_price_info', 'hotel_info', 'allow_stay', 'payment_discount_value_now', 'payment_discount_value_later')

    def to_native(self, obj):
        if obj:
            serializers = super(AdvertiseEventSerializer, self).to_native(obj)
            date = obj.date_start
            delta = date - TODAY
            night_no = obj.date_end - obj.date_start
            serializers.update({
                'day': int(date.strftime('%d')),
                'month': date.strftime('%b'),
                'time': date.strftime('%A , %B %d %Y'),
                'day_left': delta.days,
                'night': night_no.days})
            ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            try:
                view = View.objects.only('count').get(content_type=ctype, object_id=obj.id)
                view_count = view.count
            except Exception:
                view_count = 0
            like_count = Like.objects.filter(content_type=ctype, object_id=obj.id).aggregate(Sum('count'))['count__sum']
            if not like_count:
                like_count = 0
            join_count = EventMember.objects.filter(event=obj, customer__isnull=True).count()
            comment_count = Comment.objects.filter(content_type=EVENT_CTYPE, object_id=obj.id).count()

            serializers.update({
                'like_count': like_count,
                'view_count': view_count,
                'join_count': join_count,
                'comment_count': comment_count,
                'discount_pay_later': 5,
                'discount_pay_now': 10
            })
            return serializers


class EventPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventPrize


class RegisterEventSerializer(serializers.Serializer):
    # email = serializers.EmailField(required=False)
    # name = serializers.CharField(required=True, max_length=500)
    # phone = serializers.CharField(max_length=50)
    # handicap = serializers.FloatField(required=False)
    golfcourse = serializers.IntegerField(required=False, min_value=1)