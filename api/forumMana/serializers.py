from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from core.post.models import Post
from core.comment.models import Comment
from core.like.models import Like
from api.userMana.serializers import UserSerializer
from api.likeMana.serializers import LikeSerializer
from api.commentMana.serializers import CommentSerializer
from core.user.models import UserProfile


class MiniPostSeri(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', max_length=20, read_only=True)

    class Meta:
        model = Post
        fields = ('id', 'username', 'user')


class ListPostSeri(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', max_length=20, read_only=True)

    class Meta:
        model = Post
        fields = ('id', 'username', 'title', 'date_creation', 'date_modified', 'view_count')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(ListPostSeri, self).to_native(obj)
            ctype = ContentType.objects.get_for_model(obj)
            likes = Like.objects.filter(content_type=ctype, object_id=obj.id)
            likes2 = LikeSerializer(likes, many=True)
            serializers.update({
                'likes': likes2.data
            })
            serializers.update({
                'like_count': likes.count()
            })
            cmts = Comment.objects.filter(content_type=ctype, object_id=obj.id).order_by('-pk')
            if cmts.count() > 0:
                # cmts = list(sorted(cmts, key=lambda x: x['id'], reverse=True))
                cmt = CommentSerializer(cmts[0])
                serializers.update({
                    'last_comment': cmt.data
                })
            serializers.update({
                'comment_count': cmts.count()
            })
            user = UserProfile.objects.get(user=obj.user.id)
            serializers.update({
                'avatar': user.profile_picture
            })
            user = User.objects.get(id=obj.user.id)
            serializers.update({
                'full_name': user.user_profile.display_name
            })
            return serializers


class NewPostSeri(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('id', 'user', 'title', 'content', 'content_type', 'object_id')


class NewCommentSeri(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'content_type', 'object_id')


class MultiCommentSeri(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    picture = serializers.CharField(source='user.user_profile.profile_picture')

    class Meta:
        model = Comment
        fields = ('id', 'user', 'username', 'content', 'picture', 'date_creation')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(MultiCommentSeri, self).to_native(obj)
            ctype = ContentType.objects.get_for_model(obj)
            cmts = Comment.objects.filter(content_type=ctype.id, object_id=obj.id)
            cmts2 = MultiCommentSeri(cmts, many=True)
            serializers.update({
                'comment': cmts2.data
            })
            likes = Like.objects.filter(content_type=ctype, object_id=obj.id)
            likes2 = LikeSerializer(likes, many=True)
            serializers.update({
                'like_count': likes.count()
            })
            serializers.update({
                'likes': likes2.data
            })
            serializers.update({
                'full_name': obj.user.user_profile.display_name
            })
            serializers.update({
                'picture': obj.user.user_profile.profile_picture
            })
            return serializers


class DetailPostSeri(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user')

    class Meta:
        model = Post
        fields = ('id', 'user', 'user_detail', 'title', 'content', 'date_creation', 'date_modified', 'view_count')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(DetailPostSeri, self).to_native(obj)
            ctype = ContentType.objects.get_for_model(obj)
            likes = Like.objects.filter(content_type=ctype, object_id=obj.id)
            likes2 = LikeSerializer(likes, many=True)
            serializers.update({
                'likes': likes2.data
            })
            serializers.update({
                'like_count': likes.count()
            })
            cmts = Comment.objects.filter(content_type=ctype, object_id=obj.id)
            serializers.update({
                'comment_count': cmts.count()
            })
            cmts2 = MultiCommentSeri(cmts, many=True)
            serializers.update({
                'comment': cmts2.data
            })
            return serializers