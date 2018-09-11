# -*- coding: utf-8 -*-
from rest_framework import (mixins, 
                            viewsets,
                            parsers,
                            status)
from rest_framework.response import Response
from v2.core.questionair.models import *
from v2.utils.permissions import *
from .serializers import *

class ListQuestionairViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuestionairSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (parsers.JSONParser, parsers.FormParser,)

    def get_queryset(self):
        queryset = Questionair.objects.get_questionair()
        return queryset

class AnswerChoiceViewSet(viewsets.ModelViewSet):
    serializer_class = AnswerUserSerializer
    permission_classes = (IsAuthenticated,UserIsOwnerOrReadOnly)
    parser_classes = (parsers.JSONParser, parsers.FormParser,)

    def get_queryset(self):
        user = self.request.user
        queryset = AnswerChoice.objects.filter(user=user)
        return queryset

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            data = kwargs["data"]
            if isinstance(data, list):
                kwargs["data"] = [dict(d, user=self.request.user.id) for d in kwargs["data"]] 
                kwargs["many"] = True
            else:
                kwargs["data"].update({'user': self.request.user.id})
        return super(AnswerChoiceViewSet, self).get_serializer(*args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            serializer.update_or_create()
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=self.get_success_headers(serializer.data))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)