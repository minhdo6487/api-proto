# -*- coding: utf-8 -*-
import datetime

from api.noticeMana.views import get_from_xmpp
from api.userMana.serializers import UserDisplaySerializer
from core.like.models import Like
from core.teetime.models import TeeTime, TeeTimePrice, Deal, BookingTime, DealEffective_TeeTime
from django.db.models import Sum
from pytz import country_timezones, timezone

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from core.golfcourse.models import GolfCourse, GolfCourseSetting, Services, GolfCourseServices, \
    SubGolfCourse, Hole, GolfCourseBuggy, GolfCourseCaddy, GolfCourseClubSets, TeeType, HoleTee, GolfCourseStaff, \
    HoleInfo, \
    GolfCourseReview
from rest_framework.pagination import PaginationSerializer
from utils.django.models import get_or_none
from core.gallery.models import Gallery
from api.galleryMana.serializers import GolfCourseGallerySerializer


class TeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeeType
        fields = ('id', 'subgolfcourse', 'name', 'slope', 'rating', 'color')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(TeeTypeSerializer, self).to_native(obj)
            try:
                hole = Hole.objects.get(subgolfcourse=obj.subgolfcourse, holeNumber=1)
                holetee = HoleTee.objects.get(hole=hole, tee_type=obj)
                serializers.update({'yard': holetee.yard})
            except:
                serializers.update({'yard': 0})
            return serializers


class HoleTeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoleTee
        fields = ('id', 'hole', 'tee_type', 'yard')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(HoleTeeSerializer, self).to_native(obj)
            tt = TeeType.objects.only('color').get(id=obj.tee_type_id)
            serializers.update({
                'color': tt.color
            })
            return serializers


class FullGolfCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourse

    def to_native(self, obj):
        if obj:
            serializers = super(FullGolfCourseSerializer, self).to_native(obj)
            subgolfcourse = obj.subgolfcourse.all()
            subgolfcourse_serializer = SubGolfCourseSerializer(subgolfcourse)
            serializers.update({
                'subgolfcourse': subgolfcourse_serializer.data
            })
            return serializers


class GolfCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourse
        # fields = ('id', 'name', 'address', 'city', 'district', 'country', 'description', 'picture',
        #           'website', 'member_type', 'number_of_hole', 'longitude', 'latitude', 'type', 'level', 'phone')
        fields = ('id', 'name', 'picture', 'longitude', 'latitude', 'city')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(GolfCourseSerializer, self).to_native(obj)
            # cttype = ContentType.objects.get_by_natural_key('golfcourse', 'golfcourse')
            # picture = Gallery.objects.filter(content_type=cttype.id, object_id=obj.id)
            # if picture.count() > 0:
            # pic_seri = GolfCourseGallerySerializer(picture[0])
            #     serializers.update({'avatar': pic_seri.data})
            # else:
            #     serializers.update({'avatar': []})
            # serializers.update({'city': obj.city.name})
            # serializers.update({'district': obj.district.name})
            return serializers


class AdvertiseGolfCourse(serializers.ModelSerializer):
    class Meta:
        model = GolfCourse
        fields = ('id', 'name', 'description', 'website', 'phone')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(AdvertiseGolfCourse, self).to_native(obj)
            ctype = ContentType.objects.get_by_natural_key('golfcourse', 'golfcourse')
            picture = Gallery.objects.filter(content_type=ctype.id, object_id=obj.id)
            if picture:
                pic_seri = GolfCourseGallerySerializer(picture[0])
                serializers.update({'picture': pic_seri.data['picture']})
            else:
                serializers.update({'picture': ''})
            return serializers


class GolfCourseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourse
        fields = ('id', 'name', 'address', 'city', 'district', 'country', 'description', 'picture',
                  'website', 'member_type', 'number_of_hole', 'longitude', 'latitude', 'type', 'level', 'phone',
                  'rating', 'partner', 'cloth', 'open_hour', 'discount')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(GolfCourseListSerializer, self).to_native(obj)
            cttype = ContentType.objects.get_by_natural_key('golfcourse', 'golfcourse')
            picture = Gallery.objects.filter(content_type=cttype.id, object_id=obj.id).first()

            pic_seri = GolfCourseGallerySerializer(picture)

            tz = timezone(country_timezones(obj.country.short_name)[0])
            now = datetime.datetime.fromtimestamp(datetime.datetime.utcnow().timestamp(), tz)

            d = now.date() + datetime.timedelta(days=1)
            deal_date = d
            to_date = now.date() + datetime.timedelta(days=3)
            teetimes = TeeTime.objects.filter(date__gte=d, date__lte=to_date, golfcourse=obj.id, is_block=False, is_booked=False,
                                              is_request=False)
            teetime_list = teetimes.values_list('id', flat=True)

            p = TeeTimePrice.objects.filter(teetime_id__in=teetime_list, is_publish=True, hole=18).extra(
                select={'fieldsum': 'online_discount + cash_discount'}, order_by=('teetime__date', '-fieldsum',)).first()
            price = 0
            discount = 0
            if p:
                discount = p.online_discount + p.cash_discount
                price = p.price
                deal_date = p.teetime.date
            filter_condition = {
                'date': now.date(),
                'to_time__gte': now.time(),
                'deal__active': True,
                'deal__effective_date__lte': now.date(),
                'deal__expire_date__gte': now.date(),
                'deal__golfcourse': obj.id
            }
            booking_time = BookingTime.objects.filter(**filter_condition).values_list('id', flat=True)
            deal_time = ""
            if booking_time:
                query_deal = DealEffective_TeeTime.objects.filter(bookingtime_id__in=booking_time,
                                                                  teetime__date=deal_date, teetime__is_block=False, teetime__is_booked=False,
                                                                  teetime__is_request=False).order_by('-discount')
                q = query_deal.first()
                if q and p:
                    discount = query_deal.first().discount + p.cash_discount
                deal = query_deal.count()
                deal_time = query_deal.first().bookingtime.from_time if query_deal.first() else ""
            else:
                deal = 0

            ## End here
            price_discount = price * (1 - (discount / 100))
            serializers.update({'avatar': pic_seri.data,
                                'deal_count': deal,
                                'deal_date': deal_date,
                                'deal_time': deal_time,
                                'price_discount': price_discount,
                                'price': price,
                                'discount': discount})
            return serializers


class HoleInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoleInfo
        fields = ('id', 'hole', 'infotype', 'metersy', 'metersx', 'pixely', 'pixelx', 'x', 'y', 'lat', 'lon')


class HolesSerializer(serializers.ModelSerializer):
    hole_tee = HoleTeeSerializer(many=True, required=False, source='holetee')
    hole_info = HoleInfoSerializer(many=True, required=False, source='holeinfo')

    class Meta:
        model = Hole
        fields = ('id', 'subgolfcourse', 'holeNumber', 'par', 'picture', 'hdcp_index', 'hole_info', 'hole_tee', 'photo')


class SubGolfCourseSerializer(serializers.ModelSerializer):
    tee_type = TeeTypeSerializer(many=True, required=False, source='teetype')
    hole = HolesSerializer(many=True, required=False)

    class Meta:
        model = SubGolfCourse
        fields = ('id', 'golfcourse', 'name', 'description', 'picture', 'number_of_hole', 'tee_type', 'hole')

    def to_native(self, obj):
        if obj:
            serializers = super(SubGolfCourseSerializer, self).to_native(obj)
            tee_type = sorted(serializers['tee_type'], key=lambda ite_s: ite_s['yard'])
            serializers['tee_type'] = tee_type
            return serializers


class GolfCourseSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseSetting


class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = ('name', 'description')


class GolfCourseServicesSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='services.name')

    class Meta:
        model = GolfCourseServices
        fields = ('services', 'provide', 'name')


class GolfCourseClubSetSerializer(serializers.ModelSerializer):
    clubset = serializers.SerializerMethodField('get_clubset_name')

    @staticmethod
    def get_clubset_name(obj):
        clubset = obj.clubset
        if clubset:
            return clubset.name
        return None

    class Meta:
        model = GolfCourseClubSets
        fields = ('id', 'clubset', 'price')


class GolfCourseBuggySerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseBuggy
        fields = ('id', 'buggy', 'price')


class GolfCourseStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseStaff
        fields = ('id', 'user', 'golfcourse', 'description', 'role')


class GolfCourseCaddySerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseCaddy
        fields = ('id', 'name', 'number', 'price')


class GolfCourseReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseReview

    def to_native(self, obj):
        if obj is not None:
            serializers = super(GolfCourseReviewSerializer, self).to_native(obj)
            user_seri = UserDisplaySerializer(obj.user)
            gc_review_ctype = ContentType.objects.get_for_model(GolfCourseReview)
            like_count = Like.objects.filter(content_type=gc_review_ctype, object_id=obj.id).aggregate(Sum('count'))[
                'count__sum']
            if not like_count:
                like_count = 0
            (count, uread) = get_from_xmpp('', obj.id)
            golfcourse_review_count = GolfCourseReview.objects.filter(golfcourse=obj.golfcourse).count()
            golfcourse_rating = obj.golfcourse.rating
            serializers.update({'user_info': user_seri.data,
                                'like_count': like_count,
                                'comment_count': count,
                                'golfcourse_review_count': golfcourse_review_count,
                                'golfcourse_rating': golfcourse_rating,
                                'golfcourse_name':obj.golfcourse.name})
            return serializers


class PlayStayGolfCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourse
        fields = ('id', 'name','short_name', 'description', 'description_en','website', 'phone', 'address', 'longitude', 'latitude')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(PlayStayGolfCourseSerializer, self).to_native(obj)
            ctype = ContentType.objects.get_by_natural_key('golfcourse', 'golfcourse')
            picture = Gallery.objects.filter(content_type=ctype.id, object_id=obj.id)
            serializers.update({'pictures':GolfCourseGallerySerializer(picture).data})
            return serializers

class PaginatedGolfCourseListSerializer(PaginationSerializer):
    """
    Serializes page objects of notification querysets.
    """

    class Meta:
        object_serializer_class = GolfCourseListSerializer