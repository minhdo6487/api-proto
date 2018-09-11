from rest_framework import serializers

from core.user.models import Degree, Major


class MajorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Major
        fields = ('id', 'name')


class DegreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Degree
        fields = ('id', 'name')
