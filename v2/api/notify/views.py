from datetime import date

from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
import arrow

from GolfConnect.settings import TIME_ZONE

from core.user.models import UserProfile
from . import serializers
from . import models
from . import tasks


class PushNotificationCampaignViewSet(ModelViewSet):
    """
    ViewSet for viewing & editing Campaign
    """
    
    serializer_class = serializers.CampSerializer
    permission_classes = [IsAdminUser, ]
    
    paginate_by = 20
    paginate_by_param = 'page_size'
    
    queryset = models.Camp.objects.all()
    
    def get_queryset(self):
        return models.Camp.objects.filter(sent_at__isnull=True).order_by('-updated_at')
    
    def _get_client_data(self, request):
        payload = dict(request.DATA)
        payload.update({'user_id': request.user.id})
        
        if not 'scheduled_at' in payload:
            raise ValueError('scheduled_at field required.')

        payload['schedules'] = []
        # validate scheduled_at times
        req_schedules = payload.get('scheduled_at')
        if not isinstance(req_schedules, list):
            req_schedules = list(req_schedules)
        now = arrow.now(TIME_ZONE)
        for item in req_schedules:
            item_time = arrow.get(item)
            if item_time < now:
                raise ValueError('Invalid schedule time {0}'.format(item))
            payload['schedules'].append(item_time)
        
        
        
        return payload
    
    def create(self, request, *args, **kwargs):
        
        try:
            payload = self._get_client_data(request)
        except ValueError as err:
            return Response({'status': 400, 'detail': str(err)}, status=400)
        
        serializer = serializers.CampSerializer(data=payload)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        camp = serializer.save()
        schedule_times_iso = []
        for schedule_time in payload.get('schedules', []):
            schedule = models.Schedule(camp_id=camp.id, timed_at=schedule_time.datetime)
            schedule.save()
            schedule_times_iso.append(schedule_time.isoformat())
        
        resp_data = serializer.data
        resp_data['scheduled_at'] = schedule_times_iso
        return Response(serializer.data, 200)
    
    def update(self, request, *args, **kwargs):
        """
        Update campaigns

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        partial = kwargs.pop('partial', False)
        camp = self.get_object_or_none()
        try:
            payload = self._get_client_data(request)
        except ValueError as err:
            return Response({'status': 404, 'detail': str(err)}, status=400)
        
        if not camp:
            return Response({'status': 404, 'detail': 'Campaign not found.'}, status=400)
        
        if camp.sent_at:
            return Response({'status': 404, 'detail': 'Timed out campaign.'}, status=400)
        
        serializer = serializers.CampSerializer(camp, data=payload, partial=partial)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if 'schedules' in payload:
            # clear old schedules
            models.Schedule.objects.filter(camp_id=camp.id, sent_at__isnull=True).delete()
            
            for schedule_time in payload.get('schedules'):
                schedule = models.Schedule(camp_id=camp.id, timed_at=schedule_time.datetime)
                schedule.save()
        
        serializer.save(force_update=True)
        resp_data = serializer.data
        resp_data['scheduled_at'] = []
        # load all schedules for response
        schedules = models.Schedule.objects.filter(camp_id=camp.id, sent_at__isnull=True)
        for schedule in schedules:
            resp_data['scheduled_at'].append(schedule.timed_at)
        
        return Response(resp_data, 200)
    
    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.sent_at is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        self.pre_delete(obj)
        # delete all schedules
        models.Schedule.objects.filter(camp_id=obj.id, sent_at__isnull=True).delete()
        obj.delete()
        self.post_delete(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes((IsAdminUser,))
def count_total_by_filters(request):
    filters = {}
    if 'age_min' in request.DATA and 'age_max' in request.DATA:
        now = arrow.now()
        age_max = int(request.DATA['age_max'])
        age_min = int(request.DATA['age_min'])
        min_date = date(now.datetime.year - age_max, now.datetime.month, now.datetime.day)
        max_date = date(now.datetime.year - age_min, now.datetime.month, now.datetime.day)
        filters = {
            'dob__gte': min_date,
            'dob__lte': max_date,
        }
        
    # build query city_id
    if 'city_ids' in request.DATA:
        raw_city_ids = request.DATA.get('city_ids').split(',')
        city_ids = []
        for raw_id in raw_city_ids:
            # safe cast int
            try:
                city_ids.append(int(raw_id.strip()))
            except (ValueError, TypeError):
                pass
        if city_ids:
            filters['city_id__in'] = city_ids
        
    if 'gender' in request.DATA and request.DATA['gender'] != '-':
        filters['gender'] = request.DATA['gender'].upper()
    total = UserProfile.objects.filter(**filters).count()
    
    return Response({'total': total})

# do push schedules on cron
@api_view(['POST'])
def cron_push_schedules(request):
    tasks.send_expired_schedules()
    return Response(status=204)


class CampHistoryViewSet(ModelViewSet):
    paginate_by = 20
    paginate_by_param = 'page_size'
    queryset = models.Camp.objects.filter(sent_at__isnull=False)
    
    serializer_class = serializers.CampHistorySerializer
    permission_classes = [IsAdminUser, ]
    

class NotifyLogViewSet(ModelViewSet):
    paginate_by = 20
    paginate_by_param = 'page_size'
    queryset = models.CampLog.objects.all()
    
    serializer_class = serializers.NotifyLogSerializer
    permission_classes = [IsAuthenticated, ]
    
    def get_queryset(self):
        if self.request.user.is_staff and 'user_id' in self.request.QUERY_PARAMS:
            user_id = self.request.QUERY_PARAMS.get('user_id')
            self.queryset = models.CampLog.objects.filter(user_id=user_id)
        else:
            self.queryset = models.CampLog.objects.filter(user_id=self.request.user.id)

        return self.queryset
        
