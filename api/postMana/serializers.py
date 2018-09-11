from rest_framework import serializers

from core.post.models import Post


class PostSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', max_length=20, read_only=True)

    class Meta:
        model = Post
        fields = (
            'id', 'username', 'title', 'content', 'link', 'date_creation', 'date_modified', 'content_type', 'object_id',
            'view_count')


class FullPostSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', max_length=20, read_only=True)

    class Meta:
        model = Post