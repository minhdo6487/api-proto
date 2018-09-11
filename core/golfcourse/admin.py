from django.contrib import admin
from import_export.widgets import CharWidget
from import_export import fields

from core.golfcourse.models import GolfCourse, SubGolfCourse, Hole, TeeType, HoleTee, GolfCourseEvent, ClubSets, \
    GolfCourseStaff, GolfCourseSetting, GolfCourseEventAdvertise, GolfCourseBookingSetting, GolfCourseEventMoreInfo, \
    GolfCourseEventSchedule, GolfCourseEventBanner, GolfCourseEventPriceInfo, GolfCourseEventHotel

# class GolfCourseAdmin(admin.ModelAdmin):
# pass
# admin.site.register(GolfCourse, GolfCourseAdmin)
from import_export import resources
from import_export.admin import ImportExportModelAdmin


class SubGolfCourseResource(resources.ModelResource):
    par = fields.Field(column_name='par')
    yard = fields.Field(column_name='yard', widget=CharWidget)
    slope = fields.Field(column_name='slope')
    rating = fields.Field(column_name='rating')
    hole = fields.Field(column_name='hole')

    class Meta:
        model = SubGolfCourse

    def dehydrate_golfcourse(self, subgc):
        return '%s' % (subgc.golfcourse.name)

    def dehydrate_par(self, subgc):
        for h in subgc.hole.all():
            if not h.par:
                return 'No'
        return 'Yes'

    def dehydrate_yard(self, subgc):
        for h in subgc.hole.all():
            for tee in h.holetee.all():
                if not tee.yard or tee.yard == 0:
                    return 'No'
        return 'Yes'

    def dehydrate_slope(self, subgc):
        for tee in subgc.teetype.all():
            if not tee.slope or tee.slope == 0:
                return 'No'
        return 'Yes'

    def dehydrate_rating(self, subgc):
        for tee in subgc.teetype.all():
            if not tee.rating or tee.rating == 0:
                return 'No'
        return 'Yes'

    def dehydrate_hole(self, subgc):
        for h in subgc.hole.all():
            if not h.picture:
                return 'No'
        return 'Yes'


class SubGolfCourseAdmin(ImportExportModelAdmin):
    search_fields = ['name', 'golfcourse__name']
    resource_class = SubGolfCourseResource
    pass


admin.site.register(SubGolfCourse, SubGolfCourseAdmin)


class HoleAdmin(admin.ModelAdmin):
    search_fields = ['subgolfcourse__name', ]
    pass


admin.site.register(Hole, HoleAdmin)


class TeeTypeAdmin(admin.ModelAdmin):
    search_fields = ['subgolfcourse__name', ]
    pass


admin.site.register(TeeType, TeeTypeAdmin)


class HoleTeeAdmin(admin.ModelAdmin):
    pass


admin.site.register(HoleTee, HoleTeeAdmin)


class GolfCourseResource(resources.ModelResource):
    class Meta:
        model = GolfCourse
        fields = (
            'id', 'name', 'address', 'description', 'picture', 'website', 'number_of_hole', 'longitude', 'latitude',
            'phone',)


class GolfCourseAdmin(ImportExportModelAdmin):
    search_fields = ['name', ]
    resource_class = GolfCourseResource
    pass


admin.site.register(GolfCourse, GolfCourseAdmin)



class GolfCourseEventAdmin(admin.ModelAdmin):
    raw_id_fields = ('user','golfcourse','tee_type',)

admin.site.register(GolfCourseEvent, GolfCourseEventAdmin)


class GolfStaffAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseStaff, GolfStaffAdmin)


class GolfCourseEventAdvertiseAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseEventAdvertise, GolfCourseEventAdvertiseAdmin)


class GolfCourseBookingSettingAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseBookingSetting, GolfCourseBookingSettingAdmin)


class GolfCourseEventMoreInfoAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseEventMoreInfo, GolfCourseEventMoreInfoAdmin)


class GolfCourseEventScheduleAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseEventSchedule, GolfCourseEventScheduleAdmin)


class GolfCourseEventBannerAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseEventBanner, GolfCourseEventBannerAdmin)

class GolfCourseEventPriceInfoAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseEventPriceInfo, GolfCourseEventPriceInfoAdmin)

#GolfCourseEventHotel
class GolfCourseEventHotelAdmin(admin.ModelAdmin):
    pass


admin.site.register(GolfCourseEventHotel, GolfCourseEventHotelAdmin)