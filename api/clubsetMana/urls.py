from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.clubsetMana.views import GolfCourseClubSetsViewSet


router = DefaultRouter()
router.register(r'clubset', GolfCourseClubSetsViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))