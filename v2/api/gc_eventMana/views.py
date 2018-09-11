import json

from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    RetrieveAPIView
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly
)

from utils.django.models import get_or_none

from rest_framework import mixins
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.utils import encoders
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from core.golfcourse.models import GolfCourseEvent
from core.game.models import EventMember, Game
from core.booking.models import BookedTeeTime, BookedPartner, BookedClubset, BookedCaddy, BookedBuggy, BookingSetting, \
    BookedTeeTime_History, BookedPartner_History, BookedGolfcourseEvent, BookedGolfcourseEventDetail
from core.teetime.models import GCSetting, TeeTime, TeeTimePrice, GuestType, TeetimeShowBuggySetting
from api.buggyMana.serializers import GolfCourseBuggySerializer, GolfCourseCaddySerializer
import base64
from core.user.models import UserProfile

from api.bookingMana.views import fn_getHostname

from v2.api.gc_eventMana.serializers import GolfCourseEventSerializer, GC_Booking_Serializer, \
    GC_Booking_Detail_Serializer, \
    MyBookingSerializer_v2, MyBookingDetailSerializer_v2

# type_event = "GE"
type_event = ["GE", "PE"]


class MyGC_EventViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = GC_Booking_Serializer

    @staticmethod
    def get(request):
        _all = request.QUERY_PARAMS.get('all', 0)
        user = request.user

        if not user or not user.is_authenticated():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)

        ### get GE event id
        # event_ids = (GolfCourseEvent.objects.filter(event_type__exact=type_event).values('id'))
        event_ids = (GolfCourseEvent.objects.filter(event_type__in=type_event).values('id'))

        ### get member take part in GE event
        members_join_ge = EventMember.objects.filter(event_id__in=event_ids).values('id')

        ### member've booked
        members_booked_ge = BookedGolfcourseEvent.objects.filter(member_id__in=members_join_ge)

        if int(_all) == 1:
            # res = GC_Booking_Serializer(members_booked_ge)
            res = GC_Booking_Detail_Serializer(members_booked_ge)
        else:
            # res = GC_Booking_Serializer(members_booked_ge)
            res = GC_Booking_Detail_Serializer(members_booked_ge)

        return Response({'data': res.data}, status=200)


class MyGC_Event_DetailViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = GC_Booking_Detail_Serializer

    @staticmethod
    def get(request, key=None):
        user = request.user
        if not user or not user.is_authenticated():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        res = {}

        booked = get_or_none(BookedGolfcourseEvent, pk=key)

        res = GC_Booking_Detail_Serializer(booked)
        domain = fn_getHostname(request)

        return Response({'detail': res.data}, status=200)


class MyBookingViewSet_v2(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = MyBookingSerializer_v2

    @staticmethod
    def get(request):
        _all = request.QUERY_PARAMS.get('all', 0)
        _date = request.QUERY_PARAMS.get('date', 0)
        user = request.user

        if not user or not user.is_authenticated():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        partner_ids = BookedPartner.objects.filter(user_id=user.id).values('bookedteetime_id')

        if not partner_ids or len(partner_ids) == 0:
            return Response({'status': '400', 'code': 'E_NOT_FOUND',
                             'detail': 'Request data not found'}, status=401)
        booked = BookedTeeTime.objects.filter(pk__in=partner_ids).order_by('-teetime__date')

        domain = fn_getHostname(request)
        data_sorted = []
        if int(_all) == 1:
            res = MyBookingDetailSerializer_v2(booked)

            l = list(EventMember.objects.filter(user_id=request.user).values_list('id', flat=True))

            booked_gc_event_info = []
            booked_gc_event_info_tmp = []
            for item in l:
                booked = BookedGolfcourseEvent.objects.filter(member_id__exact=item)
                res_booked_gc_event = GC_Booking_Detail_Serializer(booked)
                if res_booked_gc_event.data:
                    booked_gc_event_info = (res_booked_gc_event.data)
                    booked_gc_event_info_tmp.append(res_booked_gc_event.data)
                    # booked_gc_event_info.append(res_booked_gc_event.data)

            for obj in res.data:
                encode_data = base64.urlsafe_b64encode(str(obj['id']).encode('ascii')).decode('ascii')
                cancel_teetime_url = 'https://' + domain + '/api/cancel-teetime/' + encode_data + '/'
                obj['cancel_url'] = cancel_teetime_url
                # qr text
                obj['qr_text'] = 'https://' + domain + '/#/checkin/' + encode_data
                # get gift
                gtype = GuestType.objects.get(name='G')
                teetime_price = get_or_none(TeeTimePrice, teetime_id=obj['teetime_id'], hole=18, guest_type_id=gtype.id)
                obj['gifts'] = teetime_price.gifts
                obj['food_voucher'] = teetime_price.food_voucher
                obj['buggy'] = teetime_price.buggy
                obj['caddy'] = teetime_price.caddy
                buggy = get_or_none(BookedBuggy, teetime=obj['id'])
                caddy = get_or_none(BookedCaddy, teetime=obj['id'])
                obj['buggy_qty'] = buggy.quantity if buggy else 0
                obj['caddy_qty'] = caddy.quantity if caddy else 0
                obj['test'] = 0

            # print (booked_gc_event_info)
            # print (len(booked_gc_event_info), len(booked_gc_event_info_tmp))

            # data = [dict(i) for i in res.data] + [dict(i) for i in booked_gc_event_info]
            data = [dict(i) for i in res.data]
            for item in booked_gc_event_info_tmp:
                # print (item)
                data = data + [dict(i) for i in item]
            # print (data)
            data_list = list(data)

            for i in data_list:
                if 'gcevent_date' not in i.keys():
                    i.update({'gen_date': i['teetime_date']})
                # if  booked_gc_event_info:
                # 	print (i['id'], i['teetime_date'] )
                else:
                    i.update({'gen_date': i['gcevent_date']})

            data_sorted = sorted(data_list, key=lambda k: k['gen_date'], reverse=True)

        else:
            res = MyBookingSerializer_v2(booked)
            data_sorted = res.data
        # return Response({'data': res.data}, status=200)
        return Response({'data': data_sorted}, status=200)


class MyBookingDetailViewSet_v2(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = MyBookingDetailSerializer_v2

    @staticmethod
    def get(request, key=None):
        user = request.user
        if not user or not user.is_authenticated():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        res = {}
        booked = get_or_none(BookedTeeTime, pk=key)
        res = MyBookingDetailSerializer_v2(booked)
        encode_data = base64.urlsafe_b64encode(str(booked.id).encode('ascii')).decode('ascii')
        domain = fn_getHostname(request)
        if booked:
            # cancel teetime url
            cancel_teetime_url = 'https://' + domain + '/api/cancel-teetime/' + encode_data + '/'
            res.data['cancel_url'] = cancel_teetime_url
            # get gift
            gtype = GuestType.objects.get(name='G')
            teetime_price = get_or_none(TeeTimePrice, teetime_id=booked.teetime_id, hole=18, guest_type_id=gtype.id)
            res.data['gifts'] = teetime_price.gifts
            res.data['food_voucher'] = teetime_price.food_voucher
            res.data['buggy'] = teetime_price.buggy
            res.data['caddy'] = teetime_price.caddy
            buggy = get_or_none(BookedBuggy, teetime=booked)
            caddy = get_or_none(BookedCaddy, teetime=booked)
            res.data['buggy_qty'] = buggy.quantity if buggy else 0
            res.data['caddy_qty'] = caddy.quantity if caddy else 0
        return Response({'detail': res.data}, status=200)


@api_view(["GET"])
@permission_classes((AllowAny,))
def cron_send_email_survey(request):
    from core.booking.models import BookedGolfcourseEvent, BookedGolfcourseEventDetail
    from api.bookingMana.serializers import BookedGolfcourseEventSerializer
    from core.booking.models import BookedPartner_GolfcourseEvent
    from core.customer.models import Customer
    import datetime
    from datetime import timedelta, date
    from v2.api.gc_eventMana.tasks import send_email_survey
    from pytz import timezone, country_timezones

    today = date.today()
    for i in BookedGolfcourseEvent.objects.filter(created__day=today.day, created__year=today.year,
                                                  created__month=today.month).values('created', 'id'):
        b_gcev = BookedGolfcourseEvent.objects.get(pk=i['id'])
        tz = timezone(country_timezones(b_gcev.member.event.golfcourse.country.short_name)[0])
        book_check = (datetime.datetime.fromtimestamp(i['created'].timestamp(), tz))

        if book_check.hour < 21:
            send_email_survey.delay(b_gcev.id)

    return Response({'detail': 'done'}, status=200)
# print (book_check.hour, book_check.day, b_gcev.member.customer)

