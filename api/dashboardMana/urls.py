from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin
admin.autodiscover()

router = DefaultRouter()
urlpatterns = patterns('',
                        url(r'^dashboard-summary', 'api.dashboardMana.views.get_dashboard_summary'),
                        url(r'^get-activities', 'api.dashboardMana.views.get_activities'),
                        )