from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from api.dealMana.views import GolfCourseTimeRangeViewSet,GolfCourseDealViewSet,GolfCourseDealTeeTimeViewSet,ImportDeal,DealPerGC
from api.dealMana.views import GolfCourseTimeRangeDetailSet, GolfCourseDealBookingDetail, GolfCourseDealBookingViewSet, GolfCourseDealDetailSet
urlpatterns = patterns('',
                        url(r'^deal/timerange/$', GolfCourseTimeRangeViewSet.as_view()),
                        url(r'^deal/timerange/(?P<pk>[0-9]+)/$', GolfCourseTimeRangeDetailSet.as_view()),
                        url(r'^deal/bookingtime/$', GolfCourseDealBookingViewSet.as_view()),
                        url(r'^deal/bookingtime/(?P<pk>[0-9]+)/$', GolfCourseDealBookingDetail.as_view()),
                        url(r'^deal/teetime/$', GolfCourseDealTeeTimeViewSet.as_view()),
                        url(r'^deal/$', GolfCourseDealViewSet.as_view()),
                        url(r'^deal/(?P<pk>[0-9]+)/$', GolfCourseDealDetailSet.as_view()),
                        url(r'^importdeal', ImportDeal.as_view()),
                        url(r'^deal/golfcourse$', DealPerGC.as_view())
                      )
