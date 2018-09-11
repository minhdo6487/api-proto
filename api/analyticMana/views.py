import datetime
from datetime import timedelta

import operator
from api.bookingMana.serializers import BookedTeeTimeSerializer, BookedTeeTime_HistorySerializer
from api.bookingMana.views import get_gc24_booked_teetime_price
from collections import Counter, OrderedDict
from core.booking.models import BookedTeeTime, BookedTeeTime_History, BookedBuggy, PayTransactionStore
from core.golfcourse.models import GolfCourseStaff
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

# from api.bookingMana.views import make_teetime
from core.teetime.models import TeeTime
from utils.django.models import get_or_none

DAY = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sar', 'Sun']
TRANSACTION_STR = '{}-{}'


def week_range(date):
    """Find the first/last day of the week for the given day.
    Assuming weeks start on Sunday and end on Saturday.

    Returns a tuple of ``(start_date, end_date)``.

    """
    # isocalendar calculates the year, week of the year, and day of the week.
    # dow is Mon = 1, Sat = 6, Sun = 7
    year, week, dow = date.isocalendar()

    # Find the first day of the week.
    if dow == 1:
        # Since we want to start with Monday, let's test for that condition.
        start_date = date
    else:
        # Otherwise, subtract `dow` number days to get the first day
        start_date = date - timedelta(dow - 1)

    # Now, add 6 for the last day of the week (i.e., count up to Saturday)
    end_date = start_date + timedelta(6)

    return (start_date, end_date)

def week_date(date):
    year, week, dow = date.isocalendar()
    return dow

# =================== Get Booking View ==============================
@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_analytic_booking_by_day(request):
    staff = get_or_none(GolfCourseStaff, user=request.user)
    results = {}
    if staff:
        golfcourse = staff.golfcourse
        date = request.QUERY_PARAMS.get('date', '')
        if date == '':
            date = datetime.date.today()
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        results = analytic_booking_by_day(golfcourse, date)
    return Response(results, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_analytic_booking_by_week(request):
    staff = get_or_none(GolfCourseStaff, user=request.user)
    results = {}
    if staff:
        golfcourse = staff.golfcourse
        date = request.QUERY_PARAMS.get('date', '')
        if date == '':
            date = datetime.date.today()
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        results = analytic_booking_by_week(golfcourse, date)
    return Response(results, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_analytic_booking(request):
    staff = get_or_none(GolfCourseStaff, user=request.user)
    if not staff:
        return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                         'detail': 'You do not have permission to peform this action'}, status=401)
    results = {}
    golfcourse = staff.golfcourse
    date = request.QUERY_PARAMS.get('date', '')
    if date == '':
        date = datetime.date.today()
    else:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    get_by = request.QUERY_PARAMS.get('get_by', 'date')
    if get_by == 'day':
        results = analytic_booking_by_day(golfcourse, date)
    elif get_by == 'week':
        results = analytic_booking_by_week(golfcourse, date)
    elif get_by == 'month':
        results = analytic_booking_by_month(golfcourse, date)
    elif get_by == 'year':
        results = analytic_booking_by_year(golfcourse, date)
    return Response(results, status=200)


# =================== Get Booking Report ==============================

TIME_START = datetime.time(5, 0, 0)
TIME_END = datetime.time(22, 0, 0)
TIME_FRAME = [
    {'from': 4, 'to': 7.5, 'key': 'Before 8:00'},
    {'from': 8, 'to': 9.5, 'key': '8:00 - 10:00'},
    {'from': 10, 'to': 11.5, 'key': '10:00 - 12:00'},
    {'from': 12, 'to': 13.5, 'key': '12:00 - 14:00'},
    {'from': 14, 'to': 15.5, 'key': '14:00 - 16:00'},
    {'from': 16, 'to': 23, 'key': 'After 16:00'}
]


def analytic_booking(teetimes, booked_teetimes):
    results = {}
    # checkin = Checkin.objects.filter(golfcourse=golfcourse, date=date)
    # teetimes = TeeTime.objects.filter(date=date, golfcourse=golfcourse)
    # booked_teetimes = TeeTime.objects.filter(golfcourse=golfcourse, date=date,is_booked=True).select_related('booked_teetime')
    book_count = booked_teetimes.count()
    # played_count = len(checkin)
    total_teetime = len(teetimes)
    # on_premise_amount = sum(value.total_amount for value in checkin)
    in_coming_amount = sum(value.booked_teetime.first().total_cost for value in booked_teetimes if
                           value.booked_teetime.first().status == 'P')
    booked_type_count = Counter(value.booked_teetime.first().book_type for value in booked_teetimes)
    direct = booked_type_count['D']
    walkin = booked_type_count['W']
    phone = booked_type_count['P'] + booked_type_count['E']
    booked_type = {'direct': direct, 'phone': phone, 'walkin': walkin}
    # hour_played = Counter(value.time.hour for value in checkin)
    hour_booked_teetime = Counter(t.time.hour for t in booked_teetimes)
    play_by_hour = {}
    book_by_hour = []
    map_teetime_by_hour = {}
    revenue_by_hour = {}
    for t in booked_teetimes:
        if t.time.hour not in map_teetime_by_hour:
            map_teetime_by_hour.update({
                t.time.hour: int(t.booked_teetime.first().total_cost)
            })
        else:
            map_teetime_by_hour[t.time.hour] += int(t.booked_teetime.first().total_cost)
    for i in range(TIME_START.hour, TIME_END.hour + 1):
        # if hour_played[i]:
        #     play_by_hour.append({i: hour_played[i]})
        # else:
        #     play_by_hour.append({i: 0})
        if hour_booked_teetime[i]:
            play_by_hour.update({i: hour_booked_teetime[i]})
        else:
            play_by_hour.update({i: 0})
        if i in map_teetime_by_hour:
            revenue_by_hour.update({i: map_teetime_by_hour[i]})
        else:
            revenue_by_hour.update({i: 0})
    revenue_by_time_frame = {}
    for tf in TIME_FRAME:
        _item = {tf['key']: 0}
        for r in revenue_by_hour:
            if 'Before' in tf['key'] and int(r) <= tf['to']:
                _item[tf['key']] += revenue_by_hour[r]
            elif 'After' in tf['key'] and int(r) >= tf['from']:
                _item[tf['key']] += revenue_by_hour[r]
            elif tf['from'] <= int(r) <= tf['to']:
                _item[tf['key']] += revenue_by_hour[r]
        revenue_by_time_frame.update(_item)
    results.update({'book_teetime_count': book_count,
                    'book_by_hour': book_by_hour,
                    'book_type': booked_type,
                    'in_coming_amount': in_coming_amount,
                    'play_by_hour': play_by_hour,
                    # 'played_teetime_count': played_count,
                    'total_teetime': total_teetime,
                    # 'on_premise_amount': on_premise_amount,
                    'revenue_by_hour': revenue_by_hour,
                    'revenue_by_time_frame': revenue_by_time_frame
                    # 'total_checkin': len(checkin)
                    })

    return results


def analytic_booking_by_day(golfcourse, date):
    teetimes = TeeTime.objects.filter(date=date, golfcourse=golfcourse)
    booked_teetimes = TeeTime.objects.filter(golfcourse=golfcourse, date=date, is_booked=True).select_related(
        'booked_teetime')
    return analytic_booking(teetimes, booked_teetimes)


def analytic_booking_by_week(golfcourse, date):
    start_date = week_range(date)[0]
    results = []
    for i in range(0, 7):
        date = start_date + timedelta(i)
        teetimes = TeeTime.objects.filter(date=date, golfcourse=golfcourse)
        booked_teetimes = TeeTime.objects.filter(golfcourse=golfcourse, date=date, is_booked=True).select_related(
            'booked_teetime')
        booking_analytic = analytic_booking(teetimes, booked_teetimes)
        booking_analytic.update({'date': date})
        results.append({DAY[i]: booking_analytic})
    return results


def analytic_booking_by_month(golfcourse, date):
    results = []
    date = datetime.date(date.year, date.month, 1)
    while date.weekday() != 0:
        date += timedelta(1)
    for i in range(0, 4):
        start_date, end_date = week_range(date)
        teetimes = TeeTime.objects.filter(date__range=(start_date, end_date), golfcourse=golfcourse)
        booked_teetimes = TeeTime.objects.filter(golfcourse=golfcourse, date__range=(start_date, end_date),
                                                 is_booked=True).select_related(
            'booked_teetime')
        booking_analytic = analytic_booking(teetimes, booked_teetimes)
        booking_analytic.update({'date': start_date})
        results.append({i: booking_analytic})
        date += timedelta(7)
    return results


def analytic_booking_by_year(golfcourse, date):
    results = []
    for i in range(1, 13):
        teetimes = TeeTime.objects.filter(date__year=date.year, date__month=i, golfcourse=golfcourse)
        booked_teetimes = TeeTime.objects.filter(golfcourse=golfcourse, date__year=date.year, date__month=i,
                                                 is_booked=True).select_related(
            'booked_teetime')
        booking_analytic = analytic_booking(teetimes, booked_teetimes)
        start_date = datetime.date(date.year, i, 1)
        booking_analytic.update({'date': start_date})
        results.append({i: booking_analytic})
    return results


# =================== Get Player Report ==============================
@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_analytic_player(request):
    staff = get_or_none(GolfCourseStaff, user=request.user)
    if not staff:
        return Response({'status': 403, 'detail': 'Permission denied'}, status=403)
    golfcourse = staff.golfcourse
    date = request.QUERY_PARAMS.get('date', '')
    if date == '':
        date = datetime.date.today()
    else:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()

    get_by = request.QUERY_PARAMS.get('get_by', 'date')
    if get_by == 'day':
        results = analytic_player_by_day(golfcourse, date)
    elif get_by == 'week':
        results = analytic_player_by_week(golfcourse, date)
    elif get_by == 'month':
        results = analytic_player_by_month(golfcourse, date)
    elif get_by == 'year':
        results = analytic_player_by_year(golfcourse, date)
    return Response(results, status=200)


def analytic_player(booked_teetime):
    results = {}
    serializer = BookedTeeTimeSerializer(booked_teetime)
    actual_rev = 0
    no_show = 0
    total = 0
    for user in serializer.data:
        total += int(user['total_cost'])
        if user['checkin']:
            actual_rev += int(user['total_cost'])
        else:
            no_show += 1
    loss_rev = total - actual_rev
    results.update({'players': serializer.data,
                    'actual_rev': actual_rev,
                    'no_show': no_show,
                    'loss_rev': loss_rev,
                    'total': total})
    return results


def analytic_player_by_day(golfcourse, date):
    teetimes = booked_teetime = BookedTeeTime.objects.filter(golfcourse=golfcourse, teetime__date=date)
    return analytic_booking(teetimes)


def analytic_player_by_week(golfcourse, date):
    start_date = week_range(date)[0]
    results = []
    for i in range(0, 7):
        date = start_date + timedelta(i)
        teetimes = BookedTeeTime.objects.filter(golfcourse=golfcourse, teetime__date=date)
        player_analytic = analytic_player(teetimes)
        player_analytic.update({'date': date})
        results.append({DAY[i]: player_analytic})
    return results


def analytic_player_by_month(golfcourse, date):
    results = []
    date = datetime.date(date.year, date.month, 1)
    while date.weekday() != 0:
        date += timedelta(1)
    for i in range(0, 4):
        start_date, end_date = week_range(date)
        teetimes = BookedTeeTime.objects.filter(golfcourse=golfcourse, teetime__date__range=(start_date, end_date))
        player_analytic = analytic_player(teetimes)
        player_analytic.update({'date': start_date})
        results.append({i: player_analytic})
        date += timedelta(7)
    return results


def analytic_player_by_year(golfcourse, date):
    results = []
    for i in range(1, 13):
        teetimes = BookedTeeTime.objects.filter(golfcourse=golfcourse, teetime__date__year=date.year,
                                                teetime__date__month=i)
        player_analytic = analytic_player(teetimes)
        start_date = datetime.date(date.year, i, 1)
        player_analytic.update({'date': start_date})
        results.append({i: player_analytic})
    return results


BOOKING_STATUS = dict(N='booking_request', F='paid')


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_booking_report(request):
    query_params = get_query_params(request)
    booked_teetime = BookedTeeTime.objects.filter(**query_params).order_by('teetime__date')
    serializer = BookedTeeTimeSerializer(booked_teetime)
    revenue_counter = OrderedDict()
    summary = OrderedDict(player_count=0, total_amount=0, no_round=0)
    summary_info = OrderedDict(weekday_round=0, weekend_round=0, paid_online_round=0, paid_later_round=0, web=0, ios=0, android=0)
    for tt in serializer.data:
        if tt['payment_status']:
            payment_status = 'paid'
        else:
            payment_status = 'unpaid'
        d = get_key_date(tt)
        if d not in revenue_counter:
            revenue_counter[d] = dict(paid=0, unpaid=0)
        revenue_counter[d][payment_status] += 1
        summary['player_count'] += tt['player_count']
        summary['total_amount'] += int(tt['total_cost'])
        summary['no_round'] += 1

        if week_date(datetime.datetime.fromtimestamp(int(tt['teetime_date']/1000))) < 6:
            summary_info['weekday_round'] += 1
        else:
            summary_info['weekend_round'] += 1

        if tt['payment_type'] == 'F':
            summary_info['paid_online_round'] += 1
        else:
            summary_info['paid_later_round'] += 1

        if tt['user_device'] == 'ios':
            summary_info['ios'] += 1
        elif tt['user_device'] == 'and':
            summary_info['android'] += 1
        else:
            summary_info['web'] += 1
    summary_result = []
    for k in summary:
        summary_result.append({'name': k.replace('_', ' ').capitalize(), 'amount': to_decimal(summary[k])})
    for k in summary_info:
        percentage = round(summary_info[k]/summary['no_round']*100, 2) if summary['no_round'] else 0
        summary_info[k] = "{0} | {1}%".format(summary_info[k],percentage)
        summary_result.append({'name': k.replace('_', ' ').capitalize(), 'amount': summary_info[k]})
    sort_revenue_counter = OrderedDict(
        sorted(revenue_counter.items(), key=lambda t: datetime.datetime.strptime(t[0], '%d-%m-%Y')))
    filterresult = ['Player count','Total amount','No round','Weekday round','Weekend round','Paid online round','Paid later round', 'Web', 'Ios','Android']
    filterdict = dict((k,i) for i,k in enumerate(filterresult))
    summary_result = sorted(summary_result, key=lambda x: filterdict[x['name']])
    return Response({'report': sort_revenue_counter, 'details': serializer.data, 'summary': summary_result}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_booking_gcar(request):
    query_params = get_query_params(request, True)
    query_params.update({'status': 'I'})
    booked_teetime = BookedTeeTime.objects.filter(**query_params).order_by('teetime__date')
    serializer = BookedTeeTimeSerializer(booked_teetime)
    summary = dict()
    for tt in serializer.data:
        gc_unit_green_fee = get_gc_price(tt['id'])
        gc_unit_buggy_fee = get_gc_buggy_price(tt['id'], tt['hole'])
        green_fee = gc_unit_green_fee * tt['player_checkin_count']
        buggy_fee = gc_unit_buggy_fee * tt['buggy_qty']
        tt['paid_amount'] = get_checkin_amount(tt)
        amount = get_ar_ap_amount(tt, green_fee, buggy_fee)
        tt.update(
            {'amount': to_decimal(amount),
             'gc_unit_green_fee': to_decimal(gc_unit_green_fee),
             'gc_unit_buggy_fee': to_decimal(gc_unit_buggy_fee)})
        if tt['golfcourse_name'] not in summary:
            summary[tt['golfcourse_name']] = 0
        summary[tt['golfcourse_name']] += amount
    summary_result = []
    for k in summary:
        summary_result.append({'name': k, 'amount': to_decimal(summary[k])})

    return Response({'details': serializer.data, 'summary': summary_result}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_booking_vendor(request):
    options = {
        'book': 2,
        'cancel': 4,
        'all': 6
    }
    query_params = get_query_params(request)
    option = int(request.QUERY_PARAMS.get('option', 6))

    transactions = []
    data = []
    if (option & options['cancel']) != 0:
        cancel_teetimes = get_cancel_teetime(query_params)
        transactions = [('t{}'.format(t['booked_teetime'] if t.get('booked_teetime') else t.get('id')), 'cancel') for
                        t in cancel_teetimes]
        data += cancel_teetimes

    if (option & options['book']) != 0:
        query_params.update(dict(payment_type='F', payment_status=True))
        booked_teetime = BookedTeeTime.objects.filter(**query_params).order_by('teetime__date')
        serializer = BookedTeeTimeSerializer(booked_teetime)
        transactions += [('t{}'.format(t['id']), 'book') for t in serializer.data]
        data += serializer.data

    pay_info = get_card_fee(transactions)

    revenue_counter = OrderedDict()
    summary = dict()

    for tt in data:
        d = get_key_date(tt)
        if d not in revenue_counter:
            revenue_counter[d] = dict(book=0, cancel=0)

        if tt['status'] == 'I' and tt['player_checkin_count'] != tt['player_count']:
            tt['status'] = 'PI'  # Update status

        if tt.get('booked_teetime'):
            revenue_counter[d]['cancel'] += 1
        else:
            revenue_counter[d]['book'] += 1

        # Because no save paid_amount when book and pay online. Get total cost here
        tt['paid_amount'] = tt['total_cost']
        fee = get_vendor_fee(pay_info, tt)
        vendor = fee.get('vendor')
        # Compute checkin amount
        checkin_amount = get_checkin_amount(tt)

        cancel_amount = tt['paid_amount'] - checkin_amount if tt['status'] in ['C', 'PC'] else 0
        
        total_vendor_fee = fee.get('total_vendor_fee', 0)
        vendor_payable = abs(fee.get('vendor_payable', 0) - float(cancel_amount))
        vendor_payable *= (-1 if tt['status'] in ['C', 'PC'] else 1)
        tt.update({'vendor_fee': to_decimal(fee['vendor_fee']),
                   'entry_fee': to_decimal(fee['entry_fee']),
                   'total_vendor_fee': to_decimal(total_vendor_fee),
                   'vendor_payable': to_decimal(vendor_payable),
                   'card_fee': fee.get('card_fee_str'),
                   'bank_code': fee.get('bank_code'),
                   'vendor': vendor,
                   'checkin_amount': checkin_amount,
                   'cancel_amount': cancel_amount})
        if vendor not in summary:
            summary[vendor] = dict(fee=0, pay=0)
        summary[vendor]['fee'] += total_vendor_fee
        summary[vendor]['pay'] += vendor_payable
    summary_result = []
    sum_fee = 0
    sum_pay = 0
    for k in summary:
        summary_result.append({'name': k, 'fee': to_decimal(summary[k]['fee']), 'pay': to_decimal(summary[k]['pay'])})
        sum_fee += summary[k]['fee']
        sum_pay += summary[k]['pay']
    summary_result.append({'name': 'Total', 'fee': to_decimal(sum_fee), 'pay': to_decimal(sum_pay)})
    sort_revenue_counter = OrderedDict(
        sorted(revenue_counter.items(), key=lambda t: datetime.datetime.strptime(t[0], '%d-%m-%Y')))
    return Response({'report': sort_revenue_counter, 'details': data, 'summary': summary_result}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_booking_cancel(request):
    query_params = get_query_params(request)
    cancel_teetimes = get_cancel_teetime(query_params)
    # transactions += [('t{}'.format(t['booked_teetime'] if t.get('booked_teetime') else t.get('id')), 'cancel') for
    #                  t in cancel_teetimes]
    revenue_counter = OrderedDict()
    summary = OrderedDict([('player_count', 0), ('no_round', 0), ('cancelled_amount', 0), ('refunded_amount', 0)])
    for tt in cancel_teetimes:
        if tt['payment_status']:
            booking_status = 'paid'
        else:
            booking_status = 'unpaid'
        tt.update({'booking_status': booking_status,
                   'penalty': 'No',
                   'refunded_amount': 0,
                   'refunded_percent': 0,
                   'refunded_status': 'Not Refund'})
        key_date = get_key_date(tt)
        if key_date not in revenue_counter:
            revenue_counter[key_date] = dict(paid=0, unpaid=0)
        revenue_counter[key_date][booking_status] += 1
        summary['player_count'] += tt['player_count']
        summary['no_round'] += 1
        summary['cancelled_amount'] += int(tt['total_cost'])
        if tt['payment_type'] == 'F':
            summary['refunded_amount'] += tt['total_cost']
            tt['refunded_amount'] = int(tt['total_cost'])
            tt['refunded_percent'] = float(tt['refunded_amount']) / float(tt['total_cost'])
    summary_result = []
    for k in summary:
        summary_result.append({'name': k.replace('_', ' ').capitalize(), 'amount': to_decimal(summary[k])})
    sort_revenue_counter = OrderedDict(
        sorted(revenue_counter.items(), key=lambda t: datetime.datetime.strptime(t[0], '%d-%m-%Y')))
    return Response({'report': sort_revenue_counter, 'details': cancel_teetimes, 'summary': summary_result}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsAdminUser))
def get_booking_rp(request):
    options = {
        'book': 2,
        'cancel': 4,
        'played': 8,
        'all': 14
    }
    query_params = get_query_params(request)
    revenue_counter = OrderedDict()
    result = []
    summary_item = OrderedDict([('no_round', 0), ('no_golfer', 0), ('revenues', 0), ('gross_profits', 0)])
    summary = OrderedDict(
        [('booked', summary_item.copy()), ('booked_noshow', summary_item.copy()), ('played', summary_item.copy()), ('cancelled', summary_item.copy()),
         ('penalty', summary_item.copy()), ('total', summary_item.copy())])
    option = int(request.QUERY_PARAMS.get('option', 14))

    if (option & options['cancel']) != 0:  # Get cancel teetime
        cancel_teetimes = get_cancel_teetime(query_params)
        transaction_ids = [('t{}'.format(t['booked_teetime'] if t.get('booked_teetime') else t.get('id')), 'cancel') for
                           t in cancel_teetimes]
        pay_info = get_card_fee(transaction_ids)

        for tt in cancel_teetimes:
            tt['date'] = datetime.datetime.strptime(tt['date'], '%Y-%m-%d').date().strftime('%d-%m-%Y')
            key_date = get_key_date(tt)
            if key_date not in revenue_counter:
                revenue_counter[key_date] = {'cancelled': 0, 'booked': 0, 'played': 0}
            revenue_counter[key_date]['cancelled'] += 1
            if tt['status'] == 'C':
                summary['cancelled']['no_golfer'] += tt['player_count']
            elif tt['status'] == 'PC':
                summary['cancelled']['no_golfer'] += tt['player_count'] - tt['player_checkin_count']
            summary['cancelled']['no_round'] += 1
            book_fee = get_vendor_fee(pay_info, tt)
            total_vendor_fee = -book_fee['total_vendor_fee']
            tt['paid_amount'] = book_fee['paid_amount']
            # Compute checkin amount
            checkin_amount = get_checkin_amount(tt)
            cancel_amount = tt['paid_amount'] - checkin_amount if tt['status'] in ['C', 'PC'] else 0

            tt.update({'total_vendor_fee': to_decimal(total_vendor_fee),
                       'profit_loss': to_decimal(total_vendor_fee),
                       'checkin_amount': checkin_amount,
                       'cancel_amount': cancel_amount})
            summary['cancelled']['gross_profits'] += total_vendor_fee
        result += cancel_teetimes
        revenue_counter = OrderedDict(sorted(revenue_counter.items()))

    if (option & options['book']) != 0:
        now = datetime.datetime.now()
        booked_teetime = BookedTeeTime.objects.filter(payment_status=True, teetime__date__gte=now, **query_params).exclude(
            status__in=['I', 'R']) \
            .order_by('teetime__date')
        booked_serializer = BookedTeeTimeSerializer(booked_teetime)
        transaction_ids = [('t{}'.format(t['id']), 'book') for t in booked_serializer.data]
        pay_info = get_card_fee(transaction_ids)

        for tt in booked_serializer.data:
            tt['date'] = datetime.datetime.strptime(tt['date'], '%Y-%m-%d').date().strftime('%d-%m-%Y')
            key_date = get_key_date(tt)
            if key_date not in revenue_counter:
                revenue_counter[key_date] = {'cancelled': 0, 'booked': 0, 'played': 0}

            # Get gc green fee and buggy fee
            gc_unit_green_fee = get_gc_price(tt['id'])
            gc_unit_buggy_fee = get_gc_buggy_price(tt['id'], tt['hole'])

            # Compute card fee
            book_fee = get_vendor_fee(pay_info, tt)
            total_vendor_fee = book_fee['total_vendor_fee']
            tt['paid_amount'] = book_fee['paid_amount']

            # Compute profit/lost + revenue
            profit_loss = ((int(tt['unit_price']) - gc_unit_green_fee) * tt['player_count']) + \
                          ((int(tt['buggy_unit_price']) - gc_unit_buggy_fee) * tt['buggy_qty']) - \
                          int(tt['voucher_discount_amount']) - int(total_vendor_fee)

            revenue = int(tt['total_cost']) #- int(tt['voucher_discount_amount'])

            # Update summary
            summary['booked']['gross_profits'] += int(profit_loss)
            summary['booked']['no_golfer'] += tt['player_count']
            summary['booked']['revenues'] += revenue
            summary['booked']['no_round'] += 1
            revenue_counter[key_date]['booked'] += 1

            # Update details
            tt.update({'total_vendor_fee': to_decimal(total_vendor_fee),
                       'profit_loss': to_decimal(profit_loss),
                       'total_revenue': to_decimal(revenue),
                       'gc_unit_green_fee': to_decimal(gc_unit_green_fee),
                       'gc_unit_buggy_fee': to_decimal(gc_unit_buggy_fee)
                       })
        result += booked_serializer.data

        #############
        booked_teetime = BookedTeeTime.objects.filter(payment_status=True, teetime__date__lt=now, **query_params).exclude(
            status__in=['I', 'R']) \
            .order_by('teetime__date')
        booked_serializer = BookedTeeTimeSerializer(booked_teetime)
        transaction_ids = [('t{}'.format(t['id']), 'book') for t in booked_serializer.data]
        pay_info = get_card_fee(transaction_ids)

        for tt in booked_serializer.data:
            tt['date'] = datetime.datetime.strptime(tt['date'], '%Y-%m-%d').date().strftime('%d-%m-%Y')
            key_date = get_key_date(tt)
            if key_date not in revenue_counter:
                revenue_counter[key_date] = {'cancelled': 0, 'booked': 0, 'played': 0}

            # Get gc green fee and buggy fee
            gc_unit_green_fee = get_gc_price(tt['id'])
            gc_unit_buggy_fee = get_gc_buggy_price(tt['id'], tt['hole'])

            # Compute card fee
            book_fee = get_vendor_fee(pay_info, tt)
            total_vendor_fee = book_fee['total_vendor_fee']
            tt['paid_amount'] = book_fee['paid_amount']

            # Compute profit/lost + revenue
            profit_loss = ((int(tt['unit_price']) - gc_unit_green_fee) * tt['player_count']) + \
                          ((int(tt['buggy_unit_price']) - gc_unit_buggy_fee) * tt['buggy_qty']) - \
                          int(tt['voucher_discount_amount']) - int(total_vendor_fee)

            revenue = int(tt['total_cost']) #- int(tt['voucher_discount_amount'])

            # Update summary
            summary['booked_noshow']['gross_profits'] += int(profit_loss)
            summary['booked_noshow']['no_golfer'] += tt['player_count']
            summary['booked_noshow']['revenues'] += revenue
            summary['booked_noshow']['no_round'] += 1
            revenue_counter[key_date]['booked'] += 1

            tt.update({'total_vendor_fee': to_decimal(total_vendor_fee),
                       'profit_loss': to_decimal(profit_loss),
                       'total_revenue': to_decimal(revenue),
                       'gc_unit_green_fee': to_decimal(gc_unit_green_fee),
                       'gc_unit_buggy_fee': to_decimal(gc_unit_buggy_fee)
                       })

        result += booked_serializer.data
        ############
    if (option & options['played']) != 0:
        played_teetime = BookedTeeTime.objects.filter(status='I', **query_params).order_by('teetime__date')
        played_serializer = BookedTeeTimeSerializer(played_teetime)
        transaction_ids = [('t{}'.format(t['id']), 'book') for t in played_serializer.data]
        pay_info = get_card_fee(transaction_ids)

        for tt in played_serializer.data:
            tt['date'] = datetime.datetime.strptime(tt['date'], '%Y-%m-%d').date().strftime('%d-%m-%Y')
            key_date = get_key_date(tt)
            if key_date not in revenue_counter:
                revenue_counter[key_date] = {'cancelled': 0, 'booked': 0, 'played': 0}

            if tt['player_checkin_count'] != tt['player_count']:
                tt['status'] = 'PI'  # Update status
            gc_unit_green_fee = get_gc_price(tt['id'])
            gc_unit_buggy_fee = get_gc_buggy_price(tt['id'], tt['hole'])
            green_fee = gc_unit_green_fee * tt['player_checkin_count']
            buggy_fee = gc_unit_buggy_fee * tt['buggy_qty']

            # Compute card fee
            book_fee = get_vendor_fee(pay_info, tt)

            total_vendor_fee = book_fee['total_vendor_fee']
            tt['paid_amount'] = book_fee['paid_amount']
            ar_ap_amount = get_ar_ap_amount(tt, green_fee, buggy_fee)

            # Compute profit/lost + revenue
            checkin_amount = get_checkin_amount(tt)
            variance = ((int(tt['unit_price']) - gc_unit_green_fee) * tt['player_checkin_count']) + \
                       (int(tt['buggy_unit_price']) - gc_unit_buggy_fee) * tt['buggy_qty']
            profit_loss = variance - int(tt['voucher_discount_amount']) - int(total_vendor_fee)

            revenue = checkin_amount
            revenue_counter[key_date]['played'] += 1

            summary['played']['gross_profits'] += profit_loss
            summary['played']['no_golfer'] += tt['player_count']
            summary['played']['revenues'] += revenue
            summary['played']['no_round'] += 1
            tt.update({'total_vendor_fee': to_decimal(total_vendor_fee),
                       'profit_loss': to_decimal(profit_loss),
                       'total_revenue': to_decimal(revenue),
                       'ar_ap_amount': to_decimal(ar_ap_amount),
                       'gc_unit_green_fee': to_decimal(gc_unit_green_fee),
                       'gc_unit_buggy_fee': to_decimal(gc_unit_buggy_fee),
                       'checkin_amount': checkin_amount
                       })
        result += played_serializer.data

    summary_result = []
    main_keys = summary.keys()
    sub_keys = summary['booked'].keys()
    for sk in sub_keys:
        item = dict(name=sk)
        for mk in main_keys:
            item.update({mk: summary[mk][sk]})
        total = 0
        for i in item:
            if i == 'name':
                item[i] = item[i].replace('_', ' ').capitalize()
        item.update({'total': total})
        if item['name'] == 'No golfer':
            item.update({'cancelled': '-', 'penalty': '-', 'total': ' '})
        elif item['name'] == 'No round':
            item.update({'total': ' '})
        elif item['name'] == 'Revenues' or item['name'] == 'Gross profits':
            item.update({'total': int(item['booked']) + int(item['played']) + int(item['cancelled'])})
        for k in item:
            try:
                item[k] = to_decimal(item[k])
            except:
                pass
        summary_result.append(item)

    sort_revenue_counter = OrderedDict(
        sorted(revenue_counter.items(), key=lambda t: datetime.datetime.strptime(t[0], '%d-%m-%Y')))

    return Response({'report': sort_revenue_counter, 'summary': summary_result, 'details': result}, status=200)


def get_query_params(request, tee_date=False):
    query_params = {}
    from_date = request.QUERY_PARAMS.get('from_date')
    today = datetime.date.today()
    if from_date:
        from_date = datetime.datetime.strptime(from_date, '%d-%m-%Y')
    else:
        from_date = week_range(today)[0]

    to_date = request.QUERY_PARAMS.get('to_date')
    if to_date:
        to_date = datetime.datetime.strptime(to_date, '%d-%m-%Y')
    else:
        to_date = week_range(today)[1]
    from_date = from_date.replace(hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc)
    to_date = to_date.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc)
    if not tee_date:
        from_date -= datetime.timedelta(hours=7)
        to_date -= datetime.timedelta(hours=7)
        query_params.update({'created__gte': from_date, 'created__lte': to_date})
    else:
        query_params.update({'teetime__date__gte': from_date, 'teetime__date__lte': to_date})

    golfcourse = request.QUERY_PARAMS.get('golfcourse')
    if golfcourse and int(golfcourse) > 0:
        query_params.update({'teetime__golfcourse_id': golfcourse})

    payment_status = request.QUERY_PARAMS.get('payment_status', '')
    if payment_status != '':
        query_params.update({'payment_status': bool(int(payment_status))})
    return query_params


def to_decimal(value):
    return "{:,}".format(int(value))


def get_gc_price(booking_id):
    item = get_or_none(BookedTeeTime, pk=booking_id)
    return get_gc24_booked_teetime_price(item) if item else 0


def get_gc_buggy_price(teetime_id, hole):
    bookedbuggy = get_or_none(BookedBuggy, teetime=teetime_id)
    if bookedbuggy:
        k = "price_standard_{0}".format(str(hole))
        return getattr(bookedbuggy.buggy, k, 0)
    return 0


def get_checkin_amount(tt):
    return (int(tt['unit_price']) * tt['player_checkin_count']) + int(tt['buggy_unit_price']) * tt['buggy_qty'] - int(
        tt.get('voucher_discount_amount', 0)) if tt['status'] in ['PI', 'I'] else 0


def get_card_fee(transaction_ids):
    pay_info = dict()
    for i, status in transaction_ids:
        t = PayTransactionStore.objects.filter(transactionId__contains=i, transactionStatus=1).first()
        if not t:
            continue
        card_fee_percent = 0
        card_fee_bonus = 0
        card_fee_str = '0'
        vendor = t.vendor
        if t.bankCode and '123' in t.bankCode:
            vendor = '123PAY'
            if t.bankCode == '123PCC':
                if status == 'book':
                    card_fee_str = '3.5% + 3000'
                    card_fee_percent = 0.035
                    card_fee_bonus = 3000
                else:
                    card_fee_str = '11000'
                    card_fee_percent = 0
                    card_fee_bonus = 10000
            else:
                if status == 'book':
                    card_fee_str = '1.5% + 1500'
                    card_fee_percent = 0.015
                    card_fee_bonus = 1500
                else:
                    card_fee_str = '3300'
                    card_fee_percent = 0
                    card_fee_bonus = 3000
        key = TRANSACTION_STR.format(i, status)
        pay_info[key] = dict(card_fee_str=card_fee_str,
                             card_fee_percent=card_fee_percent,
                             card_fee_bonus=card_fee_bonus,
                             vendor=vendor,
                             bank_code=t.bankCode,
                             amount=int(t.totalAmount) if t.totalAmount else 0)
    return pay_info


def get_ar_ap_amount(tt, green_fee, buggy_fee):
    if tt['payment_type'] == 'N' and tt['payment_status'] is False:
        amount = int(tt['paid_amount']) - (green_fee + buggy_fee)
    else:
        amount = -(green_fee + buggy_fee)
    return amount


def get_vendor_fee(pay_info, tt):
    tt_id = 't{}'.format(tt['booked_teetime'] if tt.get('booked_teetime') else tt.get('id'))
    if tt.get('booked_teetime') or tt['status'] == 'PC':
        status = 'cancel'
    else:
        status = 'book'
    transaction_id = TRANSACTION_STR.format(tt_id, status)
    total_vendor_fee = 0
    vendor_fee = 0
    entry_fee = 0
    vendor_payable = 0

    paid_amount = tt['paid_amount']
    if tt['status'] == 'I':
        paid_amount -= tt.get('voucher_discount_amount', 0)

    res = dict()
    if pay_info.get(transaction_id):
        paid_amount = charge_amount = pay_info[transaction_id]['amount']
        if tt['status'] in ['PI', 'PC']:
            charge_amount = get_checkin_amount(tt)

        vendor_fee = charge_amount * pay_info[transaction_id]['card_fee_percent'] + \
                     pay_info[transaction_id]['card_fee_bonus']
        entry_fee = vendor_fee * 0.1
        total_vendor_fee = vendor_fee + entry_fee
        if tt['status'] == 'PC':
            vendor_payable = paid_amount - charge_amount - total_vendor_fee
        else:
            vendor_payable = charge_amount - total_vendor_fee
        res.update(pay_info[transaction_id])
    res.update(dict(vendor_fee=vendor_fee,
                    entry_fee=entry_fee,
                    total_vendor_fee=total_vendor_fee,
                    paid_amount=paid_amount,
                    vendor_payable=vendor_payable))
    return res


def get_cancel_teetime(query_params):
    cancel_query = BookedTeeTime_History.objects.filter(payment_status=True, **query_params).order_by(
        'teetime__date')

    played_query = BookedTeeTime.objects.filter(payment_status=True, status='I', **query_params).order_by('teetime__date')

    played_teetime = BookedTeeTimeSerializer(played_query).data
    cancel_teetime = BookedTeeTime_HistorySerializer(cancel_query).data

    partial_cancel_teetime = list(filter(lambda x: x['player_checkin_count'] < x['player_count'], played_teetime))

    for item in partial_cancel_teetime:
        item.update({'status': 'PC'})

    for item in cancel_teetime:
        item.update({'status': 'C'})

    return partial_cancel_teetime + cancel_teetime


def get_key_date(tt, tee_date=False):
    if tee_date:
        return datetime.datetime.strptime(tt['date'], '%Y-%m-%d').date().strftime('%d-%m-%Y')
    return datetime.datetime.fromtimestamp((tt['created'] / 1000)).date().strftime('%d-%m-%Y')
