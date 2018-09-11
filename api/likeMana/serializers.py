from rest_framework import serializers

from core.like.models import Like, View


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ('count',)


class ViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = View
        fields = ('count',)