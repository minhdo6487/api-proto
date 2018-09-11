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
        # fields = ('id', 'golfcourse', 'name', 'description', 'picture', 'number_of_hole', 'tee_type', 'hole')


    def to_native(self, obj):
        if obj:
            serializers = super(SubGolfCourseSerializer, self).to_native(obj)


            tee_type = sorted(serializers['tee_type'], key=lambda ite_s: ite_s['yard'])
            serializers['tee_type'] = tee_type
            # if serializers['number_of_hole'] == 18:
            #     serializers.clear()
            return serializers