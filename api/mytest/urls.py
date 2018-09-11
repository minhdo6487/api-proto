from django.conf.urls import patterns, url
from . import views

urlpatterns = patterns(
  '',
  url('^/hello$', views.hello),
  url('^/hello-auth$', views.hello_auth),
)
