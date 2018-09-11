from rest_framework.urlpatterns import format_suffix_patterns
from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.forumMana import views


admin.autodiscover()

urlpatterns = [
    url(r'^forum/report$', views.Report.as_view()),
    url(r'^forum/$', views.Forum.as_view()),
]

router = DefaultRouter()
router.register(r'forum/acticle', views.PostViewSet)
router.register(r'forum/new_comment', views.CommentViewSet)

urlpatterns = format_suffix_patterns(urlpatterns) + patterns('',
                                                             url(r'', include(router.urls)))