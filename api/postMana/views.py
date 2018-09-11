from operator import attrgetter

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser
from django.contrib.contenttypes.models import ContentType

from core.friend.models import FriendConnect
from core.post.models import Post
from core.like.models import Like
from api.postMana.serializers import PostSerializer
from api.likeMana.serializers import LikeSerializer
from api.commentMana.serializers import CommentSerializer
from utils.rest.permissions import UserIsOwnerOrReadOnly
from utils.django.models import get_or_none
from utils.rest.code import code


class PostViewSet(viewsets.ModelViewSet):
    """ Viewset handle for post status methods
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, UserIsOwnerOrReadOnly)

    # Save current user to the post
    def pre_save(self, obj):
        """ Saves the current user
        """
        obj.user = self.request.user

    def list(self, request):
        """ Return the list of posted status of current user
        """
        # get post list started by login user
        posts = Post.objects.filter(user_id=int(request.user.id))
        post_serializer = PostSerializer(posts, many=True)
        return Response({'status': '200', 'code': 'OK',
                         'detail': post_serializer.data}, status=200)

    @staticmethod
    @action(methods=['GET', 'POST'])
    def read(request, pk=None):
        post = get_or_none(Post, id=pk)
        post.view_count += 1
        post.save()
        return Response(status=200)

    @staticmethod
    @action(methods=['GET', 'POST'])
    def likes(request, pk=None):
        """
            Function implements 'like' and 'unlike' method via POST
            and get the number of likes on the status via GET.
            Returns:
            The return code::

              200 -- Return like model
              400 -- Wrong Post - E_POST_NOT_FOUND.
                  -- E_INVALID_PARAMETER_VALUES.
              201 -- Save like done - OK_LIKE.
              500 -- Server can't save data - E_NOT_SAVE.
              204 -- Unlike success - OK_UNLIKE.
        """
        if request.method == 'GET':
            # get list like by post id
            ctype = ContentType.objects.get_by_natural_key('post', 'post')
            likes = Like.objects.filter(content_type=ctype.id, object_id=pk)
            serializer = LikeSerializer(likes, many=True)
            # return data to client
            return Response({'status': '200', 'code': 'OK',
                             'detail': serializer.data}, status=200)
        elif request.method == 'POST':
            ctype = ContentType.objects.get_by_natural_key('post', 'post')
            likes = get_or_none(Like, user_id=request.user.id, content_type=ctype.id, object_id=pk)
            if likes is None:
                post1 = get_or_none(Post, pk=pk)
                if post1 is None:
                    return Response({'status': '400', 'code': 'E_POST_NOT_FOUND',
                                     'detail': code['E_POST_NOT_FOUND']}, status=400)

                serializer = LikeSerializer(
                    data={'user': request.user.id, 'content_type': ctype.id, 'object_id': post1.id})
                if not serializer.is_valid():
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': serializer.errors}, status=400)
                serializer.save()

                is_save = get_or_none(Like, user_id=request.user.id, content_type=ctype.id, object_id=post1.id)
                if is_save is not None:
                    return Response({'status': '201', 'code': 'OK_LIKE',
                                     'detail': serializer.data}, status=201)
                return Response({'status': '500', 'code': 'E_NOT_SAVE',
                                 'detail': code['E_NOT_SAVE']}, status=500)
            else:
                likes.delete()
                return Response({'status': '204', 'code': 'OK_UNLIKE',
                                 'detail': code['OK_UNLIKE']}, status=204)

    @staticmethod
    @action(methods=['POST'])
    def share(request, pk=None):
        """
            Share a post.
            Returns:
            The return code::
              201 -- OK_SHARE.
              400 -- E_POST_NOT_FOUND.
                  -- E_INVALID_PARAMETER_VALUES.
              500 -- E_NOT_SAVE.
        """
        # Check if post id is wrong
        post = get_or_none(Post, pk=pk)
        if post is None:
            return Response({'status': '400', 'code': 'E_POST_NOT_FOUND',
                             'detail': code['E_POST_NOT_FOUND']}, status=400)

        # If not None : Create new post base on old post
        data = {"content": post.content, "link": post.link}
        serializer = PostSerializer(data=data)
        if not serializer.is_valid:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        # Save
        serializer.save()
        is_save = get_or_none(Post, user_id=request.user.id, content=post.content)
        if is_save is None:
            return Response({'status': '500', 'code': 'E_NOT_SAVE',
                             'detail': code['E_NOT_SAVE']}, status=500)
        return Response({'status': '201', 'code': 'OK_SHARE',
                         'detail': code['OK_SHARE']}, status=201)

    @staticmethod
    @action(methods=['POST'])
    def comment(request, pk=None):
        ctype = ContentType.objects.get_by_natural_key('post', 'post')
        serializer = CommentSerializer(data={
            'user': request.user.id,
            'content_type': ctype.id,
            'object_id': pk,
            'content': request.DATA['content']})
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=400)
        return Response({'status': '201',
                         'code': 'OK_LIKE',
                         'detail': serializer.data}, status=201)


class FeedViewSet(viewsets.ModelViewSet):
    """ Viewset handle for feeds
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, UserIsOwnerOrReadOnly)

    def list(self, request):
        """
        Return the list of feeds
        Returns:
        The return code::

          400 -- E_INVALID_PARAMETER_VALUES.
          200 -- Return success.

        """
        current_user = request.user
        friend_list = FriendConnect.objects.filter(user=current_user)
        user_post_list = Post.objects.filter(user_id=int(current_user.id))
        result_list = []
        for x in range(0, user_post_list.count()):
            result_list.append(user_post_list[x])
        for y in range(0, friend_list.count()):
            friend_post_list = Post.objects.filter(user_id=int(friend_list[y].friend_id))
            for z in range(0, friend_post_list.count()):
                result_list.append(friend_post_list[z])
        result_list.sort(key=attrgetter('date_creation'), reverse=True)
        serializer = PostSerializer(result_list, many=True)
        if serializer.is_valid:
            return Response({'status': '200', 'code': 'OK',
                             'detail': serializer.data}, status=200)
        else:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
