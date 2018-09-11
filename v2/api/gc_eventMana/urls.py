from django.conf.urls import patterns, url, include
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from v2.api.gc_eventMana.views import MyGC_EventViewSet, MyGC_Event_DetailViewSet, MyBookingViewSet_v2, MyBookingDetailViewSet_v2, cron_send_email_survey


from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
                       url(r'^my-gc-event/$', MyGC_EventViewSet.as_view()),
                       url(r'^my-gc-event/(?P<key>[^/]+)/', MyGC_Event_DetailViewSet.as_view()),
                       url(r'^my-booking/$', MyBookingViewSet_v2.as_view()),
                       url(r'my-booking/(?P<key>[^/]+)/', MyBookingDetailViewSet_v2.as_view()),
                       url(r'send-email-survey', cron_send_email_survey)
                       )
