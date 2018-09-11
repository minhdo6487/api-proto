from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from django.contrib import admin

from v2.api.subgameMana.views import GameViewSet_v2, GameViewSetCal_v2,split_sub #, ResultRecordUnderGameViewSet, ScoreViewSet, GameFlightViewSet
from api.gameMana.views import ResultRecordUnderGameViewSet, ScoreViewSet, GameFlightViewSet
from utils.rest import routers as custom_routers


admin.autodiscover()

router = DefaultRouter()
router.register(r'game', GameViewSet_v2)

patterns('', url(r'^game/maps/$', 'api.gameMana.views.get_maps'))

# GameViewSetCal_v2
gccrouter = DefaultRouter()
gccrouter.register(r'analysis_cal', GameViewSetCal_v2)

urlpatterns =  patterns(
                        '',
                        url(r'', include(router.urls)),
                        url(r'', include(gccrouter.urls)),

                        url(r'^game/find_next_sub/(?P<golfcourse_id>[0-9]+)', 'v2.api.subgameMana.views.find_next_subgame'),
                        url(r'^game/split_sub/(?P<golfcourse_id>[0-9]+)', 'v2.api.subgameMana.views.split_sub'),
                        url(r'^game/find_new_sub/(?P<golfcourse_id>[0-9]+)', 'v2.api.subgameMana.views.find_new_sub'),
                        )