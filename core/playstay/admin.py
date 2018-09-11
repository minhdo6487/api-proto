from django.contrib import admin
from .models import Hotel, HotelImages, HotelRoom, PackageTour, Services, PackageTourServices, PackageTourFee, PackageHotelRoomFee, PackageGolfcourseFee, \
    PackageAdditionalFee, PackageGolfCourse, ParentPackageTour, HotelGolfcourseDistance


# Register your models here.
class HotelAdmin(admin.ModelAdmin):
    pass


admin.site.register(Hotel, HotelAdmin)

# Register your models here.
class HotelImagesAdmin(admin.ModelAdmin):
    pass


admin.site.register(HotelImages, HotelImagesAdmin)

# Register your models here.
class HotelRoomAdmin(admin.ModelAdmin):
    pass


admin.site.register(HotelRoom, HotelRoomAdmin)

# Register your models here.
class PackageGolfCourseAdmin(admin.ModelAdmin):
    pass


admin.site.register(PackageGolfCourse, PackageGolfCourseAdmin)
# Register your models here.
class ParentPackageTourAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_destination', 'display_price', 'date_created')


admin.site.register(ParentPackageTour, ParentPackageTourAdmin)
# Register your models here.
class PackageTourAdmin(admin.ModelAdmin):
    pass
    # list_display = ('id', 'title', 'from_date', 'to_date','day', 'is_destination', 'display_price')


admin.site.register(PackageTour, PackageTourAdmin)

# Register your models here.
class ServicesAdmin(admin.ModelAdmin):
    pass


admin.site.register(Services, ServicesAdmin)


# Register your models here.
class PackageTourServicesAdmin(admin.ModelAdmin):
    pass


admin.site.register(PackageTourServices, PackageTourServicesAdmin)

# Register your models here.
class PackageTourFeeAdmin(admin.ModelAdmin):
    pass


admin.site.register(PackageTourFee, PackageTourFeeAdmin)

# Register your models here.
class PackageHotelRoomFeeAdmin(admin.ModelAdmin):
    pass


admin.site.register(PackageHotelRoomFee, PackageHotelRoomFeeAdmin)

# Register your models here.
class PackageGolfcourseFeeAdmin(admin.ModelAdmin):
    pass


admin.site.register(PackageGolfcourseFee, PackageGolfcourseFeeAdmin)

# Register your models here.
class PackageAdditionalFeeAdmin(admin.ModelAdmin):
    pass


admin.site.register(PackageAdditionalFee, PackageAdditionalFeeAdmin)


class HotelGolfcourseDistanceAdmin(admin.ModelAdmin):
    pass


admin.site.register(HotelGolfcourseDistance, HotelGolfcourseDistanceAdmin)