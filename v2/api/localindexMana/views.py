# -*- coding: utf-8 -*-
from rest_framework import (mixins, 
                            viewsets,
                            parsers,
                            status,
                            views)
from rest_framework.response import Response
from .tasks import *
from .serializers import *

class InitLocationViewSet(views.APIView):
    @staticmethod
    def get(request, key=None):
        init_location_by_GPS()
        return Response({'status':200, 'code':'OK', 'detail':'OK'}, status=200)