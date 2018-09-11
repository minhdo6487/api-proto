from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from core.comment.models import Comment
from core.gallery.models import Gallery
from core.user.models import UserProfile


class CommentSerializer(serializers.ModelSerializer):
    #username = serializers.CharField(source='user.username', max_length=50, read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'date_creation', 'date_modified', 'content_type', 'object_id')

    def to_native(self, obj):
        if obj:
            serializers = super(CommentSerializer, self).to_native(obj)
            if obj.user_id is not None:
                user_profile = UserProfile.objects.only('display_name','profile_picture').get(user_id=obj.user_id)
                serializers.update({'display_name':user_profile.display_name,
                                    'profile_picture':user_profile.profile_picture})
            ctype = ContentType.objects.get_for_model(Comment)
            images = Gallery.objects.filter(object_id=obj.id,content_type=ctype).values_list('picture',flat=True)
            serializers.update({'images':images})
            del serializers['content_type']
            del serializers['object_id']
            del serializers['user']
            return serializers

class MiniCommentSeri(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', max_length=50, read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'username', 'user')

        # def to_native(self, obj):
        # if obj is not None:
        # serializers = super(MiniCommentSeri, self).to_native(obj)
        #         ctype = ContentType.objects.get_for_model(obj)
        #         cmts = Comment.objects.filter(content_type=ctype.id, object_id=obj.id)
        #         for item in cmts:
        #             item_seri = MiniCommentSeri(item)
        #             serializers.update({'comment': item_seri.data})
        #         return serializers
