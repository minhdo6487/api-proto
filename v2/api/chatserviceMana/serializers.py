from rest_framework import serializers
from v2.core.chatservice.models import *
from core.user.models import UserGroupChat
import datetime

class UserChatPresenceSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True)
    class Meta(object):
        model = UserChatPresence
        fields = ('user','room_id','status', 'password')
        ordering = ('-id',)
    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if password != '#letsgolf':
            raise serializers.ValidationError('Password mismatch')
        return attrs
    def __update_or_create__(self, data):
        if 'password' in data.keys():
            data.pop('password')
        status = data.pop('status')
        user = data.pop('user')
        room_id = data.pop('room_id')
        my_object, created = UserChatPresence.objects.get_or_create(user_id=user, room_id=room_id)
        my_object.status = status
        my_object.modified_at = datetime.datetime.utcnow()
        my_object.save(update_fields=['status','modified_at'])
    def update_or_create(self):
        data = self.data.copy()
        data = data if isinstance(data, list) else [data]
        [self.__update_or_create__(d) for d in data]

class UserChatQuerySerializer(serializers.ModelSerializer):
    class Meta(object):
        model = UserChatPresence
        fields = ('room_id', 'modified_at')
        ordering = ('-id',)
    def to_native(self, obj):
        if obj is not None:
            serializers = super(UserChatQuerySerializer, self).to_native(obj)
            user_groupchat = UserGroupChat.objects.filter(user=obj.user, groupchat__group_id=obj.room_id).first()
            if user_groupchat:
                serializers.update({'date_joined': "{}Z".format(user_groupchat.date_joined.isoformat('T'))})
            serializers.update({'modified_at': "{}Z".format(obj.modified_at.isoformat('T'))})
            return serializers