from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'', include('v2.api.questionairMana.urls')),
    url(r'', include('v2.api.localindexMana.urls')),
    url(r'', include('v2.api.chatserviceMana.urls')),
    url(r'', include('v2.api.notify.urls')),
    url(r'', include('v2.api.gc_eventMana.urls')),
    url(r'', include('v2.api.subgameMana.urls')),
)
