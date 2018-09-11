from django.conf.urls import patterns, url, include
from rest_framework import routers
from django.contrib import admin
from .views import *

admin.autodiscover()
router = routers.DefaultRouter()
router.register(r'chatservice/statistic', UserChatPresenceViewSet, base_name='Chatservice Statistic')
urlpatterns = patterns('',
					url(r'chatservice/summary', UserChatStatisticViewSet.as_view(), name='chatservice_summary'),
					url(r'', include(router.urls)))