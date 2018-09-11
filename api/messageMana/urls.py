from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.messageMana.views import MessageViewSet


router = DefaultRouter()
router.register(r'message', MessageViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))