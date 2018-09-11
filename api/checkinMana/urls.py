from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.checkinMana.views import CheckinViewSet


router = DefaultRouter()
router.register(r'checkin', CheckinViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))