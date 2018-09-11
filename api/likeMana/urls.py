from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.likeMana.views import LikeViewSet, ViewViewSet


admin.autodiscover()

router = DefaultRouter()
router.register(r'like', LikeViewSet)
router.register(r'view', ViewViewSet)
urlpatterns = patterns('',
                       url(r'', include(router.urls)))