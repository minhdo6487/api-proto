from rest_framework.parsers import JSONParser, FormParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from core.location.models import Country, City, District
from api.locationMana.serializers import CountrySerializer, CitySerializer, DistrictSerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """ Handle all function for Country
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """ Handle all function for City
    """
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        country = request.GET.get('country', None)
        if country:
            city = City.objects.filter(country__short_name=country)
            serializer = CitySerializer(city)
            return Response(serializer.data, status=200)
        return super().list(request, *args, **kwargs)

class CityBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """ Handle all function for City
    """
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        country = request.GET.get('country', None)
        if country:
            city = City.objects.filter(country__short_name=country, golfcourse__teetime__isnull=False).distinct()
        else:
            city = City.objects.filter(golfcourse__teetime__isnull=False).distinct()
        serializer = CitySerializer(city)
        return Response(serializer.data, status=200)


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """ Handle all function for District
    """
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser, FormParser,)


