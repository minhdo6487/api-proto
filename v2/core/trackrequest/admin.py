from django.contrib import admin
import reversion

from v2.core.trackrequest.models import TrackingRequest

class TrackingRequestAdmin(admin.ModelAdmin):
    raw_id_fields = ['user']
    list_display = ['time','user','ip', 'method', 'path', 'response','referer','user_agent','language']
    list_filter = ['user__id', 'path']
admin.site.register(TrackingRequest, TrackingRequestAdmin)