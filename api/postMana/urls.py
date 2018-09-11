from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.postMana.views import PostViewSet, FeedViewSet


admin.autodiscover()

router = DefaultRouter()
router.register(r'post', PostViewSet)
router.register(r'feed', FeedViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))
