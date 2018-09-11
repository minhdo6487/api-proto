from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.teetimeMana.views import TeeTimeViewSet, TeeTimePriceViewSet, GuestTypeViewSet, PriceTypeViewSet, PriceMatrixLogViewSet,\
								HolidayViewSet, TeetimeImport, TeetimeDel, RecurringTeetimeViewSet


admin.autodiscover()

router = DefaultRouter()
router.register(r'teetime/price', TeeTimePriceViewSet)
router.register(r'teetime', TeeTimeViewSet)


router.register(r'price-matrix', PriceMatrixLogViewSet)

router.register(r'holiday', HolidayViewSet)
router.register(r'guest-type', GuestTypeViewSet)
router.register(r'price-type', PriceTypeViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))

update_discount_url = patterns('', url(r'^update-teetime-discount/$', 'api.teetimeMana.views.update_teetime_discount'))
update_discount_url = patterns('', url(r'^archive-teetime/$', 'api.teetimeMana.views.archived_teetime'))
import_teetime_recurring = patterns('', url(r'^import_teetime_recurring/$', 'api.teetimeMana.views.import_teetime_recurring'))
urlpatterns = update_discount_url + import_teetime_recurring+patterns('',
                       url(r'', include(router.urls)),
                       url(r'^teetime-import/$', TeetimeImport.as_view()),
					   url(r'^teetime-del', TeetimeDel.as_view()),
					   url(r'^recurring/$', RecurringTeetimeViewSet.as_view()))
