from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.noticeMana.views import NoticeViewSet


router = DefaultRouter()
router.register(r'notice', NoticeViewSet)
calendar_url = patterns('', url(r'^calendar/$', 'api.noticeMana.views.get_calendar'))
update_list_url = patterns('', url(r'^update-list-notice/$', 'api.noticeMana.views.update_list_notice'))
delete_list_url = patterns('', url(r'^delete-list-notice/$', 'api.noticeMana.views.delete_list_notice'))
send_push_notification = patterns('', url(r'^push-notification/$', 'api.noticeMana.views.send_push_notification'))
send_push_event_notification = patterns('', url(r'^push-notification/event/$', 'api.noticeMana.views.send_push_event_notification'))
send_push_event_notification_v2 = patterns('', url(r'^push-notification/eventv2/$', 'api.noticeMana.views.send_push_event_notification_v2'))
craw_teetime = patterns('', url(r'^task/teetime$', 'api.noticeMana.views.crawl_teetime'))
higher_price_url = patterns('', url(r'^task/higher_price$', 'api.noticeMana.views.send_email_lower_price'))
crawl_currency = patterns('', url(r'^task/currency$', 'api.noticeMana.views.crawl_currency_vietcombank'))
get_currency = patterns('', url(r'^task/get_currency$', 'api.noticeMana.views.get_currency_vietcombank'))
urlpatterns = higher_price_url + craw_teetime + send_push_event_notification+send_push_event_notification_v2 + delete_list_url + send_push_notification  +update_list_url + calendar_url + crawl_currency + get_currency+patterns('',
                                                        url(r'', include(router.urls)))