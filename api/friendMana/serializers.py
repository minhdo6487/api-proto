from geopy import distance
from core.user.models import UserActivity
from django.db.models import Avg
from rest_framework import serializers
from rest_framework.pagination import PaginationSerializer

from api.userMana.serializers import UserDisplaySerializer
from core.friend.models import FriendRequest, FriendConnect, Friend, FriendPostTrack
from core.game.models import Game
from core.user.models import UserLocation


class FriendRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendRequest
        fields = ('id', 'from_user', 'to_user', 'date_request')


class FriendConnectSerializer(serializers.ModelSerializer):
    class Meta:
        model = FriendConnect
        fields = ('id', 'user', 'friend', 'date_accepted')


class FriendSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friend

    def to_native(self, obj):
        if obj:
            serializers = super(FriendSerializer, self).to_native(obj)
            to_user_sr_context = {'user_id': self.context['user_id']} if self.context.get('user_id') else {}
            to_user_sr = UserDisplaySerializer(obj.to_user, context=to_user_sr_context)
            track = FriendPostTrack.objects.filter(user=obj.from_user, to_user=obj.to_user).first()

            if track:
                new_post = UserActivity.objects.filter(user=obj.to_user, date_creation__gte=track.timestamp).count()
            else:
                new_post = UserActivity.objects.filter(user=obj.to_user).count()
            if not new_post:
                new_post = 0
            friend_distance = 'N/A'
            if self.context.get('lat') and self.context.get('lon'):
                user_location = UserLocation.objects.filter(user=obj.to_user).order_by('-modified_at').first()
                if user_location:
                    friend_distance = round(distance.distance((user_location.lat, user_location.lon), (self.context['lat'], self.context['lon'])).kilometers, 2)
                    friend_distance = "{0:.2f}".format(friend_distance)
            serializers.update({
                'to_user_info': to_user_sr.data,
                'new_post': new_post,
                'friend_distance': friend_distance
            })
            return serializers


class PaginatedFriendSerializer(PaginationSerializer):
    """
    Serializes page objects of notification querysets.
    """

    class Meta:
        object_serializer_class = FriendSerializer
