from django.conf.urls import patterns, include, url
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from django.contrib import admin

from api.gameMana.views import GameViewSet, ResultRecordUnderGameViewSet, ScoreViewSet, GameFlightViewSet
from utils.rest import routers as custom_routers


admin.autodiscover()

router = DefaultRouter()
router.register(r'game', GameViewSet)
router.register(r'game-flight', GameFlightViewSet)
score_router = custom_routers.CreateRouter()
score_router.register(r'score', ScoreViewSet)
g_router = routers.NestedSimpleRouter(router, r'game', lookup='game')
g_router.register(r'score', ResultRecordUnderGameViewSet, base_name='g_score')

hdcp_urls = patterns('', url(r'^game/hdcp-index/$', 'api.gameMana.views.get_handicap_index'))

reser_urls = patterns('', url(r'^game/maps/$', 'api.gameMana.views.get_maps'))
compare_urls = patterns('', url(r'^game/compare/$', 'api.gameMana.views.compare'))
get_min_urls = patterns('', url(r'^game/get_min_list/$', 'api.gameMana.views.get_mini_list'))
cacul_urls = patterns('', url(r'^game/caculate/$', 'api.gameMana.views.cal_aver_par'))
distri_urls = patterns('', url(r'^game/distribute/$', 'api.gameMana.views.score_distribute'))
finish_game_url = patterns('', url(r'game/finish/$', 'api.gameMana.views.finish_game'))
cancel_game_url = patterns('', url(r'game/cancel/$', 'api.gameMana.views.cancel_game'))
delete_game_url = patterns('', url(r'game/delete/$', 'api.gameMana.views.delete_list_game'))
quit_game_url = patterns('', url(r'game/quit/(?P<game_id>[0-9]+)', 'api.gameMana.views.quit_game'))
resume_game_url = patterns('', url(r'game/resume/(?P<game_id>[0-9]+)', 'api.gameMana.views.resume_game'))
game_analysis = patterns('', url(r'^game/analysis/(?P<game_id>[0-9]+)', 'api.gameMana.views.game_analysis'))
game_confirm = patterns('', url(r'^game/confirm/(?P<game_id>[0-9]+)', 'api.gameMana.views.confirm_game'))
urlpatterns = resume_game_url + quit_game_url + game_confirm + game_analysis + delete_game_url + cancel_game_url + finish_game_url + compare_urls + hdcp_urls + reser_urls + distri_urls + get_min_urls + cacul_urls + patterns(
    '',
    url(r'',
        include(
            router.urls)),
    url(r'',
        include(
            g_router.urls)),
    url(r'',
        include(
            score_router.urls)), )