from rest_framework import serializers

from api.customerMana.serializers import CustomerSerializer
from api.userMana.serializers import UserDisplaySerializer
from core.comment.models import Comment
from core.game.models import EventMember, HOST
from core.golfcourse.models import GolfCourseEvent, GolfCourseEventPriceInfo, GolfCourseEventHotel
from core.invitation.models import *


class InvitedPeopleSerialier(serializers.ModelSerializer):
    player = serializers.SerializerMethodField('get_player_object')

    @staticmethod
    def get_player_object(obj):
        if obj.customer:
            return CustomerSerializer(obj.customer).data
        elif obj.user:
            return UserDisplaySerializer(obj.user).data
        return None

    class Meta:
        model = EventMember
        fields = ('id', 'player', 'status')

class InvitationEventPriceInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventPriceInfo
        ordering = ('id',)

class InvitationEventHotelInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseEventHotel
        ordering = ('id',)
    def to_native(self, obj):
        if obj:
            serializers = super(InvitationEventHotelInfoSerializer, self).to_native(obj)
            if obj.hotel:
                serializers.update({'hotel_name': obj.hotel.name,
                                    'hotel_address': obj.hotel.address})
            return serializers

class InvitationSerializer(serializers.ModelSerializer):
    event_price_info = InvitationEventPriceInfoSerializer(many=True, source='event_price_info', allow_add_remove=True, required=False)
    hotel_info = InvitationEventHotelInfoSerializer(many=True, source='event_hotel_info', allow_add_remove=True, required=False)
    class Meta:
        model = GolfCourseEvent
        fields = ('id', 'time', 'user', 'golfcourse', 'description', 'date_start', 'date_end','pass_code', 'score_type', 'pod','discount', 'event_price_info', 'hotel_info', 'allow_stay')


    def to_native(self, obj):
        if obj is not None:
            serializers = super(InvitationSerializer, self).to_native(obj)
            partners = obj.event_member.all().exclude(status=HOST)
            partners_serializers = InvitedPeopleSerialier(partners, many=True)
            profile = obj.user.user_profile
            username = obj.user.username
            pic = profile.profile_picture
            phone = profile.mobile
            name = profile.display_name
            event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            comment_count = Comment.objects.filter(content_type=event_ctype, object_id=obj.id).count()
            object_id = obj.id
            # cmt_serializer = CommentSerializer(comments)
            content_type = "Event"

            serializers.update({
                'username': username,
                'pic': pic,
                'phone_number': phone,
                'name': name,
                'comment_count': comment_count,
                'invite_people': partners_serializers.data,
                'join_count': len(partners_serializers.data),
                'object_id': object_id,
                'content_type': content_type,
                'date': obj.date_start,
                'golfcourse': obj.golfcourse.name,
                'golfcourse_id': obj.golfcourse_id,
                'from_user_id': obj.user.id
            })
            if obj.pass_code:
                serializers.update({'has_pass': True})
            else:
                serializers.update({'has_pass': False})
            del serializers['pass_code']
            return serializers

    def get_validation_exclusions(self, instance=None):
        exclusions = super(InvitationSerializer, self).get_validation_exclusions(instance)
        return exclusions + ['invite_people']
