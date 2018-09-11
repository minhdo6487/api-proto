from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.commentMana.views import CommentViewSet


admin.autodiscover()

router = DefaultRouter()
router.register(r'comment', CommentViewSet)

urlpatterns = patterns('',
                       url(r'', include(router.urls)))