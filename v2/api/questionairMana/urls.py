from django.conf.urls import patterns, url, include
from rest_framework import routers
from django.contrib import admin
from .views import *

admin.autodiscover()
router = routers.DefaultRouter()
router.register(r'survey/questionair', ListQuestionairViewSet, base_name='Questionair')
router.register(r'survey/answer', AnswerChoiceViewSet, base_name='AnswerChoice')

urlpatterns = patterns('',url(r'', include(router.urls)))