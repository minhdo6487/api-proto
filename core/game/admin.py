__author__ = 'toantran'
from django.contrib import admin

from .models import EventMember, Game


class EventMemberAdmin(admin.ModelAdmin):
    pass

class GameAdmin(admin.ModelAdmin):
    # search_fields = ['is_finish']
    # list_display = ('golfcourse', 'event_member', 'active', 'is_finish')
    pass


admin.site.register(EventMember, EventMemberAdmin)
admin.site.register(Game, GameAdmin)