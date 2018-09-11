from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from api.buggyMana.views import GolfCourseBuggyViewSet, GolfCourseCaddyViewSet
router = DefaultRouter()
urlpatterns = patterns('',
                        url(r'^buggy/$', GolfCourseBuggyViewSet.as_view()),
                        url(r'^caddy/$', GolfCourseCaddyViewSet.as_view()),)