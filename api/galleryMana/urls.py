from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.galleryMana.views import GalleryViewSet


admin.autodiscover()

router = DefaultRouter()
router.register(r'gallery', GalleryViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))