from rest_framework import serializers
from django.contrib.auth.models import User

from core.checkin.models import Checkin
from core.customer.models import Customer
from api.customerMana.serializers import CustomerSerializer
from api.userMana.serializers import UserDisplaySerializer


class CheckinSerializer(serializers.ModelSerializer):
    player = serializers.SerializerMethodField('get_player_object')
    name = serializers.CharField(max_length=100, required=True)
    email = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    @staticmethod
    def get_player_object(obj):
        related = obj.player
        if related is not None:
            if isinstance(related, Customer):
                return CustomerSerializer(related).data
            elif isinstance(related, User):
                return UserDisplaySerializer(related).data
            else:
                return related.id
        return None

    class Meta:
        model = Checkin
        fields = ('reservation_code', 'total_amount', 'date', 'time', 'player', 'golfcourse', 'play_number')


class MultiCheckinSerializer(serializers.Serializer):
    players = CheckinSerializer(many=True)






