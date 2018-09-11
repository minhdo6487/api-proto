import calendar
import math
import datetime
from core.customer.models import Customer
from core.friend.models import Friend
from core.game.models import Game
from core.golfcourse.models import GolfCourseEvent, Hole
from core.like.models import Like
from core.user.models import UserProfile, UserSetting, \
    UsualPlaying, MemberGolfCourse, FavGolfCourse, FavClubset, UserActivity, Invoice, \
    UserLocation, GroupChat, UserGroupChat, UserPrivacy
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Sum
from geopy import distance
from rest_framework import serializers
from rest_framework.pagination import PaginationSerializer
from utils.rest.code import code
from utils.rest.handicap import normal_handicap
from api.noticeMana.tasks import get_from_xmpp_forgroup
from v2.api.chatserviceMana.tasks import get_user_chat_statistic

class UsualPlayingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsualPlaying


class MemberGolfCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberGolfCourse


class FavGolfCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavGolfCourse


class FavClubsetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavClubset


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('description', 'middle_name', 'display_name', 'gender', 'dob', 'business_area',
                  'nationality', 'city', 'district', 'address', 'job_title',
                  'company_name', 'interests', 'personality', 'usual_golf_time', 'fav_pros', 'mobile', 'handicap_36',
                  'handicap_us', 'year_experience', 'frequency_time_playing',
                  'frequency_playing', 'profile_picture', 'date_pass_change', 'is_member', 'favor_quotation',
                  'type_golf_game', 'avg_score', 'location')

    @staticmethod
    def validate_display_name(attrs, source):
        display_name = attrs[source]
        if not display_name:
            raise serializers.ValidationError('Name is required')
        else:
            return attrs

    def to_native(self, obj):
        if obj is not None:
            serializers = super(ProfileSerializer, self).to_native(obj)
            # if obj.city:
            # city_name = obj.city.name
            #     serializers.update({'city_name': city_name})
            game = Game.objects.filter(event_member__user_id=obj.user_id, golfcourse__number_of_hole__gte=18,
                                       is_finish=True, active=True).aggregate(Avg('gross_score'))
            avg_stroke = 0
            if game['gross_score__avg']:
                avg_stroke = round(game['gross_score__avg'])
            serializers.update({'avg_stroke': avg_stroke})
            return serializers


class UserSerializer(serializers.ModelSerializer):
    """ serializer for user profile
    """
    user_profile = ProfileSerializer(source='user_profile')
    usual_playing = UsualPlayingSerializer(many=True, source='usual_playing', allow_add_remove=True)
    member_golfcourse = MemberGolfCourseSerializer(many=True, source='member_golfcourse', allow_add_remove=True)
    fav_golfcourse = FavGolfCourseSerializer(many=True, source='fav_golfcourse', allow_add_remove=True)
    fav_clubset = FavClubsetSerializer(many=True, source='fav_clubset', allow_add_remove=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'user_profile',
            'usual_playing', 'member_golfcourse', 'fav_golfcourse', 'fav_clubset', 'date_joined')

    @staticmethod
    def validate_email(attrs, source):
        email = attrs[source]
        if not email:
            raise serializers.ValidationError('Email is required')
        else:
            return attrs

    def to_native(self, obj):
        if obj:
            serializers = super(UserSerializer, self).to_native(obj)
            serializers['user_profile'].update({
                    'id': serializers['id'],
                    'username': serializers['username'],
                    'email': serializers['email'],
                    'first_name': serializers['first_name'],
                    'last_name': serializers['last_name'],
                    'date_joined': serializers['date_joined'],
                    'is_block': self.context.get('is_block',False)
                })
            return serializers



class UserSettingSerializer(serializers.HyperlinkedModelSerializer):
    """ serializer for user setting
    """
    language = serializers.ChoiceField(source='usersettings.language')
    receive_email_notification = serializers.BooleanField(source='usersettings.receive_email_notification')
    public_profile = serializers.BooleanField(source='usersettings.public_profile')

    class Meta:
        model = User
        fields = ('language', 'receive_email_notification', 'public_profile')

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            instance.usersettings.language = attrs.get('usersettings.language', instance.usersettings.language)
            instance.usersettings.receive_email_notification = attrs.get('usersettings.receive_email_notification',
                                                                         instance.usersettings.receive_email_notification)
            instance.usersettings.public_profile = attrs.get('usersettings.public_profile',
                                                             instance.usersettings.public_profile)
            return instance
        return UserSetting(**attrs)


class UserDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(UserDisplaySerializer, self).to_native(obj)
            display_name = obj.user_profile.display_name
            phone = obj.user_profile.mobile
            pic = obj.user_profile.profile_picture
            handicap_us = obj.user_profile.handicap_us
            description = obj.user_profile.description
            game = Game.objects.filter(event_member__user_id=obj.id, golfcourse__number_of_hole__gte=18,
                                       is_finish=True, active=True).aggregate(Avg('gross_score'))
            avg_stroke = 0
            if game['gross_score__avg']:
                avg_stroke = round(game['gross_score__avg'])
            if self.context.get('lat') and self.context.get('lon'):
                user_location = UserLocation.objects.filter(user=obj).order_by('-modified_at').first()
                friend_distance = 'N/A'
                if user_location:
                    friend_distance = round(distance.distance((user_location.lat, user_location.lon),
                                                              (self.context['lat'], self.context['lon'])).kilometers, 2)
                serializers.update({
                    'friend_distance': friend_distance
                })
            is_friend = False
            if self.context.get('user_id') and Friend.objects.filter(from_user_id=self.context['user_id'], to_user_id=obj.id).exists():
                is_friend = True
            is_block = False
            if self.context.get('user_id') and UserPrivacy.objects.filter(user_id=self.context['user_id'], target_id=obj.id, action='D').exists():
                is_block = True
            serializers.update({
                'name': display_name,
                'display_name': display_name,
                'phone_number': phone,
                'pic': pic,
                'handicap_us': handicap_us,
                'avg_stroke': avg_stroke,
                'avg_score': obj.user_profile.avg_score or 0,
                'description': description,
                'is_friend': is_friend,
                'is_block': is_block
            })
            return serializers


PASSWORD_MAX_LENGTH = User._meta.get_field('password').max_length


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=PASSWORD_MAX_LENGTH
    )
    new_password = serializers.CharField(
        max_length=PASSWORD_MAX_LENGTH
    )

    @staticmethod
    def validate_new_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if len(password) < 8:
            raise serializers.ValidationError(code['E_INVALID_PASSWORD'])
        return attrs


class UserGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('id', 'golfcourse', 'gross_score')

    def to_native(self, obj):
        if obj:
            serializers = super(UserGameSerializer, self).to_native(obj)
            pic = None
            display_name = None
            if obj.event_member.user_id:
                user_profile = UserProfile.objects.only('display_name', 'profile_picture').get(
                    user_id=obj.event_member.user_id)
                pic = user_profile.profile_picture
                display_name = user_profile.display_name
            elif obj.event_member.customer_id:
                customer = Customer.objects.get(id=obj.event_member.customer_id)
                pic = customer.avatar
                display_name = customer.name
            serializers.update({'display_name': display_name, 'pic': pic})
            return serializers


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity

    def to_native(self, obj):
        if obj:
            serializers = super(UserActivitySerializer, self).to_native(obj)
            related_data = {}
            if obj.related_object:
                if obj.verb == 'join_event':
                    related_data = {
                        'event_id': obj.related_object.id,
                        'event_name': obj.related_object.name,
                        'date_start': obj.related_object.date_start,
                        'date_end': obj.related_object.date_end,
                        'name': obj.related_object.user.user_profile.display_name,
                        'time': obj.related_object.time,
                        'pic': obj.related_object.user.user_profile.profile_picture,
                        'golfcourse_name': obj.related_object.golfcourse.name,
                        'golfcourse_id': obj.related_object.golfcourse_id,
                        'description': obj.related_object.description,
                        'event_type': obj.related_object.event_type,
                    }
                    if obj.related_object.event_type == 'GE':
                        related_data['pic'] = obj.related_object.banner
                elif obj.verb == 'create_event':
                    related_data = {
                        'event_id': obj.related_object.id,
                        'event_name': obj.related_object.name,
                        'date_start': obj.related_object.date_start,
                        'date_end': obj.related_object.date_end,
                        'name': obj.related_object.user.user_profile.display_name,
                        'time': obj.related_object.time,
                        'pic': obj.related_object.user.user_profile.profile_picture,
                        'golfcourse_name': obj.related_object.golfcourse.name,
                        'golfcourse_id': obj.related_object.golfcourse_id,
                        'description': obj.related_object.description,
                        'event_type': obj.related_object.event_type,
                    }
                    if obj.related_object.event_type == 'GE':
                        related_data['pic'] = obj.related_object.banner
                elif obj.verb == 'create_game':
                    games = Game.objects.filter(group_link=obj.related_object.group_link,
                                                is_finish=True).select_related(
                        'event_member').order_by('gross_score')
                    partners = []
                    rank = 0
                    last_score = 0
                    for g in games:
                        if g.gross_score == 0:
                            continue
                        data = {}
                        if g.event_member.user:
                            data.update({'name': g.event_member.user.user_profile.display_name,
                                         'user_id': g.event_member.user.id,
                                         'handicap': g.event_member.user.user_profile.handicap_us,
                                         'email': g.event_member.user.email,
                                         'avatar': g.event_member.user.user_profile.profile_picture})
                        elif g.event_member.customer:
                            data.update({'name': g.event_member.customer.name,
                                         'user_id': None,
                                         'handicap': g.event_member.customer.handicap,
                                         'email': g.event_member.customer.email,
                                         'avatar': g.event_member.customer.avatar})
                        score = g.gross_score
                        if score > last_score:
                            rank += 1
                            last_score = score
                        strokes = list(g.score.values_list('stroke', flat=True))

                        pars = list(Hole.objects.filter(subgolfcourse_id=g.score.all()[0].tee_type.subgolfcourse_id).values_list('par',
                                                                                                                flat=True))
                        data.update({
                            'gross': g.gross_score,
                            'net': g.hdcp,
                            'rank': rank,
                            'front_nine': sum(strokes[:9]),
                            'front_nine_net': normal_handicap(strokes[:9], pars[:9]),
                            'back_nine': sum(strokes[9:]),
                            'back_nine_net': normal_handicap(strokes[9:], pars[9:])
                        })
                        partners.append(data)
                    no_hole = obj.related_object.golfcourse.number_of_hole
                    related_data.update({
                        'partners': partners,
                        'golfcourse': obj.related_object.golfcourse.id,
                        'golfcourse_name': obj.related_object.golfcourse.name,
                        'number_of_hole': no_hole if no_hole <= 18 else 18
                    })
                elif obj.verb == 'comment':
                    if isinstance(obj.related_object, GolfCourseEvent):
                        related_data = {
                            'event_id': obj.related_object.id,
                            'event_name': obj.related_object.name,
                            'date_start': obj.related_object.date_start,
                            'date_end': obj.related_object.date_end,
                            'name': obj.related_object.user.user_profile.display_name,
                            'time': obj.related_object.time,
                            'pic': obj.related_object.user.user_profile.profile_picture,
                            'golfcourse_name': obj.related_object.golfcourse.name,
                            'golfcourse_id': obj.related_object.golfcourse_id,
                            'description': obj.related_object.description,
                            'event_type': obj.related_object.event_type,
                        }
                    if obj.related_object.event_type == 'GE':
                        related_data['pic'] = obj.related_object.banner
                elif obj.verb == 'review_golfcourse':
                    from api.golfcourseMana.serializers import GolfCourseReviewSerializer
                    rv_serializer = GolfCourseReviewSerializer(obj.related_object)
                    related_data = rv_serializer.data
            activity_ctype = ContentType.objects.get_for_model(UserActivity)
            like_count = Like.objects.filter(content_type=activity_ctype, object_id=obj.id).aggregate(Sum('count'))[
                'count__sum']
            if not like_count:
                like_count = 0
            if related_data and hasattr(obj.related_object, 'is_publish'):
                related_data.update({'is_publish': obj.related_object.is_publish})
            serializers.update({'related_object': related_data,
                                'like_count': like_count,
                                'date_creation': calendar.timegm(obj.date_creation.timetuple())})
            del serializers['content_type']
            del serializers['public']
            return serializers


class PaginatedActivitySerializer(PaginationSerializer):
    class Meta:
        object_serializer_class = UserActivitySerializer


class PaginatedUserSerializer(PaginationSerializer):
    class Meta:
        object_serializer_class = UserDisplaySerializer


class CommentActivitySerializer(serializers.Serializer):
    verb = serializers.CharField(required=True, max_length=255)
    object_id = serializers.IntegerField(required=True)
    content_type = serializers.CharField(required=True, max_length=255)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice


class UserLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLocation

class UserVersionMessageSerializer(serializers.Serializer):
    user = serializers.CharField(required=True)
    version = serializers.FloatField(required=True)
    password = serializers.CharField(required=True)
    source = serializers.CharField(default='ios')
    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if password != '#tuanlywecanfly':
            raise serializers.ValidationError('Password mismatch')
        return attrs
    def to_native(self, obj):
        if obj:
            serializers = super(UserVersionMessageSerializer, self).to_native(obj)
            if not serializers['user'].isdigit(): 
                serializers['version'] = 1.0
            return serializers

class GroupMemberSerializer(serializers.Serializer):
    class Meta:
        model = UserGroupChat
        #fields = ('id','date_joined','user')
    def to_native(self, obj):
        if obj:
            serializers = super(GroupMemberSerializer, self).to_native(obj)
            user = UserDisplaySerializer(obj.user)
            serializers.update(user.data)
            serializers.update({'date_joined':obj.date_joined})
            return serializers

class GroupChatSerializer(serializers.Serializer):
    invited_people = GroupMemberSerializer(many=True, source='group_member', allow_add_remove=True)

    class Meta:
        model = GroupChat

    def to_native(self, obj):
        if obj:
            timestamp = obj.modified_at
            for data in self.context.get('last_modified_date',[]):
                if data['event_id'] == obj.group_id and data['timestamp']:
                    timestamp = datetime.datetime.utcfromtimestamp(int(data['timestamp']))
            obj.group_id
            serializers = super(GroupChatSerializer, self).to_native(obj)
            serializers.update({'last_modified_at': timestamp,
                                'group_id':obj.group_id,
                                'id': obj.id})
            ip = serializers['invited_people']
            new_ip = []
            count = 0
            chat_statistic = [x for x in self.context.get('chat_statistic',[]) \
                                if x and 'record_id' in x.keys() and x['record_id'] == obj.id]
            if chat_statistic: 
                uread, cout = chat_statistic[0]['unread_count'], chat_statistic[0]['comment_count']
            else:
                uread, cout = 0,0
            for i in ip:
                i.update({'status': 'online' if str(i['id']) in self.context.get('online_user',[]) else 'offline',
                          'is_friend': True if i['id'] in self.context.get('friend_list',[]) else False,
                          'is_block': True if i['id'] in self.context.get('privacy_list',[]) else False,
                          'unread': uread})
                
                new_ip.append(i)
            serializers['invited_people'] = new_ip
            serializers.update({'comment_count':cout})
            return serializers
class UserPrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrivacy
        fields = ('target','action')
