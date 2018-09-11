from rest_framework import permissions
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.decorators import action
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response

from api.inviteMana.views import DOW
from core.comment.models import Comment
from api.commentMana.serializers import CommentSerializer
from core.gallery.models import Gallery
from core.game.models import EventMember
from core.golfcourse.models import GolfCourseEvent

# from core.invitation.models import Invitation
from core.notice.models import Notice
from core.realtime.models import UserSubcribe
from utils.rest.permissions import UserIsOwnerOrReadOnly
from api.likeMana.serializers import LikeSerializer
from core.like.models import Like
from utils.django.models import get_or_none
from utils.rest.code import code
from .tasks import  send_notification_event_channel
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from GolfConnect.settings import CURRENT_ENV


class CommentViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     GenericViewSet):
    """ Viewset handle for all comments
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, UserIsOwnerOrReadOnly)

    # Save current user to the comment
    def pre_save(self, obj):
        obj.user = self.request.user

    def list(self, request, *args, **kwargs):
        content_type = request.GET.get('content_type', None)
        object_id = request.GET.get('object_id', None)
        index = request.GET.get('index', 0)
        offset = request.GET.get('offset', 10)
        result = {
            'comment': [],
            'comment_count': 0,
            'comment_left': 0
        }
        if content_type and object_id:
            # if content_type == 'Invite':
            # ctype = ContentType.objects.get_for_model(Invitation)
            # elif content_type == 'Event' or content_type == 'GE':
            ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            total_comment = Comment.objects.filter(content_type=ctype, object_id=int(object_id)).count()
            end = int(index) + int(offset)
            comment = Comment.objects.filter(content_type=ctype, object_id=int(object_id))[int(index):end]
            serializer = CommentSerializer(comment)
            comment_left = total_comment - len(serializer.data)
            result.update({
                'index': index,
                'offset': offset,
                'comment': serializer.data,
                'comment_count': total_comment,
                'comment_left': comment_left
            })
        return Response(result, status=200)

    def create(self, request, *args, **kwargs):
        content_type = request.DATA.get('content_type', '')
        ctype = None
        if content_type == 'Event' or content_type == 'GE':
            event = get_or_none(GolfCourseEvent, id=request.DATA['object_id'])
            if not event:
                return Response({'status': '404', 'code': 'E_NOT_FOUND',
                                 'detail': 'Not found'}, status=404)
            ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            api = 'api/event/' + str(request.DATA['object_id']) + '/?fields=cmt'
            channel = CURRENT_ENV + '_event' + str(request.DATA['object_id'])
            # # Send notice to other commentors  # #
            # Format message
            message = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                request.user.user_profile.display_name) + '</a> bình luận sự kiện tại <b>' + event.golfcourse.name + '</b>'
            if event.time:
                message += ' diễn ra lúc <b>' + str(event.time.strftime('%H:%M')) + '</b>'
            message += ' vào <b>' + DOW[str(event.date_start.strftime('%A'))] + ', ' + str(
                event.date_start.strftime('%d-%m-%Y')) + '</b>'

            message_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                request.user.user_profile.display_name) + '</a>  commented event at <b>' + event.golfcourse.name + '</b>'
            if event.time:
                message_en += ' at <b>' + str(event.time.strftime('%H:%M')) + '</b>'
            message_en += ' on <b>' + str(event.date_start.strftime('%A')) + ', ' + str(
                event.date_start.strftime('%d-%m-%Y')) + '</b>'
            ## Send to commentors
            user_subcribe = UserSubcribe.objects.get(content_type=ctype,
                                                     object_id=request.DATA['object_id'])
            subcribe_list = eval(user_subcribe.user)
            for m in subcribe_list:
                if m != request.user.id:
                    Notice.objects.create(content_type=ctype,
                                          object_id=request.DATA['object_id'],
                                          to_user_id=m,
                                          detail=message,
                                          detail_en=message_en,
                                          notice_type='IN',
                                          from_user=request.user,
                                          send_email=False)
        # elif content_type == 'Invite':
        # ctype = ContentType.objects.get_for_model(Invitation)
        #     api = 'api/invitation/' + str(request.DATA['object_id']) + '/'
        #     channel = CURRENT_ENV + '_invitation' + str(request.DATA['object_id'])
        if ctype:
            request.DATA.update({'content_type': ctype.id})
        request.DATA.update({'user': request.user.id})
        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETERS',
                             'detail': serializer.errors}, status=400)
        cmt = serializer.save()
        if 'images' in request.DATA:
            cmt_ctype = ContentType.objects.get_for_model(Comment)
            gallery = []
            for i in request.DATA['images']:
                gallery.append(Gallery(picture=i, object_id=cmt.id, content_type=cmt_ctype))
            Gallery.objects.bulk_create(gallery)

        #send_notification_to_subcribe_user(api, request.user.user_profile.display_name, request.user.id, ctype.id, cmt.object_id)
        send_notification_event_channel(api, channel)
        return Response({'status': 200, 'code': 'OK', 'detail': serializer.data}, status=200)

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
            ctype = ContentType.objects.get_by_natural_key('comment', 'comment')
            likes = Like.objects.filter(content_type=ctype.id, object_id=pk)
            serializer = LikeSerializer(likes, many=True)
            # return data to client
            return Response({'status': '200', 'code': 'OK',
                             'detail': serializer.data}, status=200)
        elif request.method == 'POST':
            ctype = ContentType.objects.get_by_natural_key('comment', 'comment')
            likes = get_or_none(Like, user_id=request.user.id, content_type=ctype.id, object_id=pk)
            if likes is None:
                post1 = get_or_none(Comment, pk=pk)
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