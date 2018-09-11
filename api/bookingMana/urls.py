from django.conf.urls import patterns, url, include
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.bookingMana.views import MyBookingDetailViewSet, MyBookingViewSet, BookingGolfcourseViewSet, BookingUpdateViewSet, BookingReportViewSet,GetTeetimes, HoldTeetimes, BookingView, BookedTeeTimeViewSet, BookedPartnerViewSet, CheckPriceView, BookingSettingViewSet, BookingCancellationViewSet, ReportViewSet, \
								BookingGCViewSet, BookingSuccessViewSet, CancelReportViewSet,PaymentNotify, AutoCheckPayment, BookingRequest
from django.conf import settings

admin.autodiscover()

router = DefaultRouter()

router.register('booking/teetime', BookedTeeTimeViewSet, base_name='teetime')
router.register('booking/partner', BookedPartnerViewSet)
router.register(r'booking/setting', BookingSettingViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)),
                       url(r'^booking/$', GetTeetimes.as_view()),
                       url(r'success-booking/(?P<key>[^/]+)/', BookingSuccessViewSet.as_view()),
                       url(r'async-payment/', AutoCheckPayment.as_view()),
                       url(r'^comission/$', ReportViewSet.as_view()),
                       url(r'^cancelreport/$', CancelReportViewSet.as_view()),
                       url(r'^my-booking/$', MyBookingViewSet.as_view()),
                       url(r'my-booking/(?P<key>[^/]+)/', MyBookingDetailViewSet.as_view()),
                       url(r'^booking/hold$', HoldTeetimes.as_view()),
                       url(r'^booking/golfcourse', BookingGolfcourseViewSet.as_view()),
                       url(r'^booking/report$', BookingReportViewSet.as_view()),
                       url(r'^booking/gcadmin$', BookingGCViewSet.as_view()),
                       url(r'^booking/update', BookingUpdateViewSet.as_view()),
                       # url(r'^booking/reset$', BookingResetViewSet.as_view()),
                       url(r'^booking/payment-notify/$', PaymentNotify.as_view()),
                       url(r'^booking/payment/$', BookingView.as_view()),
                       url(r'^booking/price/$', CheckPriceView.as_view()),
                       url(r'^bookingrequest/(?P<key>[^/]+)/', BookingRequest.as_view()),
                       url(r'cancel-teetime/(?P<key>[^/]+)/', BookingCancellationViewSet.as_view()))
check_voucher = patterns('', url(r'^booking/check-voucher$', 'api.bookingMana.views.check_valid_voucher'))
get_gc24_price = patterns('', url(r'^booking/get-gc24price$', 'api.bookingMana.views.get_gc24_price'))
request_invoice = patterns('', url(r'^booking/invoice$', 'api.bookingMana.views.request_invoice'))
send_thankyou_email = patterns('', url(r'^booking/thankyou$', 'api.bookingMana.views.send_after_booking_email'))
update_booking_note = patterns('', url(r'^booking/note$', 'api.bookingMana.views.update_booking_note'))
urlpatterns += check_voucher
urlpatterns += get_gc24_price
urlpatterns += request_invoice
urlpatterns += send_thankyou_email
urlpatterns += patterns('',
        url(r'^media/qr_codes/(?P<path>.*)$',
            'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT + 'qr_codes/', }),
    )