import datetime, time
from rest_framework import serializers
from core.teetime.models import DealEffective_TeeTime,BookingTime,Deal,TimeRangeType,DealEffective_TimeRange, TeeTime
from api.dealMana.tasks import validate_deal
class DealEffective_TeeTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealEffective_TeeTime
        fields = ('teetime',)
    def to_native(self, obj):
        if obj:
            serializers = super(DealEffective_TeeTimeSerializer, self).to_native(obj)
            time = obj.teetime.time
            teetime_id = serializers['teetime']
            del serializers['teetime']
            serializers['id'] = teetime_id
            serializers['time'] = datetime.timedelta(hours=time.hour,minutes=time.minute).total_seconds() * 1000
            serializers['status'] = True
            return serializers

class UnEffectTeeTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeeTime
        fields = ('id', 'time')
    def to_native(self, obj,bookingtime=None,timerange=None):
        if obj:
            serializers = super(UnEffectTeeTimeSerializer, self).to_native(obj)
            serializers['time'] = datetime.timedelta(hours=serializers['time'].hour,minutes=serializers['time'].minute).total_seconds() * 1000
            serializers['status'] = False
            return serializers
class DealEffective_TimeRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealEffective_TimeRange
    def to_native(self, obj):
        if obj is not None:
            tt = super(DealEffective_TimeRangeSerializer, self).to_native(obj)
            tt['date'] = time.mktime(tt['date'].timetuple()) * 1000
            return tt
class BookingTimeSerializer(serializers.ModelSerializer):
    timerange=DealEffective_TimeRangeSerializer(many=True, required=False, source='timerange')
    class Meta:
        model = BookingTime
    def to_native(self, obj):
        if obj is not None:
            tt = super(BookingTimeSerializer, self).to_native(obj)
            tt['from_time'] = datetime.timedelta(hours=tt['from_time'].hour,minutes=tt['from_time'].minute).total_seconds() * 1000
            tt['to_time'] = datetime.timedelta(hours=tt['to_time'].hour,minutes=tt['to_time'].minute).total_seconds() * 1000
            tt['date'] = time.mktime(tt['date'].timetuple()) * 1000
            return tt

class TimeRangeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeRangeType
    def to_native(self, obj):
        if obj is not None:
            tt = super(TimeRangeTypeSerializer, self).to_native(obj)
            tt['from_time'] = datetime.timedelta(hours=tt['from_time'].hour,minutes=tt['from_time'].minute).total_seconds() * 1000
            tt['to_time'] = datetime.timedelta(hours=tt['to_time'].hour,minutes=tt['to_time'].minute).total_seconds() * 1000
            return tt
class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
    def to_native(self, obj):
        if obj is not None:
            obj = validate_deal(obj)
            tt = super(DealSerializer, self).to_native(obj)
            tt['effective_date'] = time.mktime(tt['effective_date'].timetuple()) * 1000
            tt['expire_date'] = time.mktime(tt['expire_date'].timetuple()) * 1000
            tt['end_date'] = time.mktime(tt['end_date'].timetuple()) * 1000 if tt['end_date'] else tt['end_date']
            tt['effective_time'] = datetime.timedelta(hours=tt['effective_time'].hour,minutes=tt['effective_time'].minute).total_seconds() * 1000
            tt['expire_time'] = datetime.timedelta(hours=tt['expire_time'].hour,minutes=tt['expire_time'].minute).total_seconds() * 1000
            tt['end_time'] = datetime.timedelta(hours=tt['end_time'].hour,minutes=tt['end_time'].minute).total_seconds() * 1000 if tt['end_time'] else tt['end_time']
            status = 1
            if obj.active:
                status = 2
            elif not obj.active and obj.end_date:
                status = 3
            tt['status'] = status
            return tt
        