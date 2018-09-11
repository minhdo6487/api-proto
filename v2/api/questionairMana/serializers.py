from rest_framework import serializers
from v2.core.questionair.models import *

class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = QuestionChoice
        ordering = ('-id',)

class QuestionSerializer(serializers.ModelSerializer):
    question_choice = QuestionChoiceSerializer(many=True,source='question_choice')

    class Meta(object):
        model = Question
        ordering = ('-id',)

class QuestionairSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(many=True,source='question')

    class Meta(object):
        model = Questionair
        ordering = ('-id',)

class AnswerUserSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = AnswerChoice
        fields = ('question', 'user', 'choice', 'text')
        ordering = ('-id',)
    def __update_or_create__(self, data):
        kwargs = {'question_id': int(data['question']), 'user_id': int(data['user'])}
        my_object, created = AnswerChoice.objects.get_or_create(**kwargs)
        my_object.choice_id = int(data['choice']) if data['choice'] else None
        my_object.text = data['text']
        my_object.save(update_fields=['choice','text'])
    def update_or_create(self):
        data = self.data.copy()
        data = data if isinstance(data, list) else [data]
        [self.__update_or_create__(d) for d in data]
