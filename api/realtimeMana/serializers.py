from rest_framework import serializers

__author__ = 'toantran'

class SubcribeSerializer(serializers.Serializer):
    content_type = serializers.CharField(required=True, max_length=255)
    object_id = serializers.IntegerField()