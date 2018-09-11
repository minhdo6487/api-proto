from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.playstayMana.views import ParentPackageTourViewSet, HotelViewSet, PackageTourReviewViewSet, BookedPackageViewSet

router = DefaultRouter()
router.register(r'package-tour', ParentPackageTourViewSet)
router.register(r'hotel', HotelViewSet)
router.register(r'package-tour-review', PackageTourReviewViewSet)
router.register(r'package-tour-book', BookedPackageViewSet)
urlpatterns = patterns('',
                       url(r'^package-tour/(?P<pk>[^/]+)/review',
                           'api.playstayMana.views.get_package_tour_review'),
                       url(r'', include(router.urls)))