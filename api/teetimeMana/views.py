import datetime, time
import csv
import json

from os.path import join

from django.utils.timezone import utc
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework import mixins
from django.db.models import Q
from rest_framework.viewsets import GenericViewSet
from api.bookingMana.tasks import send_email_task, handle_cancel_booking
from core.booking.models import BookedTeeTime, BookedPartner, BookedTeeTime_History, BookedPartner_History
from pytz import timezone, country_timezones
from core.golfcourse.models import GolfCourseStaff, SubGolfCourse, GolfCourse
from core.teetime.models import GCSetting, TeeTime, TeeTimePrice, GuestType, PriceType, PriceMatrix, PriceMatrixLog, \
    Holiday, RecurringTeetime, Deal, BookingTime, DealEffective_TimeRange, GC24DiscountOnline, ArchivedTeetime
from api.teetimeMana.serializers import TeeTimeManagementSerializer, TeeTimeSerializer, TeeTimePriceSerializer, \
    GuestTypeSerializer, \
    PriceTypeSerializer, PriceMatrixSerializer, PriceMatrixLogSerializer, HolidaySerializer, RecurringTeetimeSerializer, \
    ArchivedTeetimeSerializer
from utils.django.models import get_or_none
from utils.rest.permissions import IsGolfStaff
from core.teetime.models import GCKeyPrice, PaymentMethodSetting, GC24PriceByBooking_Detail, TeeTimePrice
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, BASE_DIR
import base64
import redis
from django.db.models import Max
from django.core.mail import send_mail
from api.teetimeMana.tasks import compare_price_and_notice, \
    monthly_archive_teetime, \
    import_teetime_recurring_queue

redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
ACTIVE = 'A'

HOLE_LIST = [18, 9]

SAVE_FILE_PATH = join(BASE_DIR, 'media', 'teetime')

_MAX_DUPLICATE_ = 2


def fn_getHostname(request):
    domain = ''
    if 'HTTP_HOST' in request.META:
        domain = request.META['HTTP_HOST']
    else:
        domain = request.META['REMOTE_ADDR']
    return domain


def get_default_discount(golfcourse_id, discount_now):
    base_discount_setup = Deal.objects.filter(golfcourse=golfcourse_id, is_base=True, active=True,
                                              effective_date__lte=discount_now).order_by('-effective_date')
    base_discount = {'Sun': 0, 'Mon': 0, 'Tue': 0, 'Wed': 0, 'Thu': 0, 'Fri': 0, 'Sat': 0}
    if base_discount_setup:
        bookingtime = BookingTime.objects.filter(deal=base_discount_setup[0])
        if bookingtime:
            dealeffective_timerange = DealEffective_TimeRange.objects.filter(bookingtime=bookingtime[0])
            if dealeffective_timerange:
                for d in dealeffective_timerange:
                    base_discount[d.date.strftime("%a")] = d.discount
    return base_discount


def handle_import_request_teetime_admin(arrRow, guest_type_id):
    teetime_import_list = []
    for obj in arrRow:
        date_valid = True
        try:
            date = datetime.datetime.strptime(obj['date'], '%d/%m/%Y').date()
        # time = datetime.datetime.strptime(obj['time'], '%H:%M')
        except Exception:
            date_valid = False
            pass
        # try again parse format example '12/9/15'
        try:
            if date_valid is False:
                date = datetime.datetime.strptime(obj['date'], '%d/%m/%y').date()
        except Exception:
            return
        # try parse time
        try:
            time = datetime.datetime.strptime(obj['time'], '%H:%M').time()
        except Exception:
            return

        # issue #425373862: key error golfcourse
        if 'golfcourse' not in obj:
            return

        golfcourse = get_or_none(GolfCourse, id=int(obj['golfcourse'].strip()))
        if not golfcourse:
            return
        golfcourse_id = golfcourse.id
        teetime_obj = TeeTime.objects.create(time=time,
                                             date=date,
                                             golfcourse_id=golfcourse_id
                                             )
        if 'min_player' in obj:
            try:
                int(obj['min_player'])
                teetime_obj.min_player = obj['min_player']
            except:
                pass
            #   update description of teetime
        if 'description' in obj:
            try:
                teetime_obj.description = obj['description']
            except:
                pass
        teetime_obj.available = False
        teetime_obj.allow_payonline = False
        teetime_obj.save()
        now = datetime.datetime.now()
        discount_now = now
        base_discount = get_default_discount(golfcourse_id, discount_now)

        hole_all = [9, 18, 27, 36]
        for k in hole_all:
            price = 0
            key = "Price_{0}"
            if key.format(k) in obj.keys():
                price = obj[key.format(k)]

                teetime_price_obj, created = TeeTimePrice.objects.get_or_create(teetime_id=teetime_obj.id,
                                                                                guest_type_id=guest_type_id,
                                                                                hole=k)
                teetime_price_obj.price = price
                teetime_price_obj.online_discount = base_discount[date.strftime("%a")]
                if obj['food_voucher'].lower() == 'yes':
                    teetime_price_obj.food_voucher = True
                if 'buggy' in obj:
                    if obj['buggy'].lower() == 'yes':
                        teetime_price_obj.buggy = True
                if 'caddy' in obj:
                    if obj['caddy'].lower() == 'yes':
                        teetime_price_obj.caddy = True
                teetime_price_obj.save()
        teetime_import_list.append(teetime_obj.id)
    compare_price_and_notice.delay(teetime_import_list)


class TeetimeImport(APIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    serializer_class = TeeTimePriceSerializer
    queryset = TeeTimePrice.objects.all()
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        file_obj = request.FILES['file']
        # generate file name
        now = datetime.datetime.now()
        nonow = now.strftime('%Y-%m-%d_%H:%M:%S')
        file_name = 'teetimeImport_' + nonow + '.csv'
        #
        fn_handle_uploaded_file(file_obj, file_name)
        arrRow = []
        with open(SAVE_FILE_PATH + file_name, encoding='cp1258') as f:
            dataReader = csv.reader(f, delimiter=',', quotechar='"')
            arrRow = fn_read_all_row_import(dataReader)

        # Get guest_type.id by name 'G'

        default_guesttype = GuestType.objects.filter(name='G')
        if len(default_guesttype) == 0:
            return Response({'status': '400', 'code': 'E_GUESTTYPE',
                             'detail': 'Guest type G not found'}, status=400)
        if golfstaff.user.username == 'booking@golfconnect24.com':  ## Tuan Ly: Hard code for admin here
            handle_import_request_teetime_admin(arrRow, default_guesttype[0].id)
            return Response({'count': len(arrRow), 'detail': request.META['CONTENT_TYPE'], 'filename': file_obj.name},
                            status=200)
        line = 0;
        option = request.QUERY_PARAMS.get('option')

        arr_new_date = []
        golfcourse_id = golfstaff.golfcourse_id
        base_online_discount = 0
        base_online_discount_setup = GC24DiscountOnline.objects.filter(golfcourse=golfcourse_id).order_by('-created')
        if base_online_discount_setup.exists() and base_online_discount_setup:
            base_online_discount = base_online_discount_setup[0].discount
        discount_now = now
        base_discount = get_default_discount(golfcourse_id, discount_now)
        teetime_list_import = []
        for obj in arrRow:
            line += 1
            date_valid = True
            try:
                date = datetime.datetime.strptime(obj['date'], '%d/%m/%Y').date()
            # time = datetime.datetime.strptime(obj['time'], '%H:%M')
            except Exception:
                date_valid = False
                pass
            # try again parse format example '12/9/15'
            try:
                if date_valid is False:
                    date = datetime.datetime.strptime(obj['date'], '%d/%m/%y').date()
            except Exception:
                return Response({'status': '400', 'code': 'E_DATETIME',
                                 'detail': 'date ' + obj['date'] + ' not valid. line ' + str(line + 1)}, status=400)
            # try parse time
            try:
                time = datetime.datetime.strptime(obj['time'], '%H:%M').time()
            except Exception:
                return Response({'status': '400', 'code': 'E_DATETIME',
                                 'detail': 'time ' + obj['time'] + ' not valid. line ' + str(line + 1)}, status=400)

            if not date in arr_new_date:
                check_teetime_obj = TeeTime.objects.filter(date=date, golfcourse_id=golfcourse_id, available=True
                                                           , is_booked=False, is_request=False, is_hold=False)
                if len(check_teetime_obj) == 0:
                    arr_new_date.append(date)
                elif len(check_teetime_obj) > 0 and not option:
                    return Response({'status': '400', 'code': 'ERR_CONFIRM',
                                     'detail': 'time ' + obj['time'] + ' not valid. line ' + str(line + 1)}, status=400)
                elif option == 'o':
                    arr_new_date.append(date)
                    tt_delete = TeeTime.objects.filter(date=date, golfcourse_id=golfcourse_id, available=True
                                                       , is_booked=False, is_request=False)
                    for tt in tt_delete:
                        if tt.is_hold == True and tt.hold_expire:
                            if tt.hold_expire < datetime.datetime.utcnow().replace(tzinfo=utc):
                                tt.is_hold = False
                                tt.hold_expire = None
                                tt.save()
                        if tt.is_hold == False:
                            tt_price = TeeTimePrice.objects.filter(teetime_id=tt.id).delete()
                            tt.delete()
                elif option == 'm':
                    arr_new_date.append(date)

            # create new teetime
            today530am = now.replace(hour=5, minute=30, second=0, microsecond=0)
            today4pm = now.replace(hour=16, minute=0, second=0, microsecond=0)
            if time < today530am.time() or time > today4pm.time():
                time = (datetime.datetime.combine(datetime.date(1, 1, 1), time) + datetime.timedelta(hours=12)).time()
                if time < today530am.time() or time > today4pm.time():  ### Tuan Ly: Try to re-check one more time
                    continue
            if not discount_now == date:
                discount_now = date
                base_discount = get_default_discount(golfcourse_id, discount_now)
            teetime_obj = TeeTime.objects.create(time=time,
                                                 date=date,
                                                 golfcourse_id=golfcourse_id
                                                 )
            if teetime_obj:
                #   update min_player of teetime
                if 'min_player' in obj:
                    try:
                        int(obj['min_player'])
                        teetime_obj.min_player = obj['min_player']
                    except:
                        pass
                # update description of teetime
                if 'description' in obj:
                    try:
                        teetime_obj.description = obj['description']
                    except:
                        pass
                # create or get teetime by unique fields
                payment_method = PaymentMethodSetting.objects.filter(golfcourse_id=golfcourse_id,
                                                                     date=teetime_obj.date.strftime("%a")).order_by(
                    '-created').first()
                if payment_method:
                    teetime_obj.allow_payonline = payment_method.allow_payonline
                    teetime_obj.allow_paygc = payment_method.allow_paygc
                teetime_obj.save()
                fn_get_or_create_teetime_price(teetime_obj.id, default_guesttype[0].id, obj, None, base_discount,
                                               base_online_discount, teetime_obj)
                teetime_list_import.append(teetime_obj.id)
        compare_price_and_notice.delay(teetime_list_import)
        return Response({'count': line, 'detail': request.META['CONTENT_TYPE'], 'filename': file_obj.name}, status=200)

    # update multi teetime status
    def put(self, request, format=None):
        ids = request.DATA['ids']
        force = request.DATA.get('force', False)
        if not ids:
            return Response({'status': '400', 'code': 'E_PARAM',
                             'detail': 'Missing request param'}, status=400)
        status = request.DATA['status']
        if status is None:
            return Response({'status': '400', 'code': 'E_PARAM',
                             'detail': 'Missing request param'}, status=400)
        default_guesttype = GuestType.objects.filter(name='G')
        if len(default_guesttype) == 0:
            return Response({'status': '400', 'code': 'E_GUESTTYPE',
                             'detail': 'Guest type G not found'}, status=400)
        teetimes = TeeTime.objects.filter(pk__in=ids)
        # check status is_hold and hold_expire
        for tt in teetimes:
            if tt.is_hold == True and tt.hold_expire:
                if tt.hold_expire < datetime.datetime.utcnow().replace(tzinfo=utc):
                    tt.is_hold = False
                    tt.hold_expire = None
                    tt.save()
                    try:
                        # publish to redis
                        channel = 'booking-' + tt.date.strftime('%Y-%m-%d')
                        msg = {
                            "id"     : tt.id,
                            "is_hold": False,
                            "expire" : 0
                        }
                        msg = json.dumps(msg)
                        redis_server.publish(channel, msg)
                    except Exception as e:
                        print(str(e))
                        continue
        if status == 0:
            for tt in teetimes:
                date = tt.date.strftime('%Y-%m-%d')
                time = tt.time.strftime('%H:%M')
                if tt.is_hold != False or tt.is_booked != False or tt.is_request != False:
                    return Response({'status': '400', 'code': 'E_UNPUBLISH',
                                     'detail': 'Teetime ' + date + ' ' + time + ' can not unpublish, please check status.'},
                                    status=400)
                elif tt.is_hold == False and tt.is_booked == False and tt.is_request == False:
                    if tt.is_block is True:
                        tt.is_block = False
                        tt.save(update_fields=['is_block'])
                    ttprice = get_or_none(TeeTimePrice, teetime_id=tt.id,
                                          guest_type_id=default_guesttype[0].id,
                                          hole=18)
                    ttprice.is_publish = False
                    ttprice.save()
                    fn_notify_booking_by_teetime_status(ttprice, tt)
        elif status == 1:
            #   publish teetime
            for tt in teetimes:
                date = tt.date.strftime('%Y-%m-%d')
                time = tt.time.strftime('%H:%M')
                # check number of duplicate teetime
                if not force is True:
                    tt_dup = TeeTime.objects.filter(date=date, time=time, golfcourse_id=tt.golfcourse_id)
                    gcsetting = get_or_none(GCSetting, golfcourse_id=tt.golfcourse_id)
                    if not gcsetting:
                        gcsetting = GCSetting.objects.create(golfcourse_id=tt.golfcourse_id,
                                                             max_duplicate=_MAX_DUPLICATE_)
                    if gcsetting and len(tt_dup) > 0:
                        if gcsetting.max_duplicate > 0 and len(tt_dup) > gcsetting.max_duplicate:
                            return Response({'status': '400', 'code': 'WARN_LIMIT_DUPLICATE',
                                             'date'  : date, 'time': time}, status=400)
                # end
                if tt.is_hold != False or tt.is_booked != False or tt.is_request != False:
                    return Response({'status': '400', 'code': 'E_PUBLISH',
                                     'detail': 'Teetime ' + date + ' ' + time + ' can not publish, it may be holding or booked.'},
                                    status=400)
                else:
                    ttprice = get_or_none(TeeTimePrice, teetime_id=tt.id,
                                          guest_type_id=default_guesttype[0].id,
                                          hole=18)
                    if not ttprice.price or ttprice.price <= 0:
                        return Response({'status': '400', 'code': 'E_PUBLISH',
                                         'detail': 'Teetime ' + date + ' ' + time + ' can not publish, invalid price of hole 18.'},
                                        status=400)
                    if ttprice.is_publish == False:
                        ttprice.is_publish = True
                        ttprice.save()
                    if tt.is_block == True:
                        tt.is_block = False
                        tt.save()
                    # return Response({'status': '400', 'code': 'E_PUBLISH',
                    #      'detail': 'Teetime ' + date + ' ' + time + ' has already published.'}, status=400)
                    # else:
                    #     ttprice.is_publish = True
                    #     ttprice.save()
        elif status == 2:
            #   block teetime
            for tt in teetimes:
                date = tt.date.strftime('%Y-%m-%d')
                time = tt.time.strftime('%H:%M')
                if tt.is_hold == True:
                    return Response({'status': '400', 'code': 'E_BLOCK',
                                     'detail': 'Teetime ' + date + ' ' + time + ' is being process by golfer. Please waiting for 5 minutes and try it again'},
                                    status=400)
                elif tt.is_block == True or tt.is_booked == True or tt.is_request == True:
                    return Response({'status': '400', 'code': 'E_BLOCK',
                                     'detail': 'Teetime ' + date + ' ' + time + ' is already blocked or booked.'},
                                    status=400)
                else:
                    tt.is_block = True
                    tt.save()
                    fn_notify_booking_by_teetime_status(None, tt)
        elif status == 4:
            handle_cancel_booking(ids)
        elif status == 5:
            for tt in teetimes:
                if not tt.is_booked:
                    domain = fn_getHostname(request)
                    send_email_task.delay(tt.pk, domain, 'C')
                tt.is_booked = True
                tt.save()
                booked = BookedTeeTime.objects.get(teetime=tt)
                booked.status = 'PP' if booked.payment_status else 'PU'
                booked.save()

        elif status == 6:
            booked_list = BookedTeeTime.objects.filter(teetime_id__in=ids).exclude(status='I')
            for booked in booked_list:
                if not booked.teetime.is_booked:
                    booked.payment_status = not booked.payment_status
                    booked.status = 'PP' if booked.payment_status else 'PU'
                    booked.save()
        teetimes = TeeTime.objects.filter(pk__in=ids)
        serializer = TeeTimeSerializer(teetimes)

        return Response(serializer.data, status=200)


class TeetimeDel(APIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    serializer_class = TeeTimePriceSerializer
    queryset = TeeTimePrice.objects.all()
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):
        ids = request.DATA.get('ids', [])

        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        teetimes = TeeTime.objects.filter(pk__in=ids)
        if golfstaff.user.username == 'booking@golfconnect24.com':
            teetimes = TeeTime.objects.filter(pk__in=ids).exclude(available=True)

        for tt in teetimes:
            if tt.golfcourse_id != golfstaff.golfcourse_id and golfstaff.user.username != 'booking@golfconnect24.com':  # Tuan Ly: Hard code for admin user here
                return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                                 'detail': 'You do not have permission to peform this action'}, status=401)
            if tt.is_hold == False and tt.is_booked == False and tt.is_request == False:
                # notify real-time
                channel = 'booking-' + tt.date.strftime('%Y-%m-%d')
                msg = {
                    "id"      : tt.id,
                    "is_block": True
                }
                msg = json.dumps(msg)
                redis_server.publish(channel, msg)
                # emd
                tt.delete()
            else:
                return Response({'status': '400', 'code': 'E_DELETE',
                                 'detail': 'Teetime ' + datetime.datetime.strftime(tt.date,
                                                                                   '%m/%d/%Y') + ' ' + datetime.time.strftime(
                                     tt.time, '%H:%M') + ' is holding or booked, can not be delete'}, status=400)
        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': ''}, status=200)


##############################################################################################################
#### fn real-time for teetime management
def fn_notify_booking_by_teetime_status(teetime_price, teetime):
    # un-publish
    if teetime_price and teetime and teetime_price.is_publish is False:
        channel = 'booking-' + teetime.date.strftime('%Y-%m-%d')
        msg = {
            "id"      : teetime.id,
            "is_block": True
        }
        msg = json.dumps(msg)
        redis_server.publish(channel, msg)

    # block
    if teetime.is_block is True:
        channel = 'booking-' + teetime.date.strftime('%Y-%m-%d')
        msg = {
            "id"      : teetime.id,
            "is_block": True
        }
        msg = json.dumps(msg)
        redis_server.publish(channel, msg)
    return True


#####  function define for import csv
def fn_get_or_create_teetime_price_one(price, hole, teetime_id, guest_type_id, obj, is_publish, base_discount,
                                       base_online_discount, teetime_obj):
    if price is not None:
        price = price.replace(',', '')
        try:
            float(price)
        except Exception as e:
            price = 0
        teetime_price_obj, created = TeeTimePrice.objects.get_or_create(teetime_id=teetime_id,
                                                                        guest_type_id=guest_type_id,
                                                                        hole=hole)
        #   update info of teetime price
        teetime_price_obj.price = price
        teetime_price_obj.gifts = obj['gifts']
        if obj['food_voucher'].lower() == 'yes':
            teetime_price_obj.food_voucher = True
        if 'addition_discount' in obj:
            try:
                float(obj['addition_discount'])
            except:
                obj['addition_discount'] = 0
            teetime_price_obj.cash_discount = base_online_discount
        if 'online_discount' in obj:
            try:
                float(obj['online_discount'])
            except:
                obj['online_discount'] = 0
            teetime_price_obj.online_discount = base_discount[teetime_obj.date.strftime("%a")]
        if is_publish is not None:
            teetime_price_obj.is_publish = False
        if 'buggy' in obj:
            if obj['buggy'].lower() == 'yes':
                teetime_price_obj.buggy = True
        if 'caddy' in obj:
            if obj['caddy'].lower() == 'yes':
                teetime_price_obj.caddy = True
        key = "GC24_hole_{0}".format(hole)
        if key in obj:
            standard_price = obj[key]
            sp = standard_price.replace(',', '')
            try:
                float(sp)
            except Exception as e:
                sp = 0
            teetime_price_obj.price_standard = sp
        teetime_price_obj.save()


def fn_get_or_create_teetime_price(teetime_id, guest_type_id, obj, is_publish, base_discount, base_online_discount,
                                   teetime_obj):
    if obj['Price_9'] is not None:
        fn_get_or_create_teetime_price_one(obj['Price_9'], 9, teetime_id, guest_type_id, obj, is_publish, base_discount,
                                           base_online_discount, teetime_obj)

    if obj['Price_18'] is not None:
        fn_get_or_create_teetime_price_one(obj['Price_18'], 18, teetime_id, guest_type_id, obj, is_publish,
                                           base_discount, base_online_discount, teetime_obj)

    if obj['Price_27'] is not None:
        fn_get_or_create_teetime_price_one(obj['Price_27'], 27, teetime_id, guest_type_id, obj, is_publish,
                                           base_discount, base_online_discount, teetime_obj)

    if obj['Price_36'] is not None:
        fn_get_or_create_teetime_price_one(obj['Price_36'], 36, teetime_id, guest_type_id, obj, is_publish,
                                           base_discount, base_online_discount, teetime_obj)


def fn_read_all_row_import(dataReader):
    result = []
    skip_row_header = 0
    header = dataReader.__next__()
    for row in list(dataReader):
        dataRow = fn_read_one_row_import(row, header)
        if dataRow:
            result.append(dataRow)
    return result


def fn_read_one_row_import(row, header):
    if row[0].strip() and row[1].strip():
        result = {}
        index = 0
        for d in header:
            result[d] = row[index].strip()
            index += 1
        return result
    return None


def fn_handle_uploaded_file(f, name):
    with open(SAVE_FILE_PATH + name, 'w', encoding='cp1258') as destination:
        for chunk in f.chunks():
            destination.write(chunk.decode("cp1258"))


# ------------------------END-----------------------------
#
###############################################################################################################
class TeeTimeViewSet(viewsets.ModelViewSet):
    queryset = TeeTime.objects.all()
    serializer_class = TeeTimeManagementSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        id = request.DATA.get('id', None)
        if not id:
            return Response({"code": "E_PARAM", "detail": "Missing params id"}, status=400)
        teetime = get_or_none(TeeTime, pk=id)
        if not teetime:
            return Response({"code": "E_NOT_FOUND", "detail": "Teetime not found"}, status=400)
        # if teetime not none
        if teetime.is_hold:
            return Response({"code": "E_HOLDING", "detail": "Can not update holding teetime"}, status=400)
        if teetime.is_booked:
            return Response({"code": "E_BOOKED", "detail": "Can not update booked teetime"}, status=400)
        if teetime.is_request:
            return Response({"code": "E_BOOKED", "detail": "Can not update booked teetime"}, status=400)
        teetime_price = get_or_none(TeeTimePrice, teetime_id=teetime.id, hole=18)
        if not teetime_price:
            return Response({"code": "E_NOT_FOUND", "detail": "Teetime price not found"}, status=400)
        if teetime_price.is_publish:
            return Response({"code": "E_PUBLISHED", "detail": "Can not update published teetime"}, status=400)

        date = request.DATA.get('date', None)
        time = request.DATA.get('time', None)
        min_player = request.DATA.get('min_player', None)
        description = request.DATA.get('description', None)
        force = request.DATA.get('force', False)

        if (date or time) and force is False:
            if date:
                date = datetime.datetime.strptime(date, '%Y-%m-%d')
            else:
                date = teetime.date

            if time:
                time = datetime.datetime.strptime(time, '%H:%M').time()
            else:
                time = teetime.time

            teetime_by_datetime = TeeTime.objects.filter(golfcourse_id=golfstaff.golfcourse_id, date=date, time=time)
            # .exclude(id=teetime.id)
            gcsetting = get_or_none(GCSetting, golfcourse_id=golfstaff.golfcourse_id)
            if not gcsetting:
                gcsetting = GCSetting.objects.create(golfcourse_id=golfstaff.golfcourse_id,
                                                     max_duplicate=_MAX_DUPLICATE_)
            if gcsetting and len(teetime_by_datetime) > 0:
                if gcsetting.max_duplicate > 0 and len(teetime_by_datetime) > gcsetting.max_duplicate:
                    return Response({"code"  : "E_CONFLICT", "num": len(teetime_by_datetime),
                                     "detail": "date and time conflict with another teetime"}, status=400)

        if date:
            teetime.date = date
        if time:
            teetime.time = time
        if min_player:
            teetime.min_player = min_player
        if description:
            teetime.description = description
        if 'available' in request.DATA:
            if request.DATA['available']:
                teetime.available = True
            else:
                teetime.available = False
        if 'allow_paygc' in request.DATA:
            if request.DATA['allow_paygc']:
                teetime.allow_paygc = True
            else:
                teetime.allow_paygc = False
        if 'allow_payonline' in request.DATA:
            if request.DATA['allow_payonline']:
                teetime.allow_payonline = True
            else:
                teetime.allow_payonline = False
        teetime.save()

        _data = request.DATA
        price_9 = request.DATA.get('price_9', None)
        price_18 = request.DATA.get('price_18', None)
        price_27 = request.DATA.get('price_27', None)
        price_36 = request.DATA.get('price_36', None)

        if price_18 is not None:
            if price_18 <= 0:
                return Response({"code": "E_INVALID_PRICE", "detail": "Price of hole 18 can not be =< 0"}, status=400)
        fn_update_teetime_price(teetime.id, _data, price_18, 18)
        fn_update_teetime_price(teetime.id, _data, price_9, 9)
        fn_update_teetime_price(teetime.id, _data, price_27, 27)
        fn_update_teetime_price(teetime.id, _data, price_36, 36)

        return Response({"code": "SUCCESS"}, status=200)

    def list(self, request, *args, **kwargs):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)

        now = datetime.datetime.now()
        # GET request data
        from_date = request.QUERY_PARAMS.get('from_date')
        if from_date:
            from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        else:
            from_date = datetime.datetime.strftime(now.date(), '%Y-%m-%d')
        to_date = request.QUERY_PARAMS.get('to_date')
        if to_date:
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        golfcourse_id = int(request.QUERY_PARAMS.get('golfcourse', golfstaff.golfcourse_id))
        # else:
        #	to_date = from_date
        # End
        if golfstaff.user.username == 'booking@golfconnect24.com':  # Tuan Ly: Hard code for admin here
            filter_condition = {
                'date__gte'    : from_date,
                'date__lte'    : to_date,
                'golfcourse_id': golfcourse_id,
            }
        else:
            filter_condition = {
                'date__gte'    : from_date,
                'date__lte'    : to_date,
                'golfcourse_id': golfcourse_id,
                'available'    : True
            }
        # set argument for filter condition
        arguments = {}
        for k, v in filter_condition.items():
            if v and not v == -1:
                arguments[k] = v
        # end
        teetimes = TeeTime.objects.filter(Q(**arguments)).order_by('date', 'time')
        # teetimes = TeeTime.objects.filter( golfcourse_id = golfstaff.golfcourse_id).filter(
        #                                     Q(date__gte = from_date, date__lte = to_date))
        is_admin = {'is_admin': False}
        if golfstaff.user.username == 'booking@golfconnect24.com':  # Hard code for admin here
            is_admin['is_admin'] = True
        json_res = self.serializer_class(teetimes, context=is_admin)
        return Response(json_res.data, status=200)

    def create(self, request, *args, **kwargs):
        """ request data format
        # {
        #     "teetime": {
        #         "interval"      : 30,
        #         "min_player"    : 1,
        #         "subgolfcourse" : "123",
        #         "from_time"     : "6:00:00",
        #         "to_time"       : "15:00:00",
        #         "from_date"     : "2015-07-11",
        #         "to_date"       : "2015-07-11"
        #     }
        # }
        """
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)

        # GET request data
        teetime = request.DATA['teetime']
        from_time = datetime.datetime.strptime(teetime['from_time'], '%H:%M:%S')
        to_time = datetime.datetime.strptime(teetime['to_time'], '%H:%M:%S')
        from_date = datetime.datetime.strptime(teetime['from_date'], '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(teetime['to_date'], '%Y-%m-%d').date()
        interval = teetime['interval']
        min_player = teetime['min_player']
        subgolfcourse = teetime['subgolfcourse']
        # End
        guest_type_list = GuestType.objects.all()
        price_type_list = PriceType.objects.all()
        holiday_list = Holiday.objects.all()
        #   loop date range
        for _date in fn_get_date_range(from_date, to_date, 1):
            #   Check this _date has any teetime which is_hold or is_block is set true
            blocked_teetime = TeeTime.objects.filter(subgolfcourse_id=subgolfcourse,
                                                     golfcourse_id=golfstaff.golfcourse_id,
                                                     date=_date).filter(
                Q(is_hold=True) | Q(is_block=True))
            if blocked_teetime:
                return Response(
                    {'status': 400, 'detail': _date.strftime('%d/%m') + ' has blocked teetimes', 'code': 'ERROR'},
                    status=400)
            # before create, delete all time of date , golfcourse_id, subgolfcourse_id
            #   if is_hold , is_block are false
            TeeTime.objects.filter(subgolfcourse_id=subgolfcourse,
                                   golfcourse_id=golfstaff.golfcourse_id,
                                   date=_date,
                                   is_hold=False,
                                   is_block=False).delete()

            #   Get date_type by _date
            date_type = fn_get_date_type(_date, holiday_list.values())
            #   Get list matrix_price by hole
            price_matrix_by_hole = fn_get_matrix_price(_date, golfstaff.golfcourse_id)

            #   Loop time range
            for _time in fn_get_time_range(from_time, to_time, interval):
                #   create teetime
                teetime_created = TeeTime.objects.create(time=_time,
                                                         date=_date,
                                                         golfcourse_id=golfstaff.golfcourse_id,
                                                         subgolfcourse_id=subgolfcourse,
                                                         min_player=min_player)

                #   After teetime created
                #   Generate teetime price
                price_type_id = fn_get_price_type(_time, price_type_list.values())
                for _hole in price_matrix_by_hole.keys():
                    for guest_type in guest_type_list.values():
                        matrix_price = list(filter(lambda x: x.price_type_id == price_type_id
                                                             and x.guest_type_id == guest_type['id']
                                                             and x.date_type == date_type,
                                                   price_matrix_by_hole[_hole]))
                        if len(matrix_price) > 0:
                            TeeTimePrice.objects.create(teetime_id=teetime_created.id,
                                                        guest_type_id=guest_type['id'],
                                                        hole=_hole,
                                                        price=matrix_price[0].price,
                                                        is_publish=False)

                        #   End loop time range
        # End loop date range

        # serializer = self.serializer_class(generated_teetime)
        return Response({'status': 200, 'detail': 'serializer.data', 'code': 'OK'}, status=200)


########################################################################################################################################
#### function update data teetime price
def fn_update_teetime_price(teetime_id, data, price_byHole, hole):
    default_guesttype_id = GuestType.objects.filter(name='G').first().id
    obj, created = TeeTimePrice.objects.get_or_create(teetime_id=teetime_id, hole=hole,
                                                      guest_type_id=default_guesttype_id)
    if obj:
        if price_byHole == 0:
            obj.delete()
            return
        if price_byHole:
            obj.price = price_byHole
        if 'online_discount' in data:
            obj.online_discount = data['online_discount']
        if 'cash_discount' in data:
            obj.cash_discount = data['cash_discount']
        if 'gifts' in data:
            obj.gifts = data['gifts']
        if 'food_voucher' in data:
            obj.food_voucher = data['food_voucher']
        if 'buggy' in data:
            obj.buggy = data['buggy']
        if 'caddy' in data:
            obj.caddy = data['caddy']
        key = "GC24_hole_{0}".format(hole)
        if key in data:
            obj.price_standard = data[key]
        obj.save()


#################     function use for generate teetime ( teetime create) from related info : guest_type, price_type ...
#   get table matrix price by
#   effective date
#   golfcourse
#   return matrix price by hole
#   {
#       '18' : object matrix price,
#       '9'  : object matrix price
#   }
def fn_get_matrix_price(date, golfcourse_id):
    result = {}
    #   Loop Hole list
    for _hole in HOLE_LIST:
        #   Get list matrix logs order decrease effective_date
        matrix_logs = PriceMatrixLog.objects.filter(golfcourse_id=golfcourse_id,
                                                    effective_date__lte=date,
                                                    hole=_hole).order_by('-effective_date')
        if len(matrix_logs) > 0:
            matrix_log_id = matrix_logs.values()[0]['id']
            price_matrix = PriceMatrix.objects.filter(matrix_log_id=matrix_log_id)
            result[_hole] = price_matrix
    return result


#   get price_type id by time
def fn_get_price_type(time, list_obj):
    for obj in list_obj:
        if obj['from_time'] <= time.time() <= obj['to_time']:
            return obj['id']


def fn_get_date_type(date, list_obj):
    for obj in list_obj:
        if date.date() == obj.date():
            return 'holiday'
    if 0 <= date.weekday() < 5:
        return 'weekday'
    else:
        return 'weekend'


def fn_get_time_range(from_time, to_time, interval):
    curr = from_time
    while curr <= to_time:
        yield curr
        curr += datetime.timedelta(minutes=interval)


def fn_get_date_range(from_date, to_date, interval):
    curr = from_date
    while curr <= to_date:
        yield curr
        curr += datetime.timedelta(days=interval)


#################################################### END ###########################################################
####################################################################################################################

class HolidayViewSet(viewsets.ModelViewSet):
    """ Handle all function for Holiday
    """
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    parser_classes = (JSONParser, FormParser,)


class TeeTimePriceViewSet(viewsets.ModelViewSet):
    queryset = TeeTimePrice.objects.all()
    serializer_class = TeeTimePriceSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)

        for data in request.DATA['teetime_setting']:
            data.update({'golfcourse': golfstaff.golfcourse_id})
        # for st in serializer.data['teetime_setting']:
        # if BookedTeeTime.objects.filter(subgolfcourse_id=st['subgolfcourse'], golfcourse_id=st['golfcourse'],
        # date_to_play__gte=st['date_start'],date_to_play__lte=st['date_end'],
        # time_to_play__gte=st['time_start'],time_to_play__lte=st['time_end']).exists():
        # return Response({'status': '400', 'code': 'E_INVALID_SETTING',
        # 'detail':'Golfers booked a teetime on this time'},status=400)
        # TeeTimeSetting.objects.filter(subgolfcourse_id=st['subgolfcourse'], golfcourse_id=st['golfcourse'],
        #                               date_start=st['date_start'], date_end=st['date_end'],
        #                               time_start=st['time_start'],
        #                               time_end=st['time_end']).delete()
        serializers = TeeTimePriceSerializer(data=request.DATA['teetime_price'], many=True)
        if not serializers.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializers.errors}, status=400)
        serializers.save()
        return Response(serializers.data, status=201)


class GuestTypeViewSet(viewsets.ModelViewSet):
    queryset = GuestType.objects.all()
    serializer_class = GuestTypeSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        list_data = request.DATA['guest_type']
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        for data in list_data:
            data.update({'golfcourse': golfstaff.golfcourse.id})
        serializers = GuestTypeSerializer(data=list_data, many=True)
        if not serializers.is_valid():
            return Response(serializers.errors, status=400)
        matrix_logs = PriceMatrixLog.objects.filter(golfcourse=golfstaff.golfcourse)
        if matrix_logs:
            matrix_log = matrix_logs[0]
        else:
            matrix_log = PriceMatrixLog.objects.create(golfcourse=golfstaff.golfcourse)
        for i, data in enumerate(serializers.data):
            if 'id' in list_data[i]:
                GuestType.objects.filter(id=list_data[i]['id']).update(
                    level=data['level'],
                    name=data['name'],
                    description=data['description'],
                    color=data['color'],
                    status=data['status']
                )
            else:
                golfcourse_id = list_data[i]['golfcourse']
                guest_type = GuestType.objects.create(level=data['level'],
                                                      name=data['name'],
                                                      description=data['description'],
                                                      color=data['color'],
                                                      golfcourse_id=list_data[i]['golfcourse'],
                                                      status=data['status'])
                price_types = PriceType.objects.filter(golfcourse=golfcourse_id)
                for price_type in price_types:
                    PriceMatrix.objects.bulk_create([
                        PriceMatrix(guest_type=guest_type, price_type=price_type, date_type='weekend',
                                    matrix_log=matrix_log),
                        PriceMatrix(guest_type=guest_type, price_type=price_type, date_type='weekday',
                                    matrix_log=matrix_log),
                        PriceMatrix(guest_type=guest_type, price_type=price_type, date_type='holiday',
                                    matrix_log=matrix_log)
                    ])
        return Response({'status': 200, 'detail': 'OK', 'code': 'OK'}, status=200)

    def list(self, request, *args, **kwargs):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        result = GuestType.objects.filter(golfcourse=golfstaff.golfcourse)
        serializer = GuestTypeSerializer(result, many=True)
        return Response(serializer.data, status=200)


class PriceTypeViewSet(viewsets.ModelViewSet):
    queryset = PriceType.objects.all()
    serializer_class = PriceTypeSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        list_data = request.DATA['price_type']
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        for data in list_data:
            data.update({'golfcourse': golfstaff.golfcourse.id})
        serializers = PriceTypeSerializer(data=list_data, many=True)
        if not serializers.is_valid():
            return Response(serializers.errors, status=400)
        matrix_logs = PriceMatrixLog.objects.filter(golfcourse=golfstaff.golfcourse)
        if matrix_logs:
            matrix_log = matrix_logs[0]
        else:
            matrix_log = PriceMatrixLog.objects.create(golfcourse=golfstaff.golfcourse)
        for i, data in enumerate(serializers.data):
            if 'id' in list_data[i]:
                PriceType.objects.filter(id=list_data[i]['id']).update(
                    from_time=data['from_time'],
                    to_time=data['to_time'],
                    description=data['description'],
                    status=data['status']
                )
            else:
                golfcourse_id = list_data[i]['golfcourse']
                price_type = PriceType.objects.create(from_time=data['from_time'],
                                                      to_time=data['to_time'],
                                                      description=data['description'],
                                                      golfcourse_id=golfcourse_id,
                                                      status=data['status'])
                guest_types = GuestType.objects.filter(golfcourse_id=golfcourse_id)
                for guest_type in guest_types:
                    PriceMatrix.objects.bulk_create([
                        PriceMatrix(guest_type=guest_type, price_type=price_type, date_type='weekend',
                                    matrix_log=matrix_log),
                        PriceMatrix(guest_type=guest_type, price_type=price_type, date_type='weekday',
                                    matrix_log=matrix_log),
                        PriceMatrix(guest_type=guest_type, price_type=price_type, date_type='holiday',
                                    matrix_log=matrix_log)
                    ])
        return Response({'status': 200, 'detail': 'OK', 'code': 'OK'}, status=200)

    def list(self, request, *args, **kwargs):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        result = PriceType.objects.filter(golfcourse=golfstaff.golfcourse)
        serializer = PriceTypeSerializer(result, many=True)
        return Response(serializer.data, status=200)


class PriceMatrixLogViewSet(mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            GenericViewSet):
    queryset = PriceMatrixLog.objects.all()
    serializer_class = PriceMatrixLogSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, IsGolfStaff)

    def list(self, request, *args, **kwargs):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        hole = request.QUERY_PARAMS.get('hole', 9)
        logs = PriceMatrixLog.objects.filter(golfcourse=golfstaff.golfcourse, hole=hole)
        if not logs:
            return Response([], status=200)
        serialziers = PriceMatrixLogSerializer(logs, many=True)

        first_result = logs[0]
        mats = first_result.price_matrix.all()
        price_types = mats.filter(price_type__status=ACTIVE).values('price_type', 'price_type__description').distinct(
            'price_type')
        guest_types = mats.filter(guest_type__status=ACTIVE).order_by('guest_type').values('guest_type',
                                                                                           'guest_type__name',
                                                                                           'guest_type__color').distinct(
            'guest_type')
        date_types = mats.order_by('date_type').values('date_type', 'date').distinct('date_type')

        mat_serializer = PriceMatrixSerializer(mats)
        serialziers.data[0].update({'matrix'    : mat_serializer.data, 'price_type': price_types,
                                    'guest_type': guest_types,
                                    'date_type' : date_types})
        return Response(serialziers.data, status=200)

    def retrieve(self, request, pk=None):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)

        log = get_or_none(PriceMatrixLog, pk=pk, golfcourse=golfstaff.golfcourse)
        if not log:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Item can not be found'}, status=404)
        serialziers = PriceMatrixLogSerializer(log)

        mats = log.price_matrix.all()
        price_types = mats.filter(price_type__status=ACTIVE).values('price_type', 'price_type__description').distinct(
            'price_type')
        guest_types = mats.filter(guest_type__status=ACTIVE).order_by('guest_type').values('guest_type',
                                                                                           'guest_type__name',
                                                                                           'guest_type__color').distinct(
            'guest_type')
        date_types = mats.order_by('date_type').values('date_type', 'date').distinct('date_type')

        mat_serializer = PriceMatrixSerializer(mats)
        serialziers.data.update({'matrix'   : mat_serializer.data, 'price_type': price_types, 'guest_type': guest_types,
                                 'date_type': date_types})
        return Response(serialziers.data, status=200)

    def partial_update(self, request, pk=None):
        golfstaff = get_or_none(GolfCourseStaff, user=request.user)
        if not golfstaff:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        request.DATA.update({'golfcourse': golfstaff.golfcourse_id})
        for data in request.DATA['matrix']:
            data.update({'matrix_log': pk})
        log = get_or_none(PriceMatrixLog, pk=pk, golfcourse=golfstaff.golfcourse)
        if not log:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Item can not be found'}, status=404)

        if (log.effective_date and log.effective_date != datetime.datetime.strptime(request.DATA['effective_date'],
                                                                                    '%Y-%m-%d').date()) or log.hole != \
                request.DATA['hole']:
            serializers = PriceMatrixLogSerializer(data=request.DATA)
            if not serializers.is_valid():
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': serializers.errors}, status=400)
            serializers.save()
            return Response(serializers.data, status=200)
        return super(PriceMatrixLogViewSet, self).partial_update(request, pk)


class RecurringTeetimeViewSet(APIView):
    serializer_class = RecurringTeetimeSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def get_object(self, pk=None, golfcourse=None, from_time=None, to_time=None):
        try:
            if pk:
                return get_or_none(RecurringTeetime, id=pk)
            else:
                return get_or_none(RecurringTeetime, golfcourse=golfcourse)
        except:
            return None

    def get(self, request, format=None):
        staff = get_or_none(GolfCourseStaff, user=request.user)
        if staff is None:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        query = self.get_object(golfcourse=staff.golfcourse)
        data = {}
        if query:
            data = RecurringTeetimeSerializer(query).data

        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': data}, status=200)

    def post(self, request, key=None):
        staff = get_or_none(GolfCourseStaff, user=request.user)
        if staff is None:
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        data = request.DATA
        gc = staff.golfcourse
        if data is None:
            return Response({"code": "E_NOT_FOUND", "detail": "Empty data input"}, status=400)
        query, created = RecurringTeetime.objects.get_or_create(golfcourse=gc)
        query.recurring_freq = data['recurring_freq']
        query.publish_period = data['publish_period']
        query.save()
        ###### Make test for Ms.Thao
        import_teetime_recurring_queue.delay()
        serializer = RecurringTeetimeSerializer(query)
        return Response({'status': '200', 'code': 'SUCCESS',
                         'detail': serializer.data or {}}, status=200)


@api_view(['PUT'])
def import_teetime_recurring(request):
    import_teetime_recurring_queue.delay()
    return Response({'status': '200', 'code': 'SUCCESS'}, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_teetime_discount(request):
    golfcourse_name = request.DATA['golfcourse']
    gc = GolfCourse.objects.filter(name=golfcourse_name).first()
    if not gc:
        return Response({'detail': 'Not found'}, status=404)

    golfstaff = get_or_none(GolfCourseStaff, user=request.user, golfcourse=gc)
    if not golfstaff:
        return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                         'detail': 'You do not have permission to peform this action'}, status=401)

    date = request.DATA['date']
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    from_time = request.DATA['from_time']
    to_time = request.DATA['to_time']
    if from_time:
        from_time = datetime.datetime.strptime(from_time, '%H:%M').time()

    if to_time:
        to_time = datetime.datetime.strptime(to_time, '%H:%M').time()
    discount = request.DATA['discount']

    query = TeeTimePrice.objects.filter(teetime__golfcourse=gc, teetime__date=date)
    if from_time:
        query = TeeTimePrice.objects.filter(teetime__golfcourse=gc, teetime__date=date, teetime__time__gte=from_time)

    if to_time:
        query = TeeTimePrice.objects.filter(teetime__golfcourse=gc, teetime__date=date, teetime__time__gte=from_time,
                                            teetime__time__lte=to_time)

    count = query.update(online_discount=discount)

    return Response({'detail': count}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def archived_teetime(request):
    # TeeTime.objects.filter(date__lte='2015-11-20').delete()
    today = datetime.date.today()
    first = today.replace(day=1)
    last_month = first - datetime.timedelta(days=1)
    first_last_month = last_month.replace(day=1)
    booked_teetime_list = BookedTeeTime.objects.filter(teetime__date__lte=first_last_month).values_list('teetime__id',
                                                                                                        flat=True)
    # print(booked_teetime_list)
    teetime_list = TeeTime.objects.filter(date__lt=first_last_month).exclude(id__in=booked_teetime_list)
    serializers = ArchivedTeetimeSerializer(teetime_list)
    monthly_archive_teetime.delay(serializers.data)
    return Response({'detail': 'OK', 'status': 200}, status=200)
