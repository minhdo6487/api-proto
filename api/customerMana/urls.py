from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter

from api.customerMana.views import CustomerViewSet


router = DefaultRouter()
router.register(r'customer', CustomerViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))