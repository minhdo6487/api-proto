# -*- coding: utf-8 -*-
import base64
import datetime
import decimal
import json
from urllib.parse import quote
from datetime import timedelta
from decimal import Decimal
from email.mime.image import MIMEImage
from hashlib import sha1, sha256
import pyqrcode
import redis
from django.contrib.auth.models import User

from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template import Context
from django.template.loader import render_to_string, get_template
from django.core.validators import validate_email
from django.db.models import Q
from django.utils import timezone as django_timezone
from django.utils.timezone import utc, pytz
from pytz import timezone, country_timezones
from rest_framework import viewsets, permissions
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError
from rest_framework.decorators import api_view, permission_classes

from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, CURRENT_ENV, PAYMERCHANTCODE, PAYPASSCODE, \
    PAYSECRETKEY, PAYURL
from api.bookingMana.serializers import BookingGolfcourseSerializer, BookingSerializer, BookingPartnerSerializer, \
    BookedTeeTimeSerializer, BookingSettingSerializer, BookedTeeTime_HistorySerializer, MyBookingDetailSerializer, \
    MyBookingSerializer, BookingBuggySerializer, BookingCaddySerializer, ComissionSerializer, BookedGCSerializer, \
    GetTeetimeSerializer, BookedGolfcourseEventSerializer
from api.buggyMana.serializers import GolfCourseBuggySerializer, GolfCourseCaddySerializer
from core.golfcourse.models import GolfCourseBuggy, GolfCourseCaddy, GolfCourseEventPriceInfo, GolfCourse
from api.bookingMana.tasks import task_auto_expire_holding, get_booked_buggy_caddy, send_email_task, \
    handle_cancel_booking, payment_queryOrder, get_client_ip, auto_payment_queryOrder, \
    send_thankyou_email  # , send_email_booking_event , update_payment_online_status

from v2.api.gc_eventMana.tasks import send_email_booking_event, update_payment_online_status

from api.golfcourseMana.serializers import GolfCourseSerializer
from api.teetimeMana.serializers import TeeTimeSerializer
from core.booking.models import BookedTeeTime, BookedPartner, calculate_price, BookingSetting, BookedTeeTime_History, \
    Voucher, BookedPayonlineLink
from core.booking.models import BookedCaddy, BookedBuggy, PayTransactionStore, TRANSACTIONSTATUS, GC24BookingVendor, \
    BookedGolfcourseEvent, BookedGolfcourseEventDetail, BookedPartner_GolfcourseEvent
from core.customer.models import Customer
from core.golfcourse.models import GolfCourseStaff, GolfCourseBookingSetting
from core.teetime.models import TeeTime, TeeTimePrice, GuestType, BookingTime, DealEffective_TeeTime, Gc24TeeTimePrice, \
    GC24PriceByDeal, GC24PriceByBooking_Detail
from utils.django.models import get_or_none
from utils.rest.code import code
from utils.rest.permissions import UserIsOwnerOrReadOnly
# from utils.rest.sendemail import send_email
from api.noticeMana.tasks import send_email, send_after_booking_email
from collections import OrderedDict
import math
from operator import itemgetter
from utils.rest.viewsets import NotDeleteViewSet

redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
import http.client

VNG = '123Pay'
VTC = 'VTCPay'
BOOKING_TEETIME_STATUS = {
    'OPEN': '1',
    'HOLD': '2',
    'BLOCK': '3',
}

DOW = {
    'Monday': 'Thứ Hai',
    'Tuesday': 'Thứ Ba',
    'Wednesday': 'Thứ Tư',
    'Thursday': 'Thứ Năm',
    'Friday': 'Thứ Sáu',
    'Saturday': 'Thứ Bảy',
    'Sunday': 'Chủ Nhật',
}
VTC_STATUS_MAPPING = {
    '1': '1',
    '2': '1',
    '7': '10',
    '0': '20',
    '-1': '-100',
    '-5': '-10',
    '-6': '7201',
    '-99': '-100'

}


def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def extract_nbr(input_str):
    if input_str is None or input_str == '':
        return 0

    out_number = ''
    for ele in input_str:
        if ele.isdigit():
            out_number += ele
        return out_number


def extract_email(email):
    last_dot_index = email.rindex('.')
    gap = min((len(email) - last_dot_index), 4)
    return email[:(last_dot_index + gap)]


# class ValidationError(APIException): pass
class AutoCheckPayment(APIView):
    @staticmethod
    def get(request, key=None):
        auto_payment_queryOrder()
        return Response({'status': '200', 'code': 'OK'}, status=200)


class BookedTeeTimeViewSet(NotDeleteViewSet):
    queryset = BookedTeeTime.objects.all()
    serializer_class = BookingSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, UserIsOwnerOrReadOnly)
    filter_fields = ('reservation_code',)
    ordering_by = ('id',)

    # Save current user to the slot
    def pre_save(self, obj):
        obj.user = self.request.user


class BookedPartnerViewSet(NotDeleteViewSet):
    queryset = BookedPartner.objects.all()
    serializer_class = BookingPartnerSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, UserIsOwnerOrReadOnly)


def fn_getHostname(request):
    domain = ''
    if 'HTTP_HOST' in request.META:
        domain = request.META['HTTP_HOST']
    else:
        domain = request.META['REMOTE_ADDR']
    return domain


def notify_unlock(teetime):
    channel = 'booking-' + str(teetime.date)
    msg = {
        "id": teetime.id,
        "is_block": False
    }
    d = json.dumps(msg)
    redis_server.publish(channel, d)


def handle_success_booking_teetime(request, key):
    pk = int(key[1:])
    teetime = get_or_none(BookedTeeTime, pk=pk)
    if teetime:
        tt = teetime.teetime
        temp_paymentStore = PayTransactionStore.objects.filter(
            transactionId__contains="t{0}".format(teetime.id)).order_by('-id')
        if temp_paymentStore.exists():
            # paymentStore = get_or_none(PayTransactionStore, transactionId="t{0}".format(teetime.id))
            paymentStore = temp_paymentStore.first()
        else:
            return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                             'detail': 'Booking Not found', 'back_link': teetime.back_link}, status=404)
        serializer = BookedTeeTimeSerializer(teetime)
        data = get_booked_buggy_caddy(teetime.id)
        serializer.data.update(data)
        domain = fn_getHostname(request)
        if int(paymentStore.transactionStatus) == 0:
            status = payment_queryOrder(paymentStore, request)
            if status == 0:
                status = -100
            update_payment_online_status(paymentStore=paymentStore, booked=teetime, bankCode=None,
                                         transactionStatus=str(status), domain=domain)
            if status == 20 or status == 10:
                return Response({'status': '404', 'code': 'NOT_COMPLETE',
                                 'detail': TRANSACTIONSTATUS[status], 'back_link': teetime.back_link}, status=404)
            elif status == 1:
                serializer = BookedTeeTimeSerializer(teetime)
                serializer.data.update(data)
                encode_data = base64.urlsafe_b64encode(str(teetime.id).encode('ascii')).decode('ascii')
                serializer.data['encode_data'] = encode_data
                return Response({'status': '200', 'code': 'OK',
                                 'detail': serializer.data, 'back_link': teetime.back_link}, status=200)
            else:
                notify_unlock(tt)
                return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                                 'detail': TRANSACTIONSTATUS.get(status, 'PAYMENT ERROR'),
                                 'back_link': teetime.back_link}, status=404)
        elif int(paymentStore.transactionStatus) == 1:
            encode_data = base64.urlsafe_b64encode(str(teetime.id).encode('ascii')).decode('ascii')
            serializer.data['encode_data'] = encode_data
            return Response({'status': '200', 'code': 'OK',
                             'detail': serializer.data, 'back_link': teetime.back_link}, status=200)
        else:

            return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                             'detail': TRANSACTIONSTATUS.get(int(paymentStore.transactionStatus), 'PAYMENT ERROR'),
                             'back_link': teetime.back_link}, status=404)
    else:
        return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                         'detail': 'Booking Not found'}, status=404)


def handle_success_booking_event(request, key):
    pk = int(key[1:])
    booked = get_or_none(BookedGolfcourseEvent, pk=pk)
    if booked:
        # temp_paymentStore = PayTransactionStore.objects.filter(
            # transactionId__contains="t{0}".format(booked.id)).order_by('-id')
        ### make it worked for booking GC event
        temp_paymentStore = PayTransactionStore.objects.filter(
            transactionId__contains="e{0}".format(booked.id)).order_by('-id')
        if temp_paymentStore.exists():
            # paymentStore = get_or_none(PayTransactionStore, transactionId="t{0}".format(teetime.id))
            paymentStore = temp_paymentStore.first()
        else:
            return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                             'detail': 'Booking Not found'}, status=404)
        serializer = BookedGolfcourseEventSerializer(booked)
        serializer.data.update({'discount_type': 'paynow'})
        domain = fn_getHostname(request)
        print ("gia tri : {}".format(paymentStore.transactionStatus))
        if int(paymentStore.transactionStatus) == 0:
            status = payment_queryOrder(paymentStore, request)
            if status == 0:
                status = -100
            update_payment_online_status(paymentStore=paymentStore, booked=booked, bankCode=None,
                                         transactionStatus=str(status), domain=domain)
            if status == 20 or status == 10:
                return Response({'status': '404', 'code': 'NOT_COMPLETE',
                                 'detail': TRANSACTIONSTATUS[status]}, status=404)
            elif status == 1:
                serializer = BookedGolfcourseEventSerializer(booked)
                encode_data = base64.urlsafe_b64encode(str(booked.id).encode('ascii')).decode('ascii')
                serializer.data['encode_data'] = encode_data
                return Response({'status': '200', 'code': 'OK',
                                 'detail': serializer.data}, status=200)
            else:
                return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                                 'detail': TRANSACTIONSTATUS.get(status, 'PAYMENT ERROR')}, status=404)
        elif int(paymentStore.transactionStatus) == 1:
            encode_data = base64.urlsafe_b64encode(str(booked.id).encode('ascii')).decode('ascii')
            serializer.data['encode_data'] = encode_data
            return Response({'status': '200', 'code': 'OK',
                             'detail': serializer.data}, status=200)
        else:
            return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                             'detail': TRANSACTIONSTATUS.get(int(paymentStore.transactionStatus), 'PAYMENT ERROR')},
                            status=404)
    else:
        return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                         'detail': 'Booking Not found'}, status=404)


def handle_success_booking_noncheck(request, key):
    pk = int(key[1:])
    booked = get_or_none(BookedPayonlineLink, pk=pk)
    if booked:
        temp_paymentStore = PayTransactionStore.objects.filter(
            transactionId__contains="n{0}".format(booked.id)).order_by('-id')
        if temp_paymentStore.exists():
            paymentStore = temp_paymentStore.first()
        else:
            return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                             'detail': 'Booking Not found'}, status=404)
        domain = fn_getHostname(request)
        if int(paymentStore.transactionStatus) == 0:
            status = payment_queryOrder(paymentStore, request)
            if status == 0:
                status = -100
            update_payment_online_status(paymentStore=paymentStore, booked=booked, bankCode=None,
                                         transactionStatus=str(status), domain=domain)
            if status == 20 or status == 10:
                return Response({'status': '404', 'code': 'NOT_COMPLETE',
                                 'detail': TRANSACTIONSTATUS[status]}, status=404)
            elif status == 1:
                return Response({'status': '200', 'code': 'NOT_COMPLETE',
                                 'detail': 'Your payment is handling. We will contact to you to confirm your booking.'},
                                status=200)
        elif int(paymentStore.transactionStatus) == 1:
            return Response({'status': '200', 'code': 'NOT_COMPLETE',
                             'detail': 'Your payment is handling. We will contact to you to confirm your booking.'},
                            status=200)
        else:
            return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                             'detail': TRANSACTIONSTATUS.get(int(paymentStore.transactionStatus), 'PAYMENT ERROR')},
                            status=404)
    else:
        return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                         'detail': 'Booking Not found'}, status=404)


class BookingSuccessViewSet(APIView):
    @staticmethod
    def get(request, key=None):
        if key:
            if 't' in key:
                return handle_success_booking_teetime(request, key)
            if 'n' in key:
                return handle_success_booking_noncheck(request, key)
            if 'e' in key:
                return handle_success_booking_event(request, key)
        return Response({'status': '404', 'code': 'UNSUCCESSFULL',
                         'detail': 'Booking Not found'}, status=404)


class PaymentNotify(APIView):
    @staticmethod
    def post(request, key=None):
        domain = fn_getHostname(request)
        data = request.DATA
        #### handle notifcation of 123Pay
        mTransactionID = data.get('mTransactionID', '')
        bankCode = data.get('bankCode', '')
        transactionStatus = data.get('transactionStatus', '')
        description = data.get('description', '')
        ts = data.get('ts', '')
        checksum = data.get('checksum', '')
        res_cs = mTransactionID + bankCode + transactionStatus + ts + PAYSECRETKEY
        res_hashed = sha1(res_cs.encode('utf-8')).hexdigest()
        ord_dict = OrderedDict()
        paymentStore = get_or_none(PayTransactionStore, transactionId=mTransactionID)
        print("Tuan Ly Here: ", mTransactionID, transactionStatus, ts)
        if not paymentStore:
            res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
            cs = mTransactionID + "-3" + res_ts + PAYSECRETKEY
            ord_dict['mTransactionID'] = mTransactionID
            ord_dict['returnCode'] = '-3'
            ord_dict['ts'] = res_ts
            ord_dict['checksum'] = sha1(cs.encode('utf-8')).hexdigest()
            return Response(ord_dict, status=200)
        if not (res_hashed == checksum):
            res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
            cs = mTransactionID + "-1" + res_ts + PAYSECRETKEY
            ord_dict['mTransactionID'] = mTransactionID
            ord_dict['returnCode'] = '-1'
            ord_dict['ts'] = res_ts
            ord_dict['checksum'] = sha1(cs.encode('utf-8')).hexdigest()
            return Response(ord_dict, status=200)

        booked = None
        if 't' in mTransactionID:
            booked_id = int(mTransactionID[mTransactionID.index('t') + 1:])
            booked = get_or_none(BookedTeeTime, pk=booked_id)
        elif 'n' in mTransactionID:
            booked_id = int(mTransactionID[mTransactionID.index('n') + 1:])
            booked = get_or_none(BookedPayonlineLink, pk=booked_id)
        elif 'e' in mTransactionID:
            booked_id = int(mTransactionID[mTransactionID.index('e') + 1:])
            booked = get_or_none(BookedGolfcourseEvent, pk=booked_id)
        if booked:
            res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
            cs = mTransactionID + "1" + res_ts + PAYSECRETKEY
            update_payment_online_status(paymentStore, booked, bankCode, transactionStatus, domain)
            ord_dict['mTransactionID'] = mTransactionID
            ord_dict['returnCode'] = '1'
            ord_dict['ts'] = res_ts
            ord_dict['checksum'] = sha1(cs.encode('utf-8')).hexdigest()
            return Response(ord_dict, status=200)
        else:
            res_ts = str(int(datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()))
            cs = mTransactionID + "1" + res_ts + PAYSECRETKEY
            ord_dict['mTransactionID'] = mTransactionID
            ord_dict['returnCode'] = '1'
            ord_dict['ts'] = res_ts
            ord_dict['checksum'] = sha1(cs.encode('utf-8')).hexdigest()
            paymentStore.transactionStatus = transactionStatus
            paymentStore.save()
            return Response(ord_dict, status=200)


class BookingCancellationViewSet(APIView):
    @staticmethod
    def post(request, key=None):
        if key:
            pk = base64.b64decode(key).decode('ascii')
            booked = get_or_none(BookedTeeTime, pk=pk)
            if booked:
                handle_cancel_booking(booked.teetime.id)
                return Response({'status': '200', 'code': 'OK',
                                 'detail': 'OK'}, status=200)
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found'}, status=404)

    @staticmethod
    def get(request, key=None):

        if key:
            pk = base64.b64decode(key).decode('ascii')
            teetime = get_or_none(BookedTeeTime, pk=pk)

            if teetime:
                serializer = BookedTeeTimeSerializer(teetime)
                data = get_booked_buggy_caddy(teetime.id)
                if data:
                    serializer.data.update(data)
                    st = GolfCourseBookingSetting.objects.filter(golfcourse=teetime.golfcourse).first()
                    if st:
                        serializer.data.update({'policy': st.policy, 'policy_en': st.policy_en})
                try:
                    country_code = teetime.golfcourse.country.short_name

                    if country_code != '':
                        tz = timezone(country_timezones(teetime.golfcourse.country.short_name)[0])
                    if tz:
                        time_now = django_timezone.make_aware(datetime.datetime.now(), tz)
                        teetime_milisecond = serializer.data['teetime_date'] + serializer.data['teetime_time']
                        teetime_timestamp = int(teetime_milisecond / 1000)
                        teetime_time = datetime.datetime.fromtimestamp(int(teetime_timestamp), pytz.utc)
                        cancel_hour = 0
                        try:
                            setting = GolfCourseBookingSetting.objects.get(golfcourse=teetime.golfcourse)
                            cancel_hour = setting.cancel_hour
                        except Exception:
                            pass
                        valid_time = teetime_time - timedelta(hours=int(cancel_hour))
                        if valid_time < time_now:
                            serializer.data.update({'cancel_hour': int(cancel_hour / 24)})
                            return Response({'status': '200', 'code': 'E_EXPIRED_TEETIME',
                                             'detail': serializer.data, }, status=200)
                except Exception as e:
                    pass
                return Response({'status': '200', 'code': 'OK',
                                 'detail': serializer.data}, status=200)
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found'}, status=404)


class BookingUpdateViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = BookedTeeTimeSerializer

    @staticmethod
    def put(request):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        data = request.DATA
        booked = BookedTeeTime.objects.get(pk=data['id'])

        if not booked:
            return Response({'code': 'ERR_NOT_FOUND'}, status=400)
        booked_buggy = get_or_none(BookedBuggy, teetime=data['id'])
        booked_caddy = get_or_none(BookedCaddy, teetime=data['id'])
        checkin = request.DATA.get('checkin', None)
        player_checkin_count = request.DATA.get('player_checkin_count', None)
        buggy_quantity = request.DATA.get('buggy_qty', None)
        caddy_quantity = request.DATA.get('caddy_qty', None)
        total_cost = request.DATA.get('total_cost', None)
        voucher_discount_amount = 0
        booked_buggy_quantity = 0
        booked_caddy_quantity = 0
        if checkin is not None:
            if checkin == 1:
                booked.status = 'I'
                voucher_codes = request.DATA.get('voucher', None)
                if voucher_codes:
                    vc = voucher_codes.split(',')
                    used_voucher_code = []
                    if booked.voucher_code:
                        used_voucher_code = booked.voucher_code.split(',')
                    valid_voucher = []
                    for voucher_code in vc:
                        if voucher_code not in valid_voucher:
                            valid_voucher.append(voucher_code)
                        else:
                            return Response({'code': 'ERR_DUPLICATE_VOUCHER', 'detail': 'Duplicate voucher'},
                                            status=400)
                    for voucher_code in vc:
                        voucher = Voucher.objects.filter(code=voucher_code.upper()).first()
                        if not voucher:
                            return Response({'code': 'ERR_VOUCHER_NOT_FOUND', 'detail': 'Invalid voucher'}, status=400)
                        if voucher.is_used is True and voucher_code not in used_voucher_code:
                            return Response({'code': 'ERR_VOUCHER_ALREADY_USED', 'detail': 'Voucher was already used'},
                                            status=400)
                        voucher_discount_amount += voucher.discount_amount
                        voucher.is_used = True
                        voucher.save()

                    for voucher_code in used_voucher_code:
                        if voucher_code not in vc:
                            Voucher.objects.filter(code=voucher_code.upper()).update(is_used=False)

                    booked.voucher_code = voucher_codes
                if total_cost:
                    booked.total_cost = Decimal(total_cost)
                hole = booked.hole
                if buggy_quantity:
                    if booked_buggy:
                        booked_buggy_quantity = booked_buggy.quantity
                        booked_buggy.quantity = int(buggy_quantity)
                        booked_buggy.save()
                    else:
                        booked_buggy_quantity = 0
                        # bg = get_or_none(GolfCourseBuggy, golfcourse=booked.golfcourse, buggy=1)
                        bg = None
                        bp = GolfCourseBuggy.objects.filter(golfcourse=self.teetime.golfcourse,
                                                            from_date__lte=self.teetime.date,
                                                            to_date__gte=self.teetime.date, buggy=1).distinct(
                            'buggy').order_by('buggy', 'id')
                        if bp.exists() and bp:
                            bg = bp[0]
                        b_price = 0.0
                        if bg:
                            if hole == 9:
                                b_price = bg.price_9
                            elif hole == 18:
                                b_price = bg.price_18
                            elif hole == 27:
                                b_price = bg.price_27
                            else:
                                b_price = bg.price_36
                        bb = BookedBuggy.objects.create(teetime=booked, buggy=bg, quantity=buggy_quantity,
                                                        amount=b_price)

                if caddy_quantity:
                    if booked_caddy:
                        booked_caddy_quantity = booked_caddy.quantity
                        booked_caddy.quantity = int(caddy_quantity)
                        booked_caddy.save()
                    else:
                        booked_caddy_quantity = 0
                        bg = get_or_none(GolfCourseCaddy, golfcourse=booked.golfcourse)
                        b_price = 0.0
                        if bg:
                            if hole == 9:
                                b_price = bg.price_9
                            elif hole == 18:
                                b_price = bg.price_18
                            elif hole == 27:
                                b_price = bg.price_27
                            else:
                                b_price = bg.price_36
                        bc = BookedCaddy.objects.create(teetime=booked, caddy=bg, quantity=caddy_quantity,
                                                        amount=b_price)
                booked.paid_amount = booked.total_cost
                booked.player_checkin_count = booked.player_count

            elif checkin == 0:
                booked.status = 'PP' if booked.payment_status else 'PU'
                booked.player_checkin_count = 0
                booked.paid_amount = 0
        booked_buggy = get_or_none(BookedBuggy, teetime=data['id'])
        booked_caddy = get_or_none(BookedCaddy, teetime=data['id'])
        teetime_price = get_or_none(TeeTimePrice, teetime_id=booked.teetime.id, hole=booked.hole)
        teetime_price2 = get_or_none(TeeTimePrice, teetime_id=booked.teetime.id, hole=18)
        discount = float(booked.discount) or float(teetime_price2.online_discount)
        green_fee = float(teetime_price.price)
        tb = 0
        tc = 0
        if booked_buggy:
            tb = booked_buggy.quantity * booked_buggy.amount
        if booked_caddy:
            tc = booked_caddy.quantity * booked_caddy.amount
        if player_checkin_count is not None:
            booked.player_checkin_count = player_checkin_count
            booked.paid_amount = Decimal(green_fee * (100 - discount) * player_checkin_count / 100) + tb + tc
        booked.paid_amount -= Decimal(voucher_discount_amount)
        booked.save()
        return Response({'code': 'SUCCESS'}, status=200)


class BookingReportViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = BookedTeeTimeSerializer

    @staticmethod
    def get(request):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        now = datetime.datetime.now()
        # GET request data
        from_date = request.QUERY_PARAMS.get('from_date')
        if not from_date:
            from_date = datetime.datetime.strftime(now.date(), '%Y-%m-%d')
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        to_date = request.QUERY_PARAMS.get('to_date')
        if to_date:
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        # End
        filter_condition = {
            'date__gte': from_date,
            'date__lte': to_date,
            'golfcourse_id': golfstaff.golfcourse_id,
            'is_booked': True
        }
        # set argument for filter condition
        arguments = {}
        for k, v in filter_condition.items():
            if v:
                arguments[k] = v
        # end
        tt = TeeTime.objects.filter(Q(**arguments)).order_by('id').values('id')
        bookedtt = BookedTeeTime.objects.filter(Q(teetime_id__in=tt)).exclude(payment_type='F',
                                                                              payment_status=False).order_by('id')
        resp = BookedTeeTimeSerializer(bookedtt)
        data = resp.data
        return Response(data, status=200)


class BookingGCViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = BookedGCSerializer

    @staticmethod
    def get(request):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        now = datetime.datetime.now()
        # GET request data
        from_date = request.QUERY_PARAMS.get('from_date')
        if not from_date:
            from_date = datetime.datetime.strftime(now.date(), '%Y-%m-%d')
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        to_date = request.QUERY_PARAMS.get('to_date')
        if to_date:
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        # End
        filter_condition = {
            'date__gte': from_date,
            'date__lte': to_date
        }
        # set argument for filter condition
        arguments = {}
        for k, v in filter_condition.items():
            if v:
                arguments[k] = v
        # end
        tt = TeeTime.objects.filter(Q(**arguments)).order_by('id').values('id')
        bookedtt = BookedTeeTime.objects.filter(Q(teetime_id__in=tt)).order_by('id')
        resp = BookedGCSerializer(bookedtt)
        data = resp.data
        return Response(data, status=200)


class CancelReportViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = BookedTeeTime_HistorySerializer

    @staticmethod
    def get(request):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        now = datetime.datetime.now()
        # GET request data
        from_date = request.QUERY_PARAMS.get('from_date')
        if not from_date:
            from_date = datetime.datetime.strftime(now.date(), '%Y-%m-%d')
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        to_date = request.QUERY_PARAMS.get('to_date')
        if to_date:
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        filter_condition = {
            'date__gte': from_date,
            'date__lte': to_date
        }
        arguments = {}
        for k, v in filter_condition.items():
            if v:
                arguments[k] = v
        # end
        tt = TeeTime.objects.filter(Q(**arguments)).order_by('id').values('id')
        bookedtt = BookedTeeTime_History.objects.filter(Q(teetime_id__in=tt)).order_by('id')
        resp = BookedTeeTime_HistorySerializer(bookedtt)
        data = resp.data
        return Response(data, status=200)


class ReportViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = BookedTeeTimeSerializer

    @staticmethod
    def get(request):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)

        now = datetime.datetime.now()
        # GET request data
        from_date = request.QUERY_PARAMS.get('from_date')
        if not from_date:
            from_date = datetime.datetime.strftime(now.date(), '%Y-%m-%d')
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        to_date = request.QUERY_PARAMS.get('to_date')
        if to_date:
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        # End
        filter_condition = {
            'date__gte': from_date,
            'date__lte': to_date,
            'golfcourse_id': golfstaff.golfcourse_id,
            'is_booked': True
        }
        # set argument for filter condition
        arguments = {}
        for k, v in filter_condition.items():
            if v:
                arguments[k] = v
        # end
        tt = TeeTime.objects.filter(Q(**arguments)).order_by('id').values('id')
        bookedtt = BookedTeeTime.objects.filter(Q(teetime_id__in=tt)).order_by('id')
        resp = ComissionSerializer(bookedtt)
        gc24_price = Gc24TeeTimePrice.objects.order_by('-created').filter(golfcourse_id=golfstaff.golfcourse_id,
                                                                          date__lte=from_date).first()
        data = resp.data
        if data:
            for d in data:
                teetime_price = get_or_none(TeeTimePrice, teetime_id=d['teetime_id'], hole=d['hole'])
                teetime_price2 = get_or_none(TeeTimePrice, teetime_id=d['teetime_id'], hole=18)
                bookedbuggy = get_or_none(BookedBuggy, teetime=d['id'])
                bookedbuggy_price = 0
                bookedbuggy_quantity = 0
                buggy_price_standard = 0
                if bookedbuggy:
                    bookedbuggy_price = bookedbuggy.amount
                    bookedbuggy_quantity = bookedbuggy.quantity
                    k = "price_standard_{0}".format(d['hole'])
                    buggy_price_standard = getattr(bookedbuggy.buggy, k)

                key = "GC24_hole_{0}".format(d['hole'])
                discount = float(d['discount']) or float(teetime_price2.online_discount)
                d['price'] = float(teetime_price.price) * (
                100 - discount) / 100 if teetime_price and teetime_price.price else 0
                d['bookedbuggy_price'] = bookedbuggy_price
                d['bookedbuggy_quantity'] = bookedbuggy_quantity
                d['buggy_price_standard'] = buggy_price_standard
                d.update({
                    'price_9_wd': gc24_price.price_9_wd if gc24_price else 0,
                    'price_18_wd': gc24_price.price_18_wd if gc24_price else 0,
                    'price_27_wd': gc24_price.price_27_wd if gc24_price else 0,
                    'price_36_wd': gc24_price.price_36_wd if gc24_price else 0,
                    'price_9_wk': gc24_price.price_9_wk if gc24_price else 0,
                    'price_18_wk': gc24_price.price_18_wk if gc24_price else 0,
                    'price_27_wk': gc24_price.price_27_wk if gc24_price else 0,
                    'price_36_wk': gc24_price.price_36_wk if gc24_price else 0,
                })

                try:
                    if datetime.datetime.fromtimestamp(d['teetime_date'] / 1e3).weekday() in range(0, 5):
                        tod = 'wd'
                    else:
                        tod = 'wk'
                    price_key = 'price_' + str(d['hole']) + '_' + tod
                    d['variance'] = (float(d['price']) - float(d[price_key])) * int(d['player_count']) + (float(
                        d['bookedbuggy_price']) - float(d['buggy_price_standard'])) * int(d['bookedbuggy_quantity'])
                except:
                    d['variance'] = 0
                # Update gc 24 price

        return Response(data, status=200)


class BookingGolfcourseViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = BookedTeeTimeSerializer

    @staticmethod
    def get(request):
        country = request.QUERY_PARAMS.get('country', None)
        filter_condition = {'is_booked': False, 'is_request': False, 'is_block': False}
        if country:
            filter_condition.update({'golfcourse__country__short_name': country})
        golfcourse_list = TeeTime.objects.filter(Q(**filter_condition)).values_list('golfcourse_id',
                                                                                    flat=True).distinct()
        data = GolfCourse.objects.filter(pk__in=golfcourse_list)
        resp = BookingGolfcourseSerializer(data)
        return Response(resp.data, status=200)


class HoldTeetimes(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = TeeTimeSerializer

    @staticmethod
    def get(request):
        id = request.QUERY_PARAMS.get('id')
        is_hold = bool(int(request.QUERY_PARAMS.get('is_hold')))
        teetime = get_or_none(TeeTime, pk=id, is_hold=not is_hold, is_block=False, is_booked=False, is_request=False)
        timer = get_or_none(BookingSetting, code='HOLD_TIMER')
        if teetime:
            channel = 'booking-' + teetime.date.strftime('%Y-%m-%d')
            msg = {
                "id": teetime.id,
                "is_hold": is_hold
            }
            if is_hold == True:
                ts = datetime.datetime.utcnow().replace(tzinfo=utc) + datetime.timedelta(0, int(timer.value))
                teetime.hold_expire = ts
                msg['expire'] = round(ts.timestamp() * 1000)
            else:
                teetime.hold_expire = None
            msg = json.dumps(msg)
            redis_server.publish(channel, msg)
            teetime.is_hold = is_hold
            teetime.save()
            #######  exec task un-hold after timer
            if is_hold is True:
                task_auto_expire_holding.apply_async(args=[teetime.id], countdown=int(timer.value))
        else:
            return Response({'status': '200', 'code': 'ok'}, status=200)
        return Response({'status': '200', 'code': 'ok'}, status=200)


def handle_request_teetime(request, pk):
    bookedteetime = get_or_none(BookedTeeTime, pk=pk)
    if bookedteetime:
        #### Accept all payment
        if bookedteetime.status == 'PP':
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Paid already'}, status=404)
        else:
            ip = get_client_ip(request)
            headers = {
                'content-type': 'application/json',
                'accept': 'application/json',
            }
            bookedpartner = BookedPartner.objects.get(bookedteetime_id=bookedteetime.id)
            customer = Customer.objects.get(id=bookedpartner.customer_id)
            description = 'Please select your preferred card to pay'
            description = description.encode('ascii', 'ignore').decode('ascii')
            values = OrderedDict()
            values['mTransactionID'] = str(int(datetime.datetime.utcnow().timestamp())) + 't' + str(
                bookedteetime.id)  #### Tuan Ly: need replace
            values['merchantCode'] = PAYMERCHANTCODE
            values['bankCode'] = '123PAY'
            values['totalAmount'] = str(int(bookedteetime.total_cost))
            values['clientIP'] = ip
            values['custName'] = customer.name
            values['custAddress'] = extract_email(customer.email)
            values['custGender'] = 'M'
            values['custDOB'] = ''
            values['custPhone'] = extract_nbr(str(customer.phone_number))
            values['custMail'] = extract_email(customer.email)
            values['description'] = description
            url = ''
            if request.user_agent.browser.family == "Apache-HttpClient" or request.user_agent.browser.family == "CFNetwork":
                url = 'golfpay123://booking-request/t' + str(bookedteetime.id) + '/'
            else:
                url = 'https://' + fn_getHostname(request) + '/#/successBooking/t' + str(bookedteetime.id) + '/'
            print(url)
            values['cancelURL'] = url
            values['redirectURL'] = url
            values['errorURL'] = url
            values['passcode'] = PAYPASSCODE
            cs = values['mTransactionID'] + values['merchantCode'] + values['bankCode'] + values['totalAmount']
            cs += values['clientIP'] + values['custName'] + values['custAddress'] + values['custGender']
            cs += values['custDOB'] + values['custPhone'] + values['custMail'] + values['cancelURL']
            cs += values['redirectURL'] + values['errorURL'] + values['passcode'] + PAYSECRETKEY
            hashed = sha1(cs.encode('utf-8'))
            values['checksum'] = hashed.hexdigest()
            values['addInfo'] = ''
            conn = http.client.HTTPSConnection(PAYURL)
            v = json.dumps(values)
            pay_url = "/createOrder1"
            if CURRENT_ENV == 'prod':
                pay_url = "/createOrder1"
            else:
                pay_url = "/miservice/createOrder1"
            conn.request('POST', pay_url, v, headers)
            res = conn.getresponse()
            response_tuanly = json.loads(res.read().decode('utf-8'))
            print(response_tuanly)
            returnCode = response_tuanly[0]
            if not (int(returnCode) == 1):
                raise ParseError('Cannot create pay order: {}'.format(response_tuanly))
            payTransactionid = response_tuanly[1]
            redirectURL = response_tuanly[2]
            res_cs = returnCode + payTransactionid + redirectURL + PAYSECRETKEY
            checksum = response_tuanly[3]
            res_hashed = sha1(res_cs.encode('utf-8')).hexdigest()
            if not (checksum == res_hashed):
                raise ParseError('Invalid checksum')
            payStore = PayTransactionStore.objects.create(payTransactionid=payTransactionid,
                                                          transactionId=values['mTransactionID'],
                                                          totalAmount=values['totalAmount'],
                                                          description=values['description'],
                                                          clientIP=values['clientIP'],
                                                          vendor=VNG)
            response_tuanly[0] = ""
            response_tuanly[1] = ""
            response_tuanly[3] = ""
            return Response({'status': '200', 'code': 'SUCCESS',
                             'detail': response_tuanly}, status=200)
    else:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found'}, status=404)


def handle_request_noncheck(request, pk):
    booked = get_or_none(BookedPayonlineLink, pk=pk)
    if booked:
        ip = get_client_ip(request)
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json',
        }
        values = OrderedDict()
        values['mTransactionID'] = str(int(datetime.datetime.utcnow().timestamp())) + 'n' + str(booked.id)
        values['merchantCode'] = PAYMERCHANTCODE
        values['bankCode'] = '123PAY'
        values['totalAmount'] = booked.totalAmount
        values['clientIP'] = ip
        values['custName'] = booked.custName
        values['custAddress'] = booked.custAddress
        values['custGender'] = 'M'
        values['custDOB'] = ''
        values['custPhone'] = extract_nbr(str(booked.custPhone))
        values['custMail'] = extract_email(booked.custMail)
        values['description'] = booked.description
        url = ''
        if request.user_agent.browser.family == "Apache-HttpClient" or request.user_agent.browser.family == "CFNetwork":
            url = 'golfpay123://booking-request/n' + str(booked.id) + '/'
        else:
            url = 'https://' + fn_getHostname(request) + '/#/successBooking/n' + str(booked.id) + '/'
        values['cancelURL'] = url
        values['redirectURL'] = url
        values['errorURL'] = url
        values['passcode'] = PAYPASSCODE
        cs = values['mTransactionID'] + values['merchantCode'] + values['bankCode'] + values['totalAmount']
        cs += values['clientIP'] + values['custName'] + values['custAddress'] + values['custGender']
        cs += values['custDOB'] + values['custPhone'] + values['custMail'] + values['cancelURL']
        cs += values['redirectURL'] + values['errorURL'] + values['passcode'] + PAYSECRETKEY
        hashed = sha1(cs.encode('utf-8'))
        values['checksum'] = hashed.hexdigest()
        values['addInfo'] = ''
        conn = http.client.HTTPSConnection(PAYURL)
        v = json.dumps(values)
        pay_url = "/createOrder1"
        if CURRENT_ENV == 'prod':
            pay_url = "/createOrder1"
        else:
            pay_url = "/miservice/createOrder1"
        conn.request('POST', pay_url, v, headers)
        res = conn.getresponse()
        response_tuanly = json.loads(res.read().decode('utf-8'))
        print(response_tuanly)
        returnCode = response_tuanly[0]
        if not (int(returnCode) == 1):
            raise ParseError('Cannot create pay order: {}'.format(response_tuanly))
        payTransactionid = response_tuanly[1]
        redirectURL = response_tuanly[2]
        res_cs = returnCode + payTransactionid + redirectURL + PAYSECRETKEY
        checksum = response_tuanly[3]
        res_hashed = sha1(res_cs.encode('utf-8')).hexdigest()
        if not (checksum == res_hashed):
            raise ParseError('Invalid checksum')
        payStore = PayTransactionStore.objects.create(payTransactionid=payTransactionid,
                                                      transactionId=values['mTransactionID'],
                                                      totalAmount=values['totalAmount'],
                                                      description=values['description'],
                                                      clientIP=values['clientIP'],
                                                      vendor=VNG)
        response_tuanly[0] = ""
        response_tuanly[1] = ""
        response_tuanly[3] = ""
        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': response_tuanly}, status=200)
    else:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found'}, status=404)


class BookingRequest(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = TeeTimeSerializer

    @staticmethod
    def get(request, key=None):
        if key:
            pk = base64.b64decode(key).decode('ascii')
            if 't' in pk:
                result = handle_request_teetime(request, pk[1:])
            elif RepresentsInt(pk):
                result = handle_request_teetime(request, pk)
            elif 'n' in pk:
                result = handle_request_noncheck(request, pk[1:])
            else:
                result = Response({'status': '404', 'code': 'E_NOT_FOUND',
                                   'detail': 'Not found'}, status=404)
            return result
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'Not found'}, status=404)


class BookingHandler(object):
    def __init__(self, **data):
        self.payment_type = 'N'
        self.name = None
        self.email = None
        self.phone = None
        self.player_count = 0
        self.buggy = 1
        self.buggy_qty = 0
        self.buggy_price = 0
        self.bg = None
        self.caddy_qty = 0
        self.caddy_price = 0
        self.cd = None
        self.discount = 0
        self.hole = 18
        self.total_cost = 0
        self.user = None
        self.CurrencyCode = None
        self.CurrencyValue = 0
        self.back_link = None
        self.__dict__.update(data)
        self.teetime = get_or_none(TeeTime, pk=self.id, is_block=False, is_booked=False, is_request=False)
        self.domain = None
        self.booked = None
        self.booked_buggy = None
        self.booked_caddy = None
        self.clientIP = '127.0.0.1'
        self.request = None
        self.voucher = ""
        self.voucher_discount_amount = 0

    def set_client_ip(self, ip):
        self.clientIP = ip

    def set_request(self, request):
        self.request = request

    def __initial_data(self):
        gtype = GuestType.objects.get(name='G')
        self.teetime_price = get_or_none(TeeTimePrice, teetime_id=self.id, hole=18, guest_type_id=gtype.id,
                                         is_publish=True)
        self.teetime_price2 = get_or_none(TeeTimePrice, teetime_id=self.id, hole=self.hole)
        tz = timezone(country_timezones(self.teetime.golfcourse.country.short_name)[0])
        now = datetime.datetime.utcnow()
        self.current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
        self.customer = Customer.objects.create(name=self.name, email=self.email, phone_number=self.phone)
        self.__verify_follow_data()

    def __verify_follow_data(self):
        if not self.teetime_price2:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError("None price")
        if not self.teetime_price:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError("None price")

    def notify_lock(self, status):
        channel = 'booking-' + str(self.teetime.date)
        msg = {
            "id": self.teetime.id,
            "is_block": status
        }
        d = json.dumps(msg)
        redis_server.publish(channel, d)

    def set_user_type(self, user_type):
        self.user = user_type

    def unlock_teetime(self):
        self.teetime.is_request = self.teetime.is_booked = self.teetime.is_hold = False
        self.teetime.hold_expire = None
        self.teetime.save()
        if self.customer:
            self.customer.delete()
        if self.booked:
            self.booked.delete()

    def verify_data(self):
        if not self.teetime:
            raise ParseError("Teetime is booked")
        if self.payment_type == 'N':
            self.teetime.is_request = True
            self.teetime.save()
        else:
            self.teetime.is_booked = True
            self.teetime.save()
        self.notify_lock(True)
        try:
            self.buggy = int(self.buggy)
            self.buggy_qty = int(self.buggy_qty)
            self.caddy_qty = int(self.caddy_qty)
            self.discount = float(self.discount)
            self.hole = int(self.hole)
            self.player_count = int(self.player_count)
        except:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError("Invalid field type")
        if self.hole not in [9, 18, 27, 36]:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError("Invalid hole")
        if not self.name or not self.phone:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError("Invalid name_phone")
        self.__initial_data()

    def validate_discount(self, discount):
        discount_cash = float(self.teetime_price.online_discount) or 0
        discount_online = float(self.teetime_price.cash_discount) or 0
        discount_additional = 0 if self.payment_type == 'N' else discount_online
        discount_deal = 0
        current_tz = self.current_tz
        teetimedatetime = datetime.datetime.combine(self.teetime.date, self.teetime.time) + datetime.timedelta(
            minutes=15)
        if current_tz.replace(tzinfo=None) > teetimedatetime:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError("Invalid teetime")
        filter_deal = {
            'teetime': self.id,
            'bookingtime__deal__active': True,
            'bookingtime__deal__is_base': False,
            'bookingtime__date': current_tz.date(),
            'bookingtime__from_time__lte': current_tz.time(),
            'bookingtime__to_time__gte': current_tz.time()
        }

        filter_exclude1 = {
            'bookingtime__deal__effective_date': current_tz.date(),
            'bookingtime__deal__effective_time__gte': current_tz.time()
        }
        filter_exclude2 = {
            'bookingtime__deal__expire_date': current_tz.date(),
            'bookingtime__deal__expire_time__lte': current_tz.time()
        }
        deal_teetime = DealEffective_TeeTime.objects.filter(Q(**filter_deal)).exclude(
            Q(**filter_exclude1) | Q(**filter_exclude2)).order_by('-modified')
        if deal_teetime.exists() and deal_teetime:
            discount_deal = deal_teetime[0].discount
        error_code = 0
        if discount_deal:
            disc = discount_deal + discount_additional
            error_code = 101
        else:
            disc = discount_cash + discount_additional
            error_code = 102
        if disc != discount:
            self.notify_lock(False)
            self.unlock_teetime()
            if error_code == 102:
                raise ParseError('discount_deal_end')
            else:
                raise ParseError('discount_deal_start')

    def __get_buggy_caddy_price(self):
        key = "price_{}".format(self.hole)
        self.bg = None
        bp = GolfCourseBuggy.objects.filter(golfcourse=self.teetime.golfcourse, from_date__lte=self.teetime.date,
                                            to_date__gte=self.teetime.date, buggy=1).distinct('buggy').order_by('buggy',
                                                                                                                'id')
        if bp.exists() and bp:
            self.bg = bp[0]
        # self.bg = get_or_none(GolfCourseBuggy, golfcourse=self.teetime.golfcourse, buggy=self.buggy)
        if self.bg:
            try:
                self.buggy_price = float(getattr(self.bg, key))
            except:
                pass
        self.cd = get_or_none(GolfCourseCaddy, golfcourse=self.teetime.golfcourse)
        if self.cd:
            try:
                self.caddy_price = float(getattr(self.cd, key))
            except:
                pass

    def check_voucher(self, voucher_codes):
        voucher_discount_amount = 0
        now = datetime.datetime.now()
        if voucher_codes:
            vc = voucher_codes.split(',')
            used_voucher_code = []
            valid_voucher = []
            for voucher_code in vc:
                if voucher_code not in valid_voucher:
                    valid_voucher.append(voucher_code)
                else:
                    return ("", 0)
            for voucher_code in vc:
                voucher = Voucher.objects.filter(code=voucher_code.upper(), from_date__lte=now,
                                                 to_date__gte=now).first()
                if not voucher:
                    return ("", 0)
                if voucher.is_used is True and voucher_code not in used_voucher_code:
                    return ("", 0)
                voucher_discount_amount += voucher.discount_amount
            return (voucher_codes, voucher_discount_amount)
        return ("", 0)

    def validate_totalcost(self, total_cost):
        voucher_codes = self.request.DATA.get('voucher', None)
        self.voucher, self.voucher_discount_amount = self.check_voucher(voucher_codes)
        pricePerOne = float(self.teetime_price2.price)
        payment = pricePerOne * self.player_count
        payment = payment * (100 - self.discount) / 100
        payment += self.buggy_price * self.buggy_qty + self.caddy_price * self.caddy_qty
        payment -= self.voucher_discount_amount
        if not (int(payment) == int(total_cost) or float(payment) == float(total_cost)):
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError('Invalid total cost')

    def handle_booking(self, domain):
        self.domain = domain
        self.__get_buggy_caddy_price()
        self.validate_discount(self.discount)
        self.validate_totalcost(self.total_cost)
        self.total_cost = int(self.total_cost)
        if self.payment_type == 'N':
            return self.__booking_with_paygolfcourse()
        else:
            return self.__booking_with_onlinepayment()

    def __booking_with_paygolfcourse(self):
        self.__booking_handle()
        self.__send_email_request()
        serializer = BookedTeeTimeSerializer(self.booked)
        str_booked_id = 't' + str(self.booked.id)
        encode_data = base64.urlsafe_b64encode(str_booked_id.encode('ascii')).decode('ascii')
        request_url = 'https://' + self.domain + '#/booking-request/payment/' + str(encode_data) + '/'
        serializer.data.update({
            'buggy_type': self.buggy,
            'buggy_qty': self.buggy_qty,
            'caddy_qty': self.caddy_qty,
            'pay_now_url': request_url
        })
        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': serializer.data}, status=200)

    def __booking_with_onlinepayment(self):
        self.__booking_handle()
        return self.__send_paymentonline_order()

    def __booking_handle(self):
        try:
            invoice_name = ""
            invoice_tax = ""
            invoice_coaddress = ""
            invoice_address = ""
            if 'invoice' in self.__dict__.keys():
                invoice_name = self.invoice['name']
                invoice_tax = self.invoice['tax_code']
                invoice_coaddress = self.invoice['company_address']
                invoice_address = self.invoice['invoice_address']
            user_agent = self.request.user_agent.browser.family
            if user_agent == "Apache-HttpClient":
                ua_device = 'and'
            elif user_agent == "CFNetwork":
                ua_device = 'ios'
            else:
                ua_device = 'web'
            self.booked = BookedTeeTime.objects.create(teetime_id=self.teetime.id,
                                                       golfcourse_id=self.teetime.golfcourse_id,
                                                       player_count=self.player_count,
                                                       total_cost=self.total_cost,
                                                       hole=self.hole,
                                                       discount=self.discount,
                                                       payment_type=self.payment_type,
                                                       invoice_name=invoice_name,
                                                       invoice_address=invoice_address,
                                                       company_address=invoice_coaddress,
                                                       tax_code=invoice_tax,
                                                       user_device=ua_device,
                                                       currencyCode=self.CurrencyCode,
                                                       currencyValue=self.CurrencyValue,
                                                       back_link=self.back_link
                                                       )
        except Exception as e:
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError(e)
        if self.user and self.user.is_authenticated:
            BookedPartner.objects.create(bookedteetime_id=self.booked.id,
                                         customer_id=self.customer.id,
                                         user_id=self.user.id)
        else:
            BookedPartner.objects.create(bookedteetime_id=self.booked.id,
                                         customer_id=self.customer.id)
        if self.buggy_qty:
            if self.bg:
                self.booked_buggy = BookedBuggy.objects.create(teetime=self.booked, buggy=self.bg,
                                                               quantity=self.buggy_qty, amount=self.buggy_price)
        if self.caddy_qty:
            if self.cd:
                self.booked_caddy = BookedCaddy.objects.create(teetime=self.booked, caddy=self.cd,
                                                               quantity=self.caddy_qty, amount=self.caddy_price)
        encode_data = base64.urlsafe_b64encode(str(self.booked.id).encode('ascii')).decode('ascii')
        uri = 'https://' + self.domain + '/#/checkin/' + encode_data
        url = pyqrcode.create(uri)
        url.png('media/qr_codes/' + encode_data + '.png', scale=6)
        with open('media/qr_codes/' + encode_data + '.png', "rb") as f:
            data = f.read()
            qr_base64 = base64.b64encode(data)
        qr_base64 = qr_base64.decode('utf-8')
        self.booked.qr_base64 = qr_base64
        self.booked.qr_url = 'https://' + self.domain + '/api/media/qr_codes/' + encode_data + '.png'
        self.booked.voucher_code = self.voucher
        self.booked.voucher_discount_amount = self.voucher_discount_amount
        self.booked.save()
        if self.voucher:
            used_voucher_code = self.voucher.split(',')
            for voucher_code in used_voucher_code:
                vc = Voucher.objects.filter(code=voucher_code.upper())
                if vc.exists():
                    for v in vc:
                        v.is_used = True
                        v.save()

    def __send_email_request(self):
        send_email_task.delay(self.booked.id, self.domain, 'R')

    def __send_paymentonline_order(self):
        vendor = GC24BookingVendor.objects.all()[0]
        if vendor:
            bookingvendor = vendor.booking_vendor
        else:
            bookingvendor = VNG
        response_tuanly = self.__send_paymentonline_order_vng()
        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': response_tuanly}, status=200)

    def __send_paymentonline_order_vng(self):
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json',
        }
        if self.CurrencyCode and self.CurrencyCode != 'VND':
            description = 'Please select your preferred card to pay for {0} {1}'.format(self.CurrencyCode,
                                                                                        self.CurrencyValue)
        else:
            description = 'Please select your preferred card to pay'
        description = description.encode('ascii', 'ignore').decode('ascii')
        values = OrderedDict()
        values['mTransactionID'] = 't' + str(self.booked.id)  #### Tuan Ly: need replace
        values['merchantCode'] = PAYMERCHANTCODE
        values['bankCode'] = '123PAY'
        values['totalAmount'] = str(self.total_cost)
        values['clientIP'] = self.clientIP
        values['custName'] = self.name
        values['custAddress'] = extract_email(self.email)
        values['custGender'] = 'M'
        values['custDOB'] = ''
        values['custPhone'] = extract_nbr(str(self.phone))
        values['custMail'] = extract_email(self.email)
        values['description'] = description
        url = ''
        request = self.request
        print(request.user_agent.browser.family)
        if request.user_agent.browser.family == "Apache-HttpClient" or request.user_agent.browser.family == "CFNetwork":
            url = 'golfpay123://booking-request/t' + str(self.booked.id) + '/'
        else:
            url = 'https://' + self.domain + '/#/successBooking/t' + str(self.booked.id) + '/'
        print(url)
        values['cancelURL'] = url
        values['redirectURL'] = url
        values['errorURL'] = url
        values['passcode'] = PAYPASSCODE
        cs = values['mTransactionID'] + values['merchantCode'] + values['bankCode'] + values['totalAmount']
        cs += values['clientIP'] + values['custName'] + values['custAddress'] + values['custGender']
        cs += values['custDOB'] + values['custPhone'] + values['custMail'] + values['cancelURL']
        cs += values['redirectURL'] + values['errorURL'] + values['passcode'] + PAYSECRETKEY
        hashed = sha1(cs.encode('utf-8'))
        values['checksum'] = hashed.hexdigest()
        values['addInfo'] = ''
        conn = http.client.HTTPSConnection(PAYURL)
        v = json.dumps(values)
        print(v)
        pay_url = "/createOrder1"
        default_language = "&lang=en"
        if CURRENT_ENV == 'prod':
            pay_url = "/createOrder1"
        else:
            default_language = ""
            pay_url = "/miservice/createOrder1"
        conn.request('POST', pay_url, v, headers)
        res = conn.getresponse()
        response_tuanly = json.loads(res.read().decode('utf-8'))
        print(response_tuanly)
        returnCode = response_tuanly[0]
        if not (int(returnCode) == 1):
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError('Cannot create pay order: {}'.format(response_tuanly))
        payTransactionid = response_tuanly[1]
        redirectURL = response_tuanly[2]
        res_cs = returnCode + payTransactionid + redirectURL + PAYSECRETKEY
        checksum = response_tuanly[3]
        res_hashed = sha1(res_cs.encode('utf-8')).hexdigest()
        if not (checksum == res_hashed):
            self.notify_lock(False)
            self.unlock_teetime()
            raise ParseError('Invalid checksum')
        payStore = PayTransactionStore.objects.create(payTransactionid=payTransactionid,
                                                      transactionId="t{0}".format(self.booked.id),
                                                      totalAmount="{0}".format(self.total_cost),
                                                      description=values['description'],
                                                      clientIP=self.clientIP,
                                                      vendor=VNG)
        response_tuanly[0] = ""
        response_tuanly[1] = ""
        response_tuanly[2] = response_tuanly[2] + default_language
        response_tuanly[3] = ""
        return response_tuanly


class GetTeetimes(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = TeeTimeSerializer

    @staticmethod
    def post(request):
        data = request.DATA
        try:
            value = int(data['id'])
        except:
            raise ValidationError("Invalid teetime")
        handler = BookingHandler(**data)
        handler.verify_data()
        user = request.user
        handler.set_client_ip(get_client_ip(request))
        handler.set_user_type(user)
        handler.set_request(request)
        return handler.handle_booking(fn_getHostname(request))

    @staticmethod
    def get(request):
        date = request.QUERY_PARAMS.get('date', '')
        city = int(request.QUERY_PARAMS.get('city', '-1'))
        golfcourse = request.QUERY_PARAMS.get('golfcourse', '-1')
        from_time = request.QUERY_PARAMS.get('from_time', '05:30:00')
        country_code = request.QUERY_PARAMS.get('country', 'vn')
        tz = timezone(country_timezones(country_code)[0])
        now = datetime.datetime.utcnow()
        to_time = request.QUERY_PARAMS.get('to_time', '16:00:00')
        item = int(request.QUERY_PARAMS.get('item', 24))
        page = int(request.QUERY_PARAMS.get('page', 1))
        order = request.QUERY_PARAMS.get('order', 'time')
        asc = request.QUERY_PARAMS.get('asc', 'asc')
        if not date:
            return Response({'status': 400, 'detail': 'Missing param date', 'code': 'ERR_PARAM'}, status=400)

        if not city:
            return Response({'status': 400, 'detail': 'Missing param city', 'code': 'ERR_PARAM'}, status=400)

        current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
        if current_tz.date() == datetime.datetime.strptime(date, '%Y-%m-%d').date() and datetime.datetime.strptime(
                from_time, '%H:%M:%S').time() < current_tz.time():
            from_time = current_tz.time()
        #### Get Deal -> Need to fix
        filter_condition2 = {
            'date': current_tz.date(),
            'from_time__lte': current_tz.time(), 'to_time__gte': current_tz.time()
        }
        args = {}
        for k, v in filter_condition2.items():
            if v:
                args[k] = v
        booking_time = BookingTime.objects.filter(Q(**args))
        deal_teetime = {}
        time_teetime = {}
        if booking_time:
            for bt in booking_time:
                if not bt.deal.active:
                    continue
                if (current_tz.date() == bt.deal.effective_date and current_tz.time() <= bt.deal.effective_time) or (
                        current_tz.date() == bt.deal.expire_date and current_tz.time() >= bt.deal.expire_time):
                    continue
                deal = DealEffective_TeeTime.objects.filter(bookingtime=bt)
                if deal.exists():
                    for d in deal:
                        hole_list = d.hole.split(',')
                        dc = {'discount_9': 0,
                              'discount_18': 0,
                              'discount_27': 0,
                              'discount_36': 0,
                              'discount_default': 0}
                        for hl in hole_list:
                            k = 'discount_{0}'.format(hl.strip())
                            dc[k] = d.discount
                        dc['discount_default'] = d.discount
                        if d.teetime.id in deal_teetime.keys():
                            if d.modified > time_teetime.get(d.teetime.id, 'None'):
                                deal_teetime[d.teetime.id] = dc
                                time_teetime[d.teetime.id] = d.modified
                        else:
                            time_teetime[d.teetime.id] = d.modified
                            deal_teetime[d.teetime.id] = dc
        #### ----------> End Deal

        filter_condition = {}
        if golfcourse and golfcourse != '-1':
            gfc = [int(a) for a in golfcourse.split(',') if a]
            filter_condition = {
                'date': date,
                'time__gte': from_time, 'time__lte': to_time,
                'golfcourse_id__in': gfc,
            }
        elif city == -1:
            filter_condition = {
                'date': date,
                'time__gte': from_time, 'time__lte': to_time,
                'available': True
            }
        else:
            gc_list = []
            gc = GolfCourse.objects.filter(city_id=city)
            for igc in gc:
                gc_list.append(igc.id)
            filter_condition = {
                'date': date,
                'time__gte': from_time, 'time__lte': to_time,
                'golfcourse_id__in': gc_list,
                'available': True
            }
        revr = False
        if asc == 'des':
            revr = True
        arguments = {}
        filter_condition['is_block'] = filter_condition['is_booked'] = filter_condition['is_request'] = False
        filter_condition.update({'teetime_price__hole': 18, 'teetime_price__is_publish': True})
        for k, v in filter_condition.items():
            if v is not None:
                arguments[k] = v
        num_pages = math.ceil(TeeTime.objects.filter(Q(**arguments)).count() * 1.0 / item)
        teetimes = TeeTime.objects.filter(Q(**arguments)).order_by('time', 'golfcourse', 'description')[
                   (item * page - item):(item * page)]
        data = {}
        if teetimes:
            serializer = GetTeetimeSerializer(teetimes, many=True, context={'deal_teetime': deal_teetime})
            # data = serializer.data
            data = [d for d in serializer.data if d]
            data = sorted(data, key=lambda x: (x['discount'] + x['discount_online']), reverse=True)
            data = sorted(data, key=itemgetter('time'), reverse=False)
        res = {'num_pages': num_pages, 'data': data}
        return Response(res, status=200)


class BookingView(APIView):
    # permission_classes = (IsAuthenticated,)
    serializers_class = BookingSerializer
    parser_classes = (JSONParser, FormParser)

    def get(self, request):
        user = request.user
        user_type = 'guest'
        if not user.is_anonymous():
            golfstaff = get_or_none(GolfCourseStaff, user=request.user)
            if golfstaff:
                user_type = 'staff'
            else:
                user_type = 'golfer'

        # GET request data
        date = request.QUERY_PARAMS.get('date')
        if not date:
            return Response({'status': 400, 'detail': 'Missing param date', 'code': 'ERR_PARAM'}, status=400)
        city = int(request.QUERY_PARAMS.get('city'))
        if not city:
            return Response({'status': 400, 'detail': 'Missing param city', 'code': 'ERR_PARAM'}, status=400)
        golfcourse = int(request.QUERY_PARAMS.get('golfcourse'))
        from_time = request.QUERY_PARAMS.get('from_time', '00:00:00')
        country_code = request.QUERY_PARAMS.get('country', 'vn')
        tz = timezone(country_timezones(country_code)[0])
        now = datetime.datetime.utcnow()
        current_tz = datetime.datetime.fromtimestamp(now.timestamp(), tz)
        if current_tz.date() == datetime.datetime.strptime(date, '%Y-%m-%d').date() and datetime.datetime.strptime(
                from_time, '%H:%M:%S').time() < current_tz.time():
            from_time = current_tz.time()
        to_time = request.QUERY_PARAMS.get('to_time', '23:59:00')
        item = int(request.QUERY_PARAMS.get('item', 24))
        page = int(request.QUERY_PARAMS.get('page', 1))
        # End
        ##### Tuan Ly: Send deal discount to client with default hole=18 to apply all teetimes
        if golfcourse and golfcourse != -1:
            filter_condition = {
                'date': date,
                'time__gte': from_time, 'time__lte': to_time,
                'golfcourse_id': golfcourse
            }
            # set argument for filter condition
            arguments = {}
            for k, v in filter_condition.items():
                if v:
                    arguments[k] = v
            # end

            teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False,
                                                                     is_request=False).values('id')
        # case all city , golfcourse all
        else:
            if city == -1:
                filter_condition = {
                    'date': date,
                    'time__gte': from_time, 'time__lte': to_time
                }
                # set argument for filter condition
                arguments = {}
                for k, v in filter_condition.items():
                    if v:
                        arguments[k] = v
                # end
                teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False,
                                                                         is_request=False).values('id')
            else:
                gc_list = []
                gc = GolfCourse.objects.filter(city_id=city)
                for igc in gc:
                    gc_list.append(igc.id)
                filter_condition = {
                    'date': date,
                    'time__gte': from_time, 'time__lte': to_time,
                    'golfcourse_id__in': gc_list
                }
                # set argument for filter condition
                arguments = {}
                for k, v in filter_condition.items():
                    if v:
                        arguments[k] = v
                # end
                teetimes = TeeTime.objects.filter(Q(**arguments)).filter(is_block=False, is_booked=False,
                                                                         is_request=False).values('id')

        # sort slot by time
        filter_condition2 = {
            'date': current_tz.date(),
            'from_time__lte': current_tz.time(), 'to_time__gte': current_tz.time()
        }
        args = {}
        for k, v in filter_condition2.items():
            if v:
                args[k] = v
        booking_time = BookingTime.objects.filter(Q(**args))
        deal_teetime = {}
        time_teetime = {}
        if booking_time:
            for bt in booking_time:
                if not bt.deal.active:
                    continue
                if (current_tz.date() == bt.deal.effective_date and current_tz.time() <= bt.deal.effective_time) or (
                        current_tz.date() == bt.deal.expire_date and current_tz.time() >= bt.deal.expire_time):
                    continue
                deal = DealEffective_TeeTime.objects.filter(bookingtime=bt)
                if deal.exists():
                    for d in deal:
                        hole_list = d.hole.split(',')
                        dc = {'discount_9': 0,
                              'discount_18': 0,
                              'discount_27': 0,
                              'discount_36': 0,
                              'discount_default': 0}
                        for hl in hole_list:
                            k = 'discount_{0}'.format(hl.strip())
                            dc[k] = d.discount
                        dc['discount_default'] = d.discount
                        if d.teetime.id in deal_teetime.keys():
                            if d.modified > time_teetime.get(d.teetime.id, 'None'):
                                deal_teetime[d.teetime.id] = dc
                                time_teetime[d.teetime.id] = d.modified
                        else:
                            time_teetime[d.teetime.id] = d.modified
                            deal_teetime[d.teetime.id] = dc
        if teetimes:
            list_id = []
            for teetime in teetimes:
                list_id.append(teetime['id'])
            price = TeeTimePrice.objects.filter(teetime_id__in=list_id, is_publish=True, hole=18).values('teetime',
                                                                                                         'online_discount',
                                                                                                         'cash_discount')
            max_discount = 0
            for p in price:
                online_discount = deal_teetime[p['teetime']]['discount_default'] if p[
                                                                                        'teetime'] in deal_teetime.keys() else \
                p['online_discount']
                discount = online_discount + p['cash_discount']

                if discount > max_discount:
                    max_discount = discount
            return Response({'status': '200', 'code': 'OK',
                             'detail': max_discount}, status=200)
        else:
            return Response({'status': '200', 'code': 'OK',
                             'detail': 0}, status=200)

    def post(self, request):
        """ Viewset handle for saving information of booking and payment
		Parameters:
			* golfcourse
			* d
			* time
			* price
			* player_count
			* subgolfcourse
			* user
			* clubsets:
				* clubset
				* amount
			* buggies:
			* caddies:
				* caddy
		"""

        # Check send json is valid
        request.DATA['user'] = request.user.id
        customer_name = request.DATA.get('customer_name', '')
        customer_email = request.DATA.get('customer_email', '')
        customer_phone = request.DATA.get('customer_phone', '')
        golfcourse_id = request.DATA['golfcourse']
        book_type = request.DATA['book_type']
        if book_type != 'D' and not customer_name:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'Customer name is required'}, status=400)
        user = request.user.id
        if customer_name:
            is_customer = True
        else:
            is_customer = False

        if customer_email:
            user = get_or_none(User, username=customer_email)
            if user:
                user = user.id
                is_customer = False

        if is_customer:
            customer = Customer.objects.create(name=customer_name, email=customer_email, phone_number=customer_phone,
                                               golfcourse_id=golfcourse_id)
            request.DATA['booked_for_customer'] = customer.id
        else:
            request.DATA['booked_for'] = user

        serializer = self.serializers_class(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        # Check whether this slot is booked or not
        is_booked = get_or_none(BookedTeeTime, golfcourse=request.DATA['golfcourse'],
                                date_to_play=request.DATA['date_to_play'], time_to_play=request.DATA['time_to_play'],
                                subgolfcourse=request.DATA['subgolfcourse'])
        if is_booked:
            return Response({'status': '400', 'code': 'E_ALREADY_EXIST',
                             'detail': code['E_ALREADY_EXIST']}, status=400)

        total_amount = request.DATA['total_amount']
        price = calculate_price(request)
        if price == 0:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Cannot find teetime setting'}, status=404)
        if decimal.Decimal(total_amount) != price or total_amount == '0':
            return Response({'status': '400', 'code': 'E_MISMATCH_VALUES',
                             'detail': 'Some values are mismatch', 'true': price}, status=400)

        paid_amount = request.DATA.get('paid_amount', '')
        payment_type = request.DATA.get('payment_type', '')
        if (total_amount != paid_amount and payment_type == 'F') \
                or (paid_amount != '0.00' and payment_type == 'N'):
            return Response({'status': '400', 'code': 'E_MISMATCH_VALUES',
                             'detail': 'Some values are mismatch'}, status=400)

        teetime = serializer.save()
        for partner in teetime.partner.all():
            if partner.email:
                try:
                    validate_email(partner.email)
                    teetime = partner.teetime
                    detail_html = '<br><br><br><b>Chào bạn,</b><br><br>' + str(
                        teetime.user.user_profile.display_name) + ' đã đặt teetime cho bạn ở sân <b> ' + str(
                        teetime.golfcourse.name) + '</b> lúc <b>' + str(
                        teetime.time_to_play.strftime('%H:%M')) + '</b> vào ngày <b> ' + str(
                        teetime.date_to_play.strftime('%d-%m-%Y')) + '</b>'

                    detail_htmlen = '<b>Hi,</b><br><br>' + str(
                        teetime.user.user_profile.display_name) + ' has booked a teetime at <b> ' + str(
                        teetime.golfcourse.name) + '</b> at <b>' + str(
                        teetime.time_to_play.strftime('%H:%M')) + '</b> on <b> ' + str(
                        teetime.date_to_play.strftime('%d-%m-%Y')) + '</b>'
                    html_content = detail_htmlen + '.<br> <a href="' + 'https://' + request.META[
                        'HTTP_HOST'] + '/#/register-booking/' + str(
                        partner.id) + '">To see teetime info, click here to register</a>'
                    html_content += detail_html + '.<br> <a href="' + 'https://' + request.META[
                        'HTTP_HOST'] + '/#/register-booking/' + str(
                        partner.id) + '">Xem thông tin teetime, nhấp vào đây để đăng kí</a>'
                    subject = 'Golfconnect24 Booking'
                    send_email.delay(subject, html_content, [partner.email])
                except ValidationError:
                    pass
        # uri = request.build_absolute_uri() + 'checkin/' + str(teetime.id)
        # # uri = 'https://ludiino.ddns.net/#/home'
        # url = pyqrcode.create(uri)
        # image_url = 'https://localhost:8000/api/media/qr_codes/' + str(teetime.id) + '.svg'
        # teetime.url = image_url
        # url.svg('media/qr_codes/' + str(teetime.id) + '.svg', scale=2)
        # result = urllib.request.urlretrieve(image_url)
        # teetime.qr_image.save(
        # os.path.basename(image_url),
        # File(open(result[0]))
        # )
        # teetime.save()

        # If everything is OK
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer.data}, status=200)


class CheckPriceView(APIView):
    serializers_class = BookingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        request.DATA['user'] = self.request.user.id
        serializer = self.serializers_class(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        # Check whether this slot is booked or not
        total_amount = request.DATA['total_amount']
        price = calculate_price(request)
        if price == 0:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Cannot find teetime setting'}, status=404)
        if decimal.Decimal(total_amount) != price or total_amount == '0':
            return Response({'status': '400', 'code': 'E_MISMATCH_VALUES',
                             'detail': 'Some values are mismatch', 'true': price}, status=400)
        # If everything is OK
        return Response({'status': '200', 'code': 'OK'}, status=200)


class BookingSettingViewSet(viewsets.ModelViewSet):
    """ Handle all function for Holiday
	"""
    queryset = BookingSetting.objects.all()
    serializer_class = BookingSettingSerializer
    parser_classes = (JSONParser, FormParser,)


class MyBookingViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = MyBookingSerializer

    @staticmethod
    def get(request):
        _all = request.QUERY_PARAMS.get('all', 0)
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
        if int(_all) == 1:
            res = MyBookingDetailSerializer(booked)
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
        else:
            res = MyBookingSerializer(booked)
        return Response({'data': res.data}, status=200)


class MyBookingDetailViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    serializer_class = MyBookingDetailSerializer

    @staticmethod
    def get(request, key=None):
        user = request.user
        if not user or not user.is_authenticated():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        res = {}
        booked = get_or_none(BookedTeeTime, pk=key)
        res = MyBookingDetailSerializer(booked)
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


@api_view(['POST'])
def check_valid_voucher(request):
    voucher_codes = request.DATA.get('voucher', None)
    voucher_discount_amount = 0
    now = datetime.datetime.now()
    if voucher_codes:
        vc = voucher_codes.split(',')
        valid_voucher = []
        for voucher_code in vc:
            if voucher_code not in valid_voucher:
                valid_voucher.append(voucher_code)
            else:
                return Response({'code': 'ERR_DUPLICATE_VOUCHER', 'detail': 'Duplicate voucher'},
                                status=400)
        for voucher_code in vc:
            voucher = Voucher.objects.filter(code=voucher_code.upper(), from_date__lte=now, to_date__gte=now).first()
            if not voucher:
                return Response({'code': 'ERR_VOUCHER_NOT_FOUND', 'detail': 'Invalid voucher'}, status=400)
            if voucher.is_used is True:
                return Response({'code': 'ERR_VOUCHER_ALREADY_USED', 'detail': 'Voucher was already used'},
                                status=400)
            voucher_discount_amount += voucher.discount_amount
        return Response({'code': 'OK', 'detail': voucher_discount_amount}, status=200)
    return Response({'code': 'ERR_VOUCHER_NOT_FOUND', 'detail': 'Invalid voucher'}, status=400)


@api_view(['GET'])
def get_gc24_price(request):
    booking_id = int(request.QUERY_PARAMS.get('id', -1))
    bookedteetime = get_or_none(BookedTeeTime, pk=booking_id)
    if not bookedteetime:
        return Response({'detail': 0}, status=200)
    else:
        ### Check booking time had deal or not
        ### Not handle multi-deal for one teetime on same booking time.
        # ### Need to verify with Mai Huynh and Thao Vuong later
        price = get_gc24_booked_teetime_price(bookedteetime)
        return Response({'detail': price}, status=200)


def get_gc24_booked_teetime_price(bookedteetime):
    created_time = datetime.datetime.combine(datetime.date.today(), bookedteetime.created.time()) + timedelta(hours=7)
    filter_condition = {
        'teetime_id': bookedteetime.teetime.id,
        'bookingtime__date': bookedteetime.created.date(),
        'bookingtime__from_time__lte': created_time.time(),
        'bookingtime__to_time__gte': created_time.time(),
        'bookingtime__deal__is_base': False
    }
    filter_exclude1 = {
        'bookingtime__deal__effective_date': bookedteetime.created.date(),
        'bookingtime__deal__effective_time__gte': created_time.time()
    }
    filter_exclude2 = {
        'bookingtime__deal__expire_date': bookedteetime.created.date(),
        'bookingtime__deal__expire_time__lte': created_time.time()
    }
    deal_teetime = DealEffective_TeeTime.objects.filter(Q(**filter_condition)).exclude(
        Q(**filter_exclude1) | Q(**filter_exclude2)).order_by('-modified').first()

    if not deal_teetime:
        # Get gc24 price by booking time
        return get_gc24_price_by_booking(bookedteetime)
    else:
        # Check has price in GC24PriceByDeal or not
        teetimeday = deal_teetime.teetime.date.strftime("%a")
        filter_condition2 = {
            'deal': deal_teetime.bookingtime.deal,
            'date': teetimeday,
            'from_time__lte': deal_teetime.teetime.time,
            'to_time__gte': deal_teetime.teetime.time
        }
        gc24price = GC24PriceByDeal.objects.filter(Q(**filter_condition2)).first()
        if not gc24price:
            # Get price of booking time
            return get_gc24_price_by_booking(bookedteetime)
        else:
            key = "price_{0}"
            price = getattr(gc24price, key.format(bookedteetime.hole))
            return price


def get_gc24_price_by_booking(bookedteetime):
    booked_day = bookedteetime.teetime.date.strftime("%a")
    filter_condition = {
        'gc24price__golfcourse': bookedteetime.golfcourse,
        'gc24price__from_date__lte': bookedteetime.teetime.date,
        'gc24price__to_date__gte': bookedteetime.teetime.date,
        'date': booked_day,
        'from_time__lte': bookedteetime.teetime.time,
        'to_time__gte': bookedteetime.teetime.time
    }
    gc24price = GC24PriceByBooking_Detail.objects.filter(Q(**filter_condition)).first()
    if not gc24price:
        return 0
    else:
        key = "price_{0}"
        price = getattr(gc24price, key.format(bookedteetime.hole))
        return price


# noinspection PyPackageRequirements
# def handle_gc_event_booking(request, eventmember):
def handle_gc_event_booking(request, eventmember, list_cus):
    ip = get_client_ip(request)
    domain = fn_getHostname(request)
    user_agent = request.user_agent.browser.family
    if user_agent == "Apache-HttpClient":
        ua_device = 'and'
    elif user_agent == "CFNetwork":
        ua_device = 'ios'
    else:
        ua_device = 'web'
    # total_cost = compute_total_cost(request.DATA, eventmember)
    total_cost = compute_total_cost(request.DATA, eventmember, list_cus)
    if total_cost != request.DATA['total_cost']:
        eventmember.delete()
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': 'Total cost mismatch'}, status=400)
    booked = BookedGolfcourseEvent.objects.create(member=eventmember, discount=request.DATA['discount'],
                                                  total_cost=request.DATA['total_cost'],
                                                  payment_type=request.DATA['payment_type'], user_device=ua_device)
    qr_url, qr_code = generate_qr_code(fn_getHostname(request), booked.id)
    booked.qr_url = qr_url
    booked.qr_code = qr_code
    booked.save()
    ### Minh add booked partner
    for item in list_cus:
        booked_partner = BookedPartner_GolfcourseEvent.objects.create(
            bookedgolfcourse=booked,
            customer=item
        )
        booked_partner.save()
        ############################

    for event_price in request.DATA.get('event_price_info', []):
        price_info = GolfCourseEventPriceInfo.objects.get(pk=event_price['id'])
        BookedGolfcourseEventDetail.objects.create(booked_event=booked, price_info=price_info,
                                                   quantity=event_price['quantity'],
                                                   price=event_price['quantity'] * price_info.price)
    serializer = BookedGolfcourseEventSerializer(booked).data
    if booked.payment_type == 'N':
        serializer.update({'discount_type':'paylater'})
        send_email_booking_event.delay(booked.id)
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer}, status=200)
    else:

        if eventmember.customer:
            custAddress = eventmember.customer.email
            custPhone = eventmember.customer.phone_number
            custMail = eventmember.customer.email
        else:
            custAddress = eventmember.user.email
            custPhone = eventmember.user.user_profile.mobile if eventmember.user.user_profile.mobile else ""
            custMail = eventmember.user.email
        # print ("add {} ---phong {} --- mail{}".format(custAddress, custPhone, custMail))
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json',
        }
        description = 'Please select your preferred card to pay'
        description = description.encode('ascii', 'ignore').decode('ascii')
        values = OrderedDict()
        mTransactionID = str(int(datetime.datetime.utcnow().timestamp())) + 'e' + str(booked.id)
        values['mTransactionID'] = mTransactionID  #### Tuan Ly: need replace
        values['merchantCode'] = PAYMERCHANTCODE
        values['bankCode'] = '123PAY'
        values['totalAmount'] = str(int(booked.total_cost))
        values['clientIP'] = ip
        values['custName'] = serializer['member']
        # values['custAddress'] = extract_email(request.DATA.get('email', 'abc@gmail.com'))
        values['custAddress'] = custAddress
        values['custGender'] = 'M'
        values['custDOB'] = ''
        # values['custPhone'] = extract_nbr(str(request.DATA.get('phone', '')))
        values['custPhone'] = custPhone
        # values['custMail'] = extract_email(request.DATA.get('email', 'abc@gmail.com'))
        values['custMail'] = custMail
        values['description'] = description
        url = ''
        if request.user_agent.browser.family == "Apache-HttpClient" or request.user_agent.browser.family == "CFNetwork":
            url = 'golfpay123://booking-request/e' + str(booked.id) + '/'
        else:
            url = 'https://' + domain + '/#/successBooking/e' + str(booked.id) + '/'
        print(url)
        values['cancelURL'] = url
        values['redirectURL'] = url
        values['errorURL'] = url
        values['passcode'] = PAYPASSCODE
        cs = values['mTransactionID'] + values['merchantCode'] + values['bankCode'] + values['totalAmount']
        cs += values['clientIP'] + values['custName'] + values['custAddress'] + values['custGender']
        cs += values['custDOB'] + values['custPhone'] + values['custMail'] + values['cancelURL']
        cs += values['redirectURL'] + values['errorURL'] + values['passcode'] + PAYSECRETKEY
        hashed = sha1(cs.encode('utf-8'))
        values['checksum'] = hashed.hexdigest()
        values['addInfo'] = ''
        conn = http.client.HTTPSConnection(PAYURL)
        v = json.dumps(values)
        pay_url = "/createOrder1"
        default_language = "&lang=en"
        if CURRENT_ENV == 'prod':
            pay_url = "/createOrder1"
        else:
            default_language = ""
            pay_url = "/miservice/createOrder1"
        conn.request('POST', pay_url, v, headers)
        res = conn.getresponse()
        # print (res.read().decode('utf-8'))
        # print (type(res.read().decode('utf-8')))
        # response_tuanly = json.loads(res.read().decode('utf-8'))
        r = res.read().decode('utf-8')
        print (r)
        response_tuanly = json.loads(r)
        print(response_tuanly)
        returnCode = response_tuanly[0]
        if not (int(returnCode) == 1):
            raise ParseError('Cannot create pay order: {}'.format(response_tuanly))
        payTransactionid = response_tuanly[1]
        redirectURL = response_tuanly[2]
        res_cs = returnCode + payTransactionid + redirectURL + PAYSECRETKEY
        checksum = response_tuanly[3]
        res_hashed = sha1(res_cs.encode('utf-8')).hexdigest()
        if not (checksum == res_hashed):
            raise ParseError('Invalid checksum')
        payStore = PayTransactionStore.objects.create(payTransactionid=payTransactionid,
                                                      transactionId=mTransactionID,
                                                      totalAmount="{0}".format(booked.total_cost),
                                                      description=values['description'],
                                                      clientIP=ip,
                                                      vendor=VNG)
        response_tuanly[0] = ""
        response_tuanly[1] = ""
        response_tuanly[2] = response_tuanly[2] + default_language
        response_tuanly[3] = ""
        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': response_tuanly}, status=200)


# def compute_total_cost(data, member):
def compute_total_cost(data, member, list_cus):
    event_price = member.event.event_price_info.all()
    total_cost = 0

    if 'event_price_info' not in  data.keys():
        return total_cost

    for item in data['event_price_info']:
        query = event_price.filter(id=item['id']).first()
        total_cost += int(query.price) * int(item.get('quantity', 1))
    # total_cost *= (1 - (member.event.discount / 100))

    number_golfer_joined = len(list_cus)

    total_cost = total_cost * number_golfer_joined

    if data['payment_type'] == "N":
        # delta_price = total_cost * 0.05 (member.event.payment_discount_value / 100)
        delta_price = total_cost * (member.event.payment_discount_value_later / 100)
    else:
        delta_price = total_cost * (member.event.payment_discount_value_now / 100)

    total_cost = total_cost - delta_price

    return (total_cost)


def generate_qr_code(domain, book_id):
    qr_code = base64.urlsafe_b64encode(str(book_id).encode('ascii')).decode('ascii')
    uri = 'https://{}/#/event-register/{}'.format(domain, qr_code)
    url = pyqrcode.create(uri)
    filename = 'media/qr_codes/{}.png'.format(qr_code)
    url.png(filename, scale=6)
    qr_url = 'https://{}/api/media/qr_codes/{}.png'.format(domain, qr_code)
    return qr_url, qr_code


@api_view(['POST'])
def request_invoice(request):
    data = request.DATA
    invoice_name = data.get('name', '')
    invoice_tax = data.get('tax_code', '')
    invoice_coaddress = data.get('company_address', '')
    invoice_address = data.get('invoice_address', '')
    booked_id = data.get('id', None)
    if not booked_id:
        raise ParseError('Invalid field type')
    booked_teetime = get_or_none(BookedTeeTime, pk=booked_id)
    if not booked_teetime:
        raise ParseError('Invalid booking')
    booked_teetime.invoice_name = invoice_name
    booked_teetime.invoice_address = invoice_address
    booked_teetime.company_address = invoice_coaddress
    booked_teetime.tax_code = invoice_tax
    booked_teetime.save()

    reservation_code = '#' + booked_teetime.reservation_code if booked_teetime.teetime.is_booked else 'request'
    subject = "Request invoice for booking {}".format(reservation_code)
    to_email = ["booking@golfconnect24.com"]
    if CURRENT_ENV != 'prod':
        subject = "[{}] {}".format(CURRENT_ENV, subject)

    customer_name = ''
    book_partner = booked_teetime.book_partner.all().first()
    if book_partner:
        customer_name = book_partner.customer.name

    html_content = 'Hi,<br><br>Booking for golfer: <b>' + customer_name + ' </b> for teetime of <b>' + booked_teetime.golfcourse.name + '</b> on <b>{0} {1}</b>'.format(
        booked_teetime.teetime.date, booked_teetime.teetime.time)
    html_content += '<br> Request invoice as below: <br>'
    html_content += 'Company Name: <b>{}</b> <br>'.format(invoice_name)
    html_content += 'Tax code: <b>{}</b> <br>'.format(invoice_tax)
    html_content += 'Company Address: <b>{}</b> <br>'.format(invoice_coaddress)
    html_content += 'Address to receive invoice: <b>{}</b> <br>'.format(invoice_address)
    send_email.delay(subject, html_content, to_email)
    return Response({'status': '200', 'code': 'SUCCESS'}, status=200)


# reservation_code

@api_view(['GET'])
def send_after_booking_email(request):
    from core.booking.models import BookedGolfcourseEvent, BookedGolfcourseEventDetail
    from api.bookingMana.serializers import BookedGolfcourseEventSerializer
    from core.booking.models import BookedPartner_GolfcourseEvent
    from core.customer.models import Customer
    import datetime
    from datetime import timedelta, date
    from v2.api.gc_eventMana.tasks import send_email_survey
    from pytz import timezone, country_timezones

    teetime_date = datetime.datetime.today()
    teetime_list_booked = TeeTime.objects.filter(date=teetime_date, is_booked=True, booked_teetime__user_device='web')
    teetime_list_request = TeeTime.objects.filter(date=teetime_date, is_request=True, booked_teetime__user_device='web')
    teetime_list = teetime_list_request | teetime_list_booked
    teetime_id = teetime_list.values_list('id', flat=True).distinct()
    if teetime_id:
        send_thankyou_email.delay(list(teetime_id))

    today = date.today()
    for i in BookedGolfcourseEvent.objects.filter(created__day=today.day, created__year=today.year,
                                                  created__month=today.month).values('created', 'id'):
        b_gcev = BookedGolfcourseEvent.objects.get(pk=i['id'])
        tz = timezone(country_timezones(b_gcev.member.event.golfcourse.country.short_name)[0])
        book_check = (datetime.datetime.fromtimestamp(i['created'].timestamp(), tz))

        if book_check.hour < 21:
            send_email_survey.delay(b_gcev.id)
    return Response({'status': '200', 'code': 'SUCCESS'}, status=200)


@api_view(['POST'])
def update_booking_note(request):
    data = Request.DATA
    booked_teetime = BookedTeetime.objects.get(pk=data['id'])
    booked_teetime.note = data['note']
    booked_teetime.save()
    return Response({'status': '200', 'code': 'SUCCESS'}, status=200)
