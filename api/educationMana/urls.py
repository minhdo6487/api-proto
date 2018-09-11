from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.educationMana.views import MajorViewSet, DegreeViewSet


router = DefaultRouter()
router.register(r'profile/major', MajorViewSet)
router.register(r'profile/degree', DegreeViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))