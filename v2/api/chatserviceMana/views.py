# -*- coding: utf-8 -*-
from rest_framework import (mixins, 
                            viewsets,
                            parsers,
                            status,
                            views)
from rest_framework.response import Response
from v2.core.questionair.models import *
from v2.utils.permissions import *
from .serializers import *
from .tasks import *

class UserChatPresenceViewSet(viewsets.ModelViewSet):
    queryset = UserChatPresence.objects.all()
    serializer_class = UserChatPresenceSerializer
    parser_classes = (parsers.JSONParser, parsers.FormParser,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            serializer.update_or_create()
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=self.get_success_headers(serializer.data))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserChatStatisticViewSet(views.APIView):
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly)
    serializer_class = UserChatQuerySerializer

    @staticmethod
    def get(request):
        data = get_user_chat_statistic(request.user)
        return Response({'status': status.HTTP_200_OK, 'code': 'OK', 'detail': data}, status=status.HTTP_200_OK)