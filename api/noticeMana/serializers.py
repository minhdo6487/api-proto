from bs4 import BeautifulSoup
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from rest_framework import serializers
from rest_framework.pagination import PaginationSerializer
import calendar
from core.booking.models import BookedTeeTime
from core.friend.models import Friend
from core.game.models import Game
from core.golfcourse.models import GolfCourseEvent
from core.notice.models import Notice


# from core.invitation.models import Invitation


class NoticeSerializer(serializers.ModelSerializer):
    """
    Notification serializer
    """
    from_user_detail = serializers.HyperlinkedRelatedField(
        source='from_user',
        view_name='user-detail',
        read_only=True
    )
    related_object = serializers.SerializerMethodField('get_related_object')

    def get_related_object(self, obj):
        if obj:
            related = obj.related_object
            if related is not None:
                if isinstance(related, BookedTeeTime):
                    return reverse('teetime-detail', kwargs={'pk': obj.object_id})
                elif isinstance(related, Game):
                    return reverse('game-detail', kwargs={'pk': obj.object_id})
                elif isinstance(related, GolfCourseEvent):
                    return '/api/invitation/' + str(obj.object_id) + '/'
                else:
                    return related.id
        return None

    class Meta:
        model = Notice
        fields = (
            'id', 'is_read', 'is_show', 'from_user',
            'from_user_detail', 'related_object',
            'detail', 'detail_en', 'object_id', 'notice_type', 'date_create'
        )

    def to_native(self, obj):
        if obj is not None:
            event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            serializers = super(NoticeSerializer, self).to_native(obj)
            soup_en = BeautifulSoup(obj.detail_en)
            soup_vi = BeautifulSoup(obj.detail)
            if obj.notice_type == 'I':
                if obj.content_type == event_ctype:
                    serializers.update({
                        'date_play': obj.related_object.date_start,
                    })
                elif obj.related_object.date:
                    serializers.update({
                        'date_play': obj.related_object.date,
                    })

            elif obj.notice_type == 'FR':
                friend = obj.related_object
                user_friend = Friend.objects.filter(from_user=friend.to_user).values_list('to_user',flat=True)
                mutual_friend = Friend.objects.filter(from_user=friend.from_user, to_user_id__in=user_friend).count()
                serializers.update({
                    'mutual_friend':mutual_friend
                })

            else:
                serializers.update({
                    'plain_text': soup_en.text,
                    'plain_text_vi': soup_vi.text})
            if obj.from_user is not None:
                from_user_avatar = obj.from_user.user_profile.profile_picture
            else:
                from_user_avatar = '/assets/images/att04.png'
            serializers.update({
                'username': obj.from_user.user_profile.display_name,
                'plain_text': soup_en.text.replace(obj.from_user.user_profile.display_name + ' ',
                                                   ''),
                'plain_text_vi': soup_vi.text.replace(obj.from_user.user_profile.display_name + ' ',
                                                      ''),
                'from_user_avatar': from_user_avatar,
                'date_create': calendar.timegm(obj.date_create.timetuple())
            })
            return serializers


class PaginatedNotificationSerializer(PaginationSerializer):
    """
    Serializes page objects of notification querysets.
    """

    class Meta:
        object_serializer_class = NoticeSerializer


class MessageTranslate(serializers.Serializer):
    alert_vi = serializers.CharField(required=True)
    alert_en = serializers.CharField(required=True)


class PushMessageSerializer(serializers.Serializer):
    user = serializers.IntegerField(required=True)
    message = serializers.CharField(required=True)
    translate_message = MessageTranslate(required=False)
    badge = serializers.IntegerField(default=0)
    password = serializers.CharField(required=True)

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if password != '#letsgolf':
            raise serializers.ValidationError('Password mismatch')
        return attrs

class PushEventMessageSerializer(serializers.Serializer):
    event_id = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    translate_message = MessageTranslate(required=False)
    badge = serializers.IntegerField(default=0)
    password = serializers.CharField(required=True)

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if password != '#letsgolf':
            raise serializers.ValidationError('Password mismatch')
        return attrs

class PushEventMessagev2Serializer(serializers.Serializer):
    event_id = serializers.CharField(required=True)
    from_user = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if password != '#letsgolf':
            raise serializers.ValidationError('Password mismatch')
        return attrs

class CrawlTeetimeSerializer(serializers.Serializer):
    day = serializers.IntegerField(default=0, required=False)
    password = serializers.CharField(required=True)

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if password != '#letsgolf':
            raise serializers.ValidationError('Password mismatch')
        return attrs
