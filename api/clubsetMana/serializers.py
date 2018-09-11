from rest_framework import serializers

from core.golfcourse.models import ClubSets


class ClubSetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSets
        fields = ('id', 'name', 'price')