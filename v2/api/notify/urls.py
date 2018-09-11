
from django.contrib import admin
from django.conf.urls import url, include, patterns
from rest_framework.routers import DefaultRouter

from . import views

admin.autodiscover()
campaign_router = DefaultRouter()
campaign_router.register(r'campaigns', views.PushNotificationCampaignViewSet)
campaign_router.register(r'logs', views.NotifyLogViewSet)

urlpatterns = patterns(
    '',
    url(r'^notify/count-users/', views.count_total_by_filters),
    url(r'^notify/campaigns/history/', views.CampHistoryViewSet.as_view({'get': 'list'})),
    url(r'^notify/cron/', views.cron_push_schedules),
    url(r'^notify/', include(campaign_router.urls)),
)
