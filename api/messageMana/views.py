from rest_framework.parsers import JSONParser, FormParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.messsage.models import Message
from api.messageMana.serializers import MessageSerializer
from utils.rest.permissions import UserIsOwnerOrReadOnly


class MessageViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
    parser_classes = (JSONParser, FormParser,)