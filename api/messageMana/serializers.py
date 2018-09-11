from rest_framework import serializers

from core.messsage.models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('date_send', 'date_read', 'date_show', 'from_user', 'to_user', 'content')