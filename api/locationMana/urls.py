from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.locationMana.views import CountryViewSet, CityViewSet, DistrictViewSet, CityBookingViewSet


router = DefaultRouter()
router.register(r'location/country', CountryViewSet)
router.register(r'location/city', CityViewSet)
router.register(r'location/district', DistrictViewSet)
router.register(r'location/booking/city', CityBookingViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))