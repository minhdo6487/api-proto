from django.contrib import admin
import reversion

from v2.core.eventqueue.models import *

class EventQueueAdmin(admin.ModelAdmin):
    pass

admin.site.register(EventQueue, EventQueueAdmin)