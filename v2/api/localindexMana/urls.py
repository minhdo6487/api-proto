from django.conf.urls import patterns, url, include
from rest_framework import routers
from django.contrib import admin
from .views import *

admin.autodiscover()

urlpatterns = patterns('',url(r'locale/init', InitLocationViewSet.as_view()),)