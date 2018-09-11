# serializers
from rest_framework import serializers

from . import models


class CampSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Camp
        
    def to_native(self, obj):
        data = super(CampSerializer, self).to_native(obj)
        
        data['scheduled_at'] = []
        schedules = models.Schedule.objects.filter(camp_id=obj.id)
        for schedule in schedules:
            data['scheduled_at'].append(schedule.timed_at)
        
        return data


class CampHistorySerializer(CampSerializer):
    def to_native(self, obj):
        data = super(serializers.ModelSerializer, self).to_native(obj)
        data['scheduled_at'] = []
        schedules = models.Schedule.objects.filter(camp_id=obj.id, sent_at__isnull=False)
        for schedule in schedules:
            data['scheduled_at'].append(schedule.timed_at)

        return data


class NotifyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CampLog
        