from rest_framework.parsers import JSONParser, FormParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.user.models import Major, Degree
from api.educationMana.serializers import MajorSerializer, DegreeSerializer


class MajorViewSet(viewsets.ModelViewSet):
    """ Handle all function for Major
    """
    queryset = Major.objects.all()
    serializer_class = MajorSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)


class DegreeViewSet(viewsets.ModelViewSet):
    """ Handle all function for Degree
    """
    queryset = Degree.objects.all()
    serializer_class = DegreeSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)