__author__ = 'toantran'
from django.conf.urls import patterns, url

urlpatterns = patterns('',
                       url(r'^subcribe/$', 'api.realtimeMana.views.subcribe'),
                       url(r'^unsubcribe/$', 'api.realtimeMana.views.unsubcribe'))