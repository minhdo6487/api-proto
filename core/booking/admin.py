from django.contrib import admin
import datetime

from django.db import models
from django import forms

from .models import *
from core.golfcourse.models import GolfCourse
from core.teetime.models import TeeTime

from core.booking.models import BookedPartner, BookedTeeTime, BookedPartner_GolfcourseEvent
from core.game.models import EventMember
from core.customer.models import Customer
from core.game.admin import EventMemberAdmin

from v2.core.bookinghis.models import BookedGolfcourseEvent_History

class VoucherAdmin(admin.ModelAdmin):
    pass


class BookedTeeTimeAdmin(admin.ModelAdmin):
    # raw_id_fields = ('teetime','golfcourse',)
    pass


class BookedTeeTime_HistoryAdmin(admin.ModelAdmin):
    pass


class BookingSettingAdmin(admin.ModelAdmin):
    pass


class BookedPartnerAdmin(admin.ModelAdmin):
    pass


class GC24BookingVendorAdmin(admin.ModelAdmin):
    pass


class PayTransactionStoreAdmin(admin.ModelAdmin):
    pass


class BookedPayonlineLinkAdmin(admin.ModelAdmin):
    readonly_fields = ('paymentLink', 'paymentStatus')


class EventMemberAdminForm(forms.ModelForm):
    class Meta:
        model = EventMember
        widgets = {
            'member': forms.RadioSelect
        }
        fields = '__all__'


# class TagCatAdmin(admin.ModelAdmin):
#     form = MyTagCatAdminForm

class BookedGolfcourseEventAdmin(admin.ModelAdmin):
    search_fields = ['payment_type', 'status']
    list_display = ('member', 'total_cost', 'book_type', 'payment_type', 'status')


# form = EventMemberAdminForm

class CloneBookedTeeTime(BookedTeeTime):
    class Meta:
        proxy = True

    def __unicode__(self):
        return self.teetime, self.golfcourse, self.status



class BookedPartnerInline(admin.StackedInline):
    model = BookedPartner
    extra = 0



class EventMemberInline(admin.StackedInline):
    model = EventMember
    extra = 1


class BookedTeetimeTestAdmin(BookedTeeTimeAdmin):
    # list_display = ('bookedteetime_id', 'customer_id','user_id')
    list_display = ('teetime', 'golfcourse', 'status')

    # fields = ['customer', 'status']

    fieldsets = [
        ('Teetime', {'fields': ['teetime']}),
        ('Status', {'fields': ['status']}),
    ]
    inlines = [BookedPartnerInline]



class BookedGolfcourseEvent_HistoryAdmin(admin.ModelAdmin):
    pass

class BookedPartner_GolfcourseEvent_Admin(admin.ModelAdmin):
    search_fields = ['customer__email']
    list_display = ('bookedgolfcourse', 'get_event_id', 'customer', 'get_custome_name', 'get_customer_phone')
    list_filter =  ('bookedgolfcourse__member__event', 'bookedgolfcourse__member',)

    def get_custome_name(self, obj):
        return obj.customer.name if obj.customer else ""

    def get_customer_phone(self, obj):
        return obj.customer.phone_number if obj.customer else ""

    def get_event_id(self, obj):
        return obj.bookedgolfcourse.member.event.name

    get_custome_name.short_description = 'Customer Name'  # Renames column head
    get_customer_phone.short_description = 'Customer Phone'  # Renames column head
    get_event_id.short_description = 'Event'  # Renames column head


admin.site.register(Voucher, VoucherAdmin)
admin.site.register(BookedTeeTime, BookedTeeTimeAdmin)
admin.site.register(BookedTeeTime_History, BookedTeeTime_HistoryAdmin)
admin.site.register(BookingSetting, BookingSettingAdmin)
admin.site.register(BookedPartner, BookedPartnerAdmin)
admin.site.register(GC24BookingVendor, GC24BookingVendorAdmin)
admin.site.register(PayTransactionStore, PayTransactionStoreAdmin)
admin.site.register(BookedPayonlineLink, BookedPayonlineLinkAdmin)
admin.site.register(BookedGolfcourseEvent, BookedGolfcourseEventAdmin)

admin.site.register(CloneBookedTeeTime, BookedTeetimeTestAdmin)

admin.site.register(BookedGolfcourseEvent_History, BookedGolfcourseEvent_HistoryAdmin)

admin.site.register(BookedPartner_GolfcourseEvent, BookedPartner_GolfcourseEvent_Admin)
