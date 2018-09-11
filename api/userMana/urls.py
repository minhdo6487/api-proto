from django.conf.urls import patterns, url, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework import routers
from django.contrib import admin

from api.userMana.views import UserViewSet, ProfileView, UserSettingView, ChangePassView, FindEmailViewSet, \
    UserGameViewSet, UserActivityViewset, InvoiceViewSet, NewFindEmailViewSet, GroupchatViewSet, UserPrivacyViewSet
from utils.rest import routers as addedrouters
admin.autodiscover()

router = routers.DefaultRouter()
router.register(r'user', UserViewSet)
router.register(r'invoice', InvoiceViewSet)
router.register(r'activity', UserActivityViewset)


router2 = addedrouters.GroupchatRouter()
router2.register(r'groupchat', GroupchatViewSet)
router2.register(r'privacy', UserPrivacyViewSet)

get_urls = patterns('', url(r'^user/get_group/$', 'api.userMana.views.get_group'))
update_user_version = patterns('', url(r'^user/version', 'api.userMana.views.update_user_version'))
get_username_url = patterns('', url(r'^user/get_username/$', FindEmailViewSet.as_view()))
new_get_username_url = patterns('', url(r'^user/get_username/v2$', NewFindEmailViewSet.as_view()))
urlpatterns = get_username_url + get_urls + update_user_version + patterns('',url(r'', include(router.urls))) + patterns('',url(r'', include(router2.urls)))

addedrouter = addedrouters.GetAndUpdateRouter()
addedrouter.register(r'profile/setting', UserSettingView, base_name='profilesetting')
addedrouter.register(r'profile', ProfileView, base_name='profile')

user_game_urls = patterns('', url(r'^user/(?P<user_id>[^/]+)/games', UserGameViewSet.as_view()))
user_location_url = patterns('', url(r'^user/location', 'api.userMana.views.track_location'))

clean_activity_url = patterns('', url(r'^activity/clean', 'api.userMana.views.clean_up_activities'))
urlpatterns += new_get_username_url+ clean_activity_url + user_location_url +user_game_urls + format_suffix_patterns(patterns('',
                                               url(r'profile/password/', ChangePassView.as_view()),
                                               url(r'', include(addedrouter.urls))))
