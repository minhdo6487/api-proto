from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.golfcourseeventMana.views import GolfCourseEventViewSet, EventMemberViewSet, ListMember, \
    GroupEventViewSet, EventPrizeViewSet, AdvertiseEventViewSet, LeaderBoardEventViewSet, PublishEventViewSet


admin.autodiscover()

router = DefaultRouter()
router.register(r'event', GolfCourseEventViewSet)  # get all events
router.register(r'event-member', EventMemberViewSet)
router.register(r'golfcourse-event', LeaderBoardEventViewSet)  # get leaderboard events
router.register(r'coming-event', AdvertiseEventViewSet)  # get advertised events
router.register(r'group-event', GroupEventViewSet)
router.register(r'event-prize', EventPrizeViewSet)
router.register(r'publish-event', PublishEventViewSet)
craw_member_urls = patterns('', url(r'^ehandicap-member/$', ListMember.as_view()))
join_url = patterns('', url(r'event/join/$', 'api.golfcourseeventMana.views.join_event'))
register_url = patterns('', url(r'event/register/$', 'api.golfcourseeventMana.views.register_event'))
my_event_url = patterns('', url(r'event/me/$', 'api.golfcourseeventMana.views.get_my_event'))
delete_member_url = patterns('', url(r'member/delete/$', 'api.golfcourseeventMana.views.delete_list_member'))
urlpatterns = delete_member_url + register_url + my_event_url + join_url + craw_member_urls + patterns('',
                                                                                   url(r'', include(router.urls)))