from rest_framework.parsers import JSONParser, FormParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.advertise.models import Advertise
from api.advertiseMana.serializers import AdvertiseSerializer
from utils.rest.permissions import UserIsOwnerOrReadOnly


class AdvertiseViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Advertise.objects.all()
    serializer_class = AdvertiseSerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly, )
    parser_classes = (JSONParser, FormParser,)