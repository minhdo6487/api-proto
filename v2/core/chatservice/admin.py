from django.contrib import admin
import reversion

from .models import *

class UserChatPresenceAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    readonly_fields = ('modified_at',)

admin.site.register(UserChatPresence, UserChatPresenceAdmin)