from rest_framework import serializers

from core.gallery.models import Gallery


class GolfCourseGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ('id', 'picture', 'description')