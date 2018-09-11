from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from django.contrib import admin

from api.socialMana.views import leaderboardVs, S3Policy


admin.autodiscover()

router = DefaultRouter()
router.register(r'social/leaderboard', leaderboardVs)
policy_url = patterns('', url(r'^s3policy/', S3Policy.as_view()))

urlpatterns = policy_url + patterns('',
                                    url(r'', include(router.urls)))
