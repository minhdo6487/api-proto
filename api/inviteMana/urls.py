from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.inviteMana.views import InvitationViewSet, DecidedView, InvitedPeopleViewSet, DecidedFromMailView


router = DefaultRouter()
router.register(r'invitation', InvitationViewSet)
router.register(r'invited-people', InvitedPeopleViewSet)
urlpatterns = patterns('',
                       url(r'^invitation/decided/$', DecidedView.as_view()),
                       url(r'^invitation/decided/(?P<type>[0-9A-Za-z]+)/(?P<user_id>[0-9A-Za-z]+)/$',
                           DecidedFromMailView.as_view()),
                       url(r'', include(router.urls)))
