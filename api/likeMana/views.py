import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework import permissions
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework import viewsets
from api.inviteMana.views import DOW
from core.game.models import EventMember

from core.golfcourse.models import GolfCourseEvent, GolfCourse, GolfCourseReview
from core.like.models import Like, View
from api.likeMana.serializers import LikeSerializer, ViewSerializer
from core.notice.models import Notice
from core.user.models import UserActivity
from utils.django.models import get_or_none


class LikeViewSet(viewsets.ModelViewSet):
    """ Viewset handle for all likes
    """
    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        content_type = request.DATA.get('content_type', '')
        object_id = request.DATA.get('object_id', '')
        if not content_type or not object_id:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'object or content is null'}, status=400)
        if content_type == 'Event':
            event = get_or_none(GolfCourseEvent, id=object_id)
            if not event:
                return Response({'status': '404', 'code': 'E_NOT_FOUND',
                                 'detail': 'Not found'}, status=400)
            ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            if request.user.is_authenticated():
                like, created = Like.objects.get_or_create(content_type=ctype, object_id=int(object_id), user=request.user)
                event_member = EventMember.objects.filter(event_id=object_id)
                message = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                        request.user.user_profile.display_name) + '</a> thích sự kiện tại <b>' + event.golfcourse.name + '</b>'
                if event.time:
                    message += ' lúc <b>' + str(event.time.strftime('%H:%M')) + '</b>'
                message += ' vào <b>' + DOW[str(event.date_start.strftime('%A'))] + ', ' + str(
                    event.date_start.strftime('%d-%m-%Y')) + '</b>'

                message_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
                    request.user.user_profile.display_name) + '</a>  like the event at <b>' + event.golfcourse.name + '</b>'
                if event.time:
                    message_en += ' at <b>' + str(event.time.strftime('%H:%M')) + '</b>'
                message_en += ' on <b>' + str(event.date_start.strftime('%A')) + ', ' + str(
                    event.date_start.strftime('%d-%m-%Y')) + '</b>'
                for m in event_member:
                    if m.user:
                        Notice.objects.create(content_type=ctype,
                                              object_id=object_id,
                                              to_user=m.user,
                                              detail=message,
                                              detail_en=message_en,
                                              notice_type='IN',
                                              from_user=request.user,
                                              send_email=False)
                Notice.objects.create(content_type=ctype,
                                      object_id=object_id,
                                      to_user=event.user,
                                      detail=message,
                                      detail_en=message_en,
                                      notice_type='IN',
                                      from_user=request.user,
                                      send_email=False)
                #Notice.objects.bulk_create(notices)
                #obj, created = EventMember.objects.get_or_create(user=request.user, event_id=object_id)
                #obj.status = 'A'
                #obj.is_join = True
                #obj.save()
            else:
                like, created = Like.objects.get_or_create(content_type=ctype, object_id=int(object_id))
            like.count += 1
            like.save()
        elif content_type == 'activity':
            ctype = ContentType.objects.get_for_model(UserActivity)

            if request.user.is_authenticated():
                like, created = Like.objects.get_or_create(content_type=ctype, object_id=int(object_id), user=request.user)
            else:
                like, created = Like.objects.get_or_create(content_type=ctype, object_id=int(object_id))
            like.count += 1
            like.save()
        elif content_type == 'golfcourse-review':
            ctype = ContentType.objects.get_for_model(GolfCourseReview)

            if request.user.is_authenticated():
                like, created = Like.objects.get_or_create(content_type=ctype, object_id=int(object_id),
                                                           user=request.user)
            else:
                like, created = Like.objects.get_or_create(content_type=ctype, object_id=int(object_id))
            like.count += 1
            like.save()
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)


class ViewViewSet(mixins.CreateModelMixin, GenericViewSet):
    """ Viewset handle for all likes
    """
    queryset = View.objects.all()
    serializer_class = ViewSerializer
    parser_classes = (JSONParser, FormParser,)

    def create(self, request, *args, **kwargs):
        content_type = request.DATA.get('content_type', '')
        object_id = request.DATA.get('object_id', '')
        if not content_type or not object_id:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'object or content is null'}, status=400)
        if content_type == 'Event':
            if not GolfCourseEvent.objects.filter(id=int(object_id)).exists():
                return Response({'status': '404', 'code': 'E_NOT_FOUND',
                                 'detail': 'Not found'}, status=400)
            ctype = ContentType.objects.get_for_model(GolfCourseEvent)
            view, created = View.objects.get_or_create(content_type=ctype, object_id=int(object_id))
            view.count += 1
            view.save()
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)