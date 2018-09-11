from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.advertiseMana.views import AdvertiseViewSet


router = DefaultRouter()
router.register(r'advertise', AdvertiseViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))