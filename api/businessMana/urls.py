from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
# from api.businessMana.views import BusinessAreaViewSet, BusinessSubAreaViewSet
#
router = DefaultRouter()
# router.register(r'profile/businessarea', BusinessAreaViewSet)
# router.register(r'profile/businesssubarea', BusinessSubAreaViewSet)
#
urlpatterns = patterns('',
                       url(r'', include(router.urls)))