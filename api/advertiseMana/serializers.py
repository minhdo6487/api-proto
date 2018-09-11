from rest_framework import serializers

from core.advertise.models import Advertise


class AdvertiseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertise
        fields = ('from_date', 'to_date', 'notice_type', 'image', 'link')