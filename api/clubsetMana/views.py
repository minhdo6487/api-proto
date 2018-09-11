from rest_framework.parsers import JSONParser, FormParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.golfcourse.models import ClubSets
from api.clubsetMana.serializers import ClubSetsSerializer


class GolfCourseClubSetsViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = ClubSets.objects.all()
    serializer_class = ClubSetsSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)