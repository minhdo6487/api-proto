from django.contrib import admin
from rest_framework.routers import DefaultRouter
from django.conf.urls import patterns, include, url
from api.friendMana.views import FriendViewSet, FriendViewV2

admin.autodiscover()
router = DefaultRouter()
router.register(r'friend', FriendViewSet)

get_friend_url = patterns('', url(r'^friend/find_friend', 'api.friendMana.views.get_friend'))
track_post_friend_url = patterns('', url(r'^friend/track-post', 'api.friendMana.views.track_post_friend'))
unfriend = patterns('', url(r'^unfriend/(?P<pk>[^/]+)', 'api.friendMana.views.unfriend'))
urlpatterns = track_post_friend_url + \
              get_friend_url + \
              unfriend + \
              patterns('', url(r'', include(router.urls))) + \
              patterns('', url(r'^v2/friend', FriendViewV2.as_view()))

