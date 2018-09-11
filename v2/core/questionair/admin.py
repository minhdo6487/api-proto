from django.contrib import admin
import reversion

from v2.core.questionair.models import *

class QuestionairAdmin(admin.ModelAdmin):
    pass

admin.site.register(Questionair, QuestionairAdmin)

class QuestionAdmin(admin.ModelAdmin):
    pass

admin.site.register(Question, QuestionAdmin)

class QuestionChoiceAdmin(admin.ModelAdmin):
    pass

admin.site.register(QuestionChoice, QuestionChoiceAdmin)

class AnswerChoiceAdmin(admin.ModelAdmin):
    pass

admin.site.register(AnswerChoice, AnswerChoiceAdmin)
