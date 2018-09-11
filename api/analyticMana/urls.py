from django.conf.urls import patterns, url


urlpatterns = patterns('', url(r'^analytic/player/$', 'api.analyticMana.views.get_analytic_player'),
                       url(r'^analytic/booking/day/$', 'api.analyticMana.views.get_analytic_booking_by_day'),
                       url(r'^analytic/booking/$', 'api.analyticMana.views.get_analytic_booking'),
                       url(r'^analytic/booking/week/$', 'api.analyticMana.views.get_analytic_booking_by_week'),
                       url(r'^analytic/booking/booked/$', 'api.analyticMana.views.get_booking_report'),
                       url(r'^analytic/booking/cancel/$', 'api.analyticMana.views.get_booking_cancel'),
                       url(r'^analytic/booking/rp/$', 'api.analyticMana.views.get_booking_rp'),
                       url(r'^analytic/booking/gcar/$', 'api.analyticMana.views.get_booking_gcar'),
                       url(r'^analytic/booking/vendor/$', 'api.analyticMana.views.get_booking_vendor'),)
