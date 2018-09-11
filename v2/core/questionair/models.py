# -*- coding: utf-8 -*-
import datetime, json, django
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from v2.utils.code import MODULE_QUESTIONAIR, TYPE_QUESTION
from .managers import *
from .utils import *
try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

class Questionair(models.Model):
    package_name = models.CharField(max_length=255)
    referer_object = models.CharField(max_length=255,blank=True,null=True,choices=MODULE_QUESTIONAIR,default='UserProfile')
    modified_at = models.DateTimeField(default=now, db_index=True, editable=False)
    objects = QuestionairManager()
    def __str__(self):
        return str(self.id) + '--' + self.package_name + '--' + self.referer_object

class Question(models.Model):
    package = models.ForeignKey(Questionair, related_name='question')
    question_vi = models.CharField(max_length=8000)
    question_en = models.CharField(max_length=8000)
    code_name = models.CharField(max_length=8000)
    type_question = models.CharField(max_length=255, blank=True, null=True, default='input', choices=TYPE_QUESTION)

    def __str__(self):
        return self.question_en

class QuestionChoice(models.Model):
    question = models.ForeignKey(Question, related_name='question_choice')
    choice_vi = models.CharField(max_length=8000)
    choice_en = models.CharField(max_length=8000)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.question.question_en + ': ' + self.choice_en

class AnswerChoice(models.Model):
    question = models.ForeignKey(Question, related_name='question_answer')
    user = models.ForeignKey(User, related_name='user_answer_choice')
    choice = models.ForeignKey(QuestionChoice, related_name='answer_choice', null=True, blank=True)
    text = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.question.question_en + ': ' + (self.choice.choice_en if self.choice else self.text)


post_save.connect(update_user_profile, sender=AnswerChoice)