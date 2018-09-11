from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from django.contrib import admin

from api.golfcourseMana.views import GolfCourseViewSet, SettingsUnderCourseViewSet, \
    GolfCourseServicesUnderCourseViewSet, SubGolfCourseUnderCourseViewSet, \
    ServicesViewSet, GolfCourseBuggyViewSet, GolfCourseCaddyViewSet, GolfCourseClubSetsViewSet, \
    HolesUnderSubCourseViewSet, TeeTypeUnderGolfcourseViewSet, HolesTeeUnderHoleViewSet, SubGolfCourseViewSet, \
    StaffUnderCourseViewSet, GolfCourseListViewSet, GolfCourseGalleryViewSet, HolesViewSet, GolfCourseReviewViewSet

admin.autodiscover()

router = DefaultRouter()
router.register(r'golfcourse', GolfCourseViewSet)
router.register(r'golfservice', ServicesViewSet)
router.register(r'get_hole', HolesViewSet)
router.register(r'golfcourse-review', GolfCourseReviewViewSet)

gcb_router = routers.NestedSimpleRouter(router, r'golfcourse', lookup='golfcourse')
gcb_router.register(r'service', GolfCourseServicesUnderCourseViewSet, base_name='gcb_service')

gcb_router.register(r'gallery', GolfCourseGalleryViewSet, base_name='gcb_gallery')
gcb_router.register(r'buggy', GolfCourseBuggyViewSet, base_name='gcb_buggy')
gcb_router.register(r'setting', SettingsUnderCourseViewSet, base_name='gcb_setting')
gcb_router.register(r'caddy', GolfCourseCaddyViewSet, base_name='gcb_caddy')
gcb_router.register(r'clubset', GolfCourseClubSetsViewSet, base_name='gcb_clubset')
gcb_router.register(r'subgolfcourse', SubGolfCourseUnderCourseViewSet, base_name='gcb_course')
gcb_router.register(r'staff', StaffUnderCourseViewSet, base_name='gcb_staff')

sgcrouter = DefaultRouter()
sgcrouter.register(r'subgolfcourse', SubGolfCourseViewSet)
sgcrouter.register(r'subgolfcourse/(?P<scourse_pk>[^/]+)/hole',
                   HolesUnderSubCourseViewSet, base_name='golfcourse_sub_hole')
sgcrouter.register(r'subgolfcourse/(?P<scourse_pk>[^/]+)/teecolor', TeeTypeUnderGolfcourseViewSet,
                   base_name='gcb_service')

sgcb_router = routers.NestedSimpleRouter(sgcrouter, r'subgolfcourse', lookup='subgolfcourse')
sgcb_router.register(r'teecolor', TeeTypeUnderGolfcourseViewSet, base_name='gcb_service')

htrouter = DefaultRouter()
htrouter.register(r'hole', GolfCourseViewSet)
htrouter.register(
    r'hole/(?P<hole_pk>[^/]+)/teecolor',
    HolesTeeUnderHoleViewSet, base_name='golfcourse_sub_hole_tee')

gclrouter = DefaultRouter()
gclrouter.register(r'golfcourse-list', GolfCourseListViewSet)


urlpatterns = patterns('',
                       url(r'^golfcourse/id', 'api.golfcourseMana.views.golfcourse_id_by_staff'),
                       url(r'^golfcourse/(?P<golfcourse_id>[^/]+)/terms/', 'api.golfcourseMana.views.golfcourse_term'),
                       url(r'^golfcourse-list/(?P<golfcourse_id>[^/]+)/review', 'api.golfcourseMana.views.golfcourse_review'),
                       url(r'^golfcourse-list/(?P<golfcourse_id>[^/]+)/event','api.golfcourseMana.views.golfcourse_event'),
                       url(r'', include(router.urls)),
                       url(r'', include(gcb_router.urls)),
                       url(r'', include(gclrouter.urls)),
                       url(r'', include(sgcrouter.urls)),
                       url(r'', include(htrouter.urls)))