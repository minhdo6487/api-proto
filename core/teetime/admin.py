__author__ = 'toantran'
from django.contrib import admin

from .models import *


class TeeTimeAdmin(admin.ModelAdmin):
    pass


class GuestTypeAdmin(admin.ModelAdmin):
    pass

class PriceTypeAdmin(admin.ModelAdmin):
    pass

class TeeTimePriceAdmin(admin.ModelAdmin):
    list_display = ['get_teetime_date','get_teetime_time' , 'hole', 'price', 'get_default_discount', 'get_online_discount']
    list_filter = ['teetime__date', ]
    def get_teetime_date(self, obj):
    	return obj.teetime.date
    def get_teetime_time(self, obj):
    	return obj.teetime.time
    def get_online_discount(self, obj):
    	return obj.cash_discount
    def get_default_discount(self, obj):
    	return obj.online_discount
    get_online_discount.admin_order_field = 'cash_discount'
    get_online_discount.short_description = 'Online Discount'
    get_default_discount.admin_order_field = 'online_discount'
    get_default_discount.short_description = 'Default Discount'
    get_teetime_time.admin_order_field = 'teetime__time'
    get_teetime_time.short_description = 'Teetime time'
    get_teetime_date.admin_order_field = 'teetime__date'
    get_teetime_date.short_description = 'Teetime date'

class GCSettingAdmin(admin.ModelAdmin):
    pass

class GCTeeTimePriceAdmin(admin.ModelAdmin):
    pass
class GC24DiscountOnlineAdmin(admin.ModelAdmin):
    pass
class GCKeyPriceAdmin(admin.ModelAdmin):
    pass
class TeetimeFreeBuggySettingAdmin(admin.ModelAdmin):
	pass
class TeetimeShowBuggySettingAdmin(admin.ModelAdmin):
    pass
class GC24PriceByBookingAdmin(admin.ModelAdmin):
    pass
class GC24PriceByBooking_DetailAdmin(admin.ModelAdmin):
    pass
class GC24PriceByDealAdmin(admin.ModelAdmin):
    pass
class DealAdmin(admin.ModelAdmin):
    pass
class PaymentMethodSettingAdmin(admin.ModelAdmin):
    pass
class ArchivedTeetimeAdmin(admin.ModelAdmin):
    pass
admin.site.register(TeeTime, TeeTimeAdmin)
admin.site.register(GuestType, GuestTypeAdmin)
admin.site.register(PriceType, PriceTypeAdmin)
admin.site.register(TeeTimePrice, TeeTimePriceAdmin)
admin.site.register(GCSetting, GCSettingAdmin)
admin.site.register(Gc24TeeTimePrice, GCTeeTimePriceAdmin)
admin.site.register(GC24DiscountOnline, GC24DiscountOnlineAdmin)
admin.site.register(GCKeyPrice, GCKeyPriceAdmin)
admin.site.register(TeetimeFreeBuggySetting, TeetimeFreeBuggySettingAdmin)
admin.site.register(TeetimeShowBuggySetting, TeetimeShowBuggySettingAdmin)
admin.site.register(GC24PriceByBooking, GC24PriceByBookingAdmin)
admin.site.register(GC24PriceByBooking_Detail, GC24PriceByBooking_DetailAdmin)
admin.site.register(GC24PriceByDeal, GC24PriceByDealAdmin)
admin.site.register(Deal, DealAdmin)
admin.site.register(PaymentMethodSetting, PaymentMethodSettingAdmin)
admin.site.register(ArchivedTeetime, ArchivedTeetimeAdmin)