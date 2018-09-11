from django.contrib.contenttypes.models import ContentType
from core.golfcourse.models import GolfCourseEvent
# from core.invitation.models import Invitation
from core.realtime.models import UserSubcribe

__author__ = 'toantran'
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import SubcribeSerializer

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def subcribe(request):
    serializer = SubcribeSerializer(data=request.DATA)
    if not serializer.is_valid():
         return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
    if serializer.data['content_type'] == 'Event' or serializer.data['content_type'] == 'GE':
        ctype = ContentType.objects.get_for_model(GolfCourseEvent)
    # elif serializer.data['content_type'] == 'Invite':
    #     ctype = ContentType.objects.get_for_model(Invitation)
    user_subcribe = UserSubcribe.objects.get(content_type=ctype, object_id=serializer.data['object_id'])
    subcribe_list = eval(user_subcribe.user)
    if request.user.id not in subcribe_list:
        subcribe_list.append(request.user.id)
        user_subcribe.user = subcribe_list
        user_subcribe.save(update_fields=['user'])
    return Response({'status': '200', 'code': 'OK',
                     'detail': 'OK'}, status=200)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def unsubcribe(request):
    serializer = SubcribeSerializer(data=request.DATA)
    if not serializer.is_valid():
         return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
    if serializer.data['content_type'] == 'Event' or serializer.data['content_type'] == 'GE':
        ctype = ContentType.objects.get_for_model(GolfCourseEvent)
    # elif serializer.data['content_type'] == 'Invite':
    #     ctype = ContentType.objects.get_for_model(Invitation)
    user_subcribe = UserSubcribe.objects.get(content_type=ctype, object_id=serializer.data['object_id'])
    subcribe_list = eval(user_subcribe.user)
    subcribe_list.remove(request.user.id)
    user_subcribe.user = subcribe_list
    user_subcribe.save(update_fields=['user'])
    return Response({'status': '200', 'code': 'OK',
                     'detail': 'OK'}, status=200)