import datetime, os, calendar
from datetime import timedelta
from django.db.models import Q
from GolfConnect.settings import CURRENT_ENV
from api.noticeMana.tasks import send_notification, get_from_xmpp, xml2json, update_version, get_badge_xmpp
from core.comment.models import Comment
from core.game.models import EventMember, HOST, ACCEPT, Game
from core.golfcourse.models import GolfCourseEvent, GolfCourse
from core.like.models import Like
from core.notice.models import Notice
from core.teetime.models import Deal, DealEffective_TimeRange, BookingTime, GC24DiscountOnline, GCKeyPrice, DealEffective_TeeTime
from core.teetime.models import TeeTime, GuestType, TeeTimePrice, CrawlTeeTime, PaymentMethodSetting
from core.user.models import UserProfile, GroupChat, UserGroupChat, User, UserPrivacy
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.rest.sendemail import send_email
from .serializers import NoticeSerializer, PaginatedNotificationSerializer, PushMessageSerializer, \
    PushEventMessageSerializer, CrawlTeetimeSerializer, PushEventMessagev2Serializer
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, SETTINGS_PATH, ADMIN_EMAIL_RECIPIENT, SYSADMIN_EMAIL
# from core.invitation.models import Invitation, InvitedPeople
from api.inviteMana.serializers import InvitedPeopleSerialier
from api.golfcourseeventMana.serializers import GolfCourseEventPriceInfoSerializer, GolfCourseEventHotelInfoSerializer
import requests

from celery import task
# invitation_ctype = ContentType.objects.get_for_model(Invitation)
event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
LIST_GOLFCOURSE_CRAWL = {
    27: 155,
    48: 1077
}
CURRENCY_PATH = os.path.join(SETTINGS_PATH,'media/currency.xml')
class NoticeViewSet(viewsets.ReadOnlyModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        """ filter only notifications of current user """
        type = request.GET.get('type', '')
        if not type:
            return Response([], status=200)
        date = datetime.datetime.today().date()
        query = []
        if type in ['I', 'IN']:
            query = Notice.objects.filter(to_user=request.user, notice_type=type)
        elif type == 'F':
            query = Notice.objects.filter(to_user=request.user, notice_type__contains=type)
        elif type == 'ALL':
            query = Notice.objects.order_by('-date_create').filter(to_user=request.user, notice_type__in=['I', 'G', 'FR'])
        notifications = []
        for x in query:
            try:
                if x.content_type_id == event_ctype.id and x.related_object and x.related_object.date_start < date:
                    continue
            except Exception:
                continue
            notifications.append(x)

        unshow_count = len(list(filter(lambda x: x.is_show is False, notifications)))
        unread_count = len(list(filter(lambda x: x.is_read is False, notifications)))
        # make pagination
        item = request.GET.get('item', '')
        if not item:
            item = len(notifications)
            if item == 0:
                item = item + 1
        paginator = Paginator(notifications, item)
        page = request.QUERY_PARAMS.get('page')
        try:
            notifs = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            notifs = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999),
            # deliver last page of results.
            notifs = paginator.page(paginator.num_pages)
        serializer = PaginatedNotificationSerializer(instance=notifs)

        # update unread notifications to serialize data
        unread = {'unread_count': unread_count, 'unshow_count': unshow_count}
        serializer.data.update(unread)
        return Response(serializer.data, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_list_notice(request):
    ids = request.DATA['update_list']
    Notice.objects.filter(id__in=ids).update(is_read=True, is_show=True)
    return Response({'status': '200', 'code': 'OK',
                     'detail': 'Update OK'}, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def delete_list_notice(request):
    ids = request.DATA['delete_list']
    Notice.objects.filter(id__in=ids, to_user=request.user).delete()
    return Response({'status': '200', 'detail': 'OK'}, status=200)


DATE = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


def double_week_range(date, first_date):
    """Find the first/last day of the week for the given day.
    Assuming weeks start on Sunday and end on Saturday.

    Returns a tuple of ``(start_date, end_date)``.

    """
    # isocalendar calculates the year, week of the year, and day of the week.
    # dow is Mon = 1, Sat = 6, Sun = 7

    year, week, dow = date.isocalendar()
    start_date = date
    # Find the first day of the week.
    if not first_date:
        delta = 13
        if dow == 1:
            # Since we want to start with Monday, let's test for that condition.
            start_date = date
        else:
            # Otherwise, subtract `dow` number days to get the first day
            start_date = date - timedelta(dow - 1)
    else:
        delta = 14 - dow
    # Now, add 6 for the last day of the week (i.e., count up to Saturday)
    end_date = start_date + timedelta(delta)
    return start_date, end_date

def add_months(sourcedate,months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12 )
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return datetime.date(year,month,day)

def calendar_serializer(invite, user_id, user_type):
    date = invite.date_start
    time = invite.time
    if time:
        time = time.strftime('%H:%M')
        temp_time = invite.time
    else:
        temp_time = datetime.time(0, 0, 0)
    partners = EventMember.objects.filter(event=invite).exclude(status=HOST).exclude(customer__isnull=False)
    partners_seri = InvitedPeopleSerialier(partners)
    # if invite.object_id:
    #     comment_count = Comment.objects.filter(content_type=invite.content_type, object_id=invite.object_id).count()
    # else:
    #     comment_count = Comment.objects.filter(content_type=invitation_ctype, object_id=invite.id).count()
    comment_count = Comment.objects.filter(content_type=event_ctype, object_id=invite.id).count()
    # cmt_serializer = CommentSerializer(comments)
    user_profile = UserProfile.objects.only('display_name', 'profile_picture').get(user_id=invite.user_id)
    # if invite.object_id:
    #     object_id = invite.object_id
    # else:
    object_id = invite.id

    # Get like info
    like_count = Like.objects.filter(content_type=event_ctype, object_id=invite.id).aggregate(Sum('count'))[
        'count__sum']
    if Like.objects.filter(content_type=event_ctype, object_id=invite.id, user_id=user_id).exists():
        is_liked = True
    else:
        is_liked = False
    if not like_count:
        like_count = 0
    is_scored = False
    game_id = None
    try:
        game = Game.objects.only('id').get(event_member__user_id=user_id, event_member__event=invite)
        is_scored = True
        game_id = game.id
    except Exception:
        pass
    # try:
    #     badge_notify = UserBadge.objects.filter(event=invite, user_id=user_id)[0].count
    # except Exception:
    #     badge_notify = 0
    gc_price_info = invite.event_price_info.all()
    gc_price_info_seri = GolfCourseEventPriceInfoSerializer(gc_price_info)
    hotel_info = GolfCourseEventHotelInfoSerializer(invite.event_hotel_info.all())
    invitation = {
        'id': invite.id,
        'event_type': invite.event_type,
        'start': date,
        'time': time,
        'pod': invite.pod,
        'title': invite.golfcourse.name,
        'user_type': user_type,
        'type': 'Event',
        'week_day': date.strftime('%A'),
        'month': date.strftime('%b'),
        'day': date.strftime('%d'),
        'year': date.strftime('%Y'),
        'week': int(date.strftime('%W')) + 1,
        'from_user': str(user_profile.display_name),
        'gender': user_profile.gender,
        'email': str(invite.user.username),
        'same_day': False,
        'partners': partners_seri.data,
        'num_join_partner': invite.event_member.filter(status=ACCEPT, customer__isnull=True).count(),
        'num_partner': len(partners_seri.data),
        'pic': user_profile.profile_picture,
        'from_user_id': invite.user.id,
        'object_id': object_id,
        'description': invite.description,
        'from_hdcp': invite.from_hdcp,
        'to_hdcp': invite.to_hdcp,
        'comment_count': comment_count,
        'temp_time': temp_time,
        'like_count': like_count,
        'is_liked': is_liked,
        'is_scored': is_scored,
        'game_id': game_id,
        'date_start': invite.date_start,
        'date_end': invite.date_end,
        'name': user_profile.display_name,
        # 'badge_notify': badge_notify,
        'semi_null': 0 if invite.banner else 1,
        'score_type': invite.score_type,
        'banner': invite.banner,
        'price_range': invite.price_range,
        'event_price_info': gc_price_info_seri.data,
        'hotel_info': hotel_info.data,
        'discount': invite.discount,
        'payment_discount_value_now': invite.payment_discount_value_now,
        'payment_discount_value_later': invite.payment_discount_value_later
        # 'comment':cmt_serializer.data
    }
    try:
        gc_event = invite
        location = gc_event.location
        if not location:
            location = gc_event.golfcourse.name
        invitation.update({
            'pass_code': gc_event.pass_code,
            'end': gc_event.date_end,
            'golfcourse': gc_event.golfcourse_id,
            'golfcourse_name': location,
            'is_publish': gc_event.is_publish,
            'allow_stay': gc_event.allow_stay,
            'content_type': 'Event',
            'event_name': gc_event.name
        })
    except Exception:
        pass
    return invitation


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_calendar(request):
    # type = request.GET.get('type', None)
    today = datetime.date.today()
    user = request.user
    date = request.GET.get('date', '')
    month = request.GET.get('month', '')

    status = request.GET.get('status', 'A')
    sort_type = request.GET.get('sort', 'DSC')

    if sort_type == 'ASC':
        sort_type = 'event__date_start'
        sort = False
    else:
        sort_type = '-event__date_start'
        sort = True

    # ctype = ContentType.objects.get_for_model(user)
    Like.objects.filter(user=user)
    unread = 0
    first_today = today.replace(day=1)
    # set argument for filter condition
    if month:
        #month = int(month)
        #year = int(request.GET.get('year', today.year))
        #year = today.year
        #to_month = int(request.GET.get('to_month', month))
        #to_year = year
        #delta = to_month - month
        #if delta < 0:
        #    to_year += 1

        #from_date = datetime.date(year, month, 1)
        #to_date = datetime.date(to_year, to_month, 1) + datetime.timedelta(days=30)
        from_date = first_today - datetime.timedelta(days=1)
        from_date = from_date.replace(day=1)
        to_date = add_months(first_today,2)

        invitations = GolfCourseEvent.objects.filter(user=user, date_start__gte=from_date, date_start__lt=to_date).exclude(event_type='GE', date_end__lt=(today - datetime.timedelta(days=14)))
        invited_people = EventMember.objects.filter(user=user,
                                                    event__date_start__gte=from_date,
                                                    event__date_start__lt=to_date).exclude(status=HOST).exclude(event__event_type='GE', event__date_end__lt=(today - datetime.timedelta(days=14))).order_by(
            sort_type)
    elif date:

        if date == 'today':
            date = datetime.date.today()
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        invitations = GolfCourseEvent.objects.filter(user=user, date_start__gte=date).exclude(event_type='GE', date_end__lt=(today - datetime.timedelta(days=14)))
        invited_people = EventMember.objects.filter(user=user, event__date_start__gte=date).exclude(
            status=HOST).exclude(event__event_type='GE', event__date_end__lt=(today - datetime.timedelta(days=14))).order_by(sort_type)
    else:
        invitations = GolfCourseEvent.objects.filter(user=user).exclude(event_type='GE', date_end__lt=(today - datetime.timedelta(days=14)))
        invited_people = EventMember.objects.filter(user=user).exclude(status=HOST).exclude(event__event_type='GE', event__date_end__lt=(today - datetime.timedelta(days=14))).order_by(sort_type)
    # book_teetimes = BookedTeeTime.objects.filter(user=user)
    # partners = BookedPartner.objects.filter(user=user, status='A')


    invitation = []
    object_ids = []
    #################### Get invitation #################################
    for invite in invitations:
        (count, uread) = get_from_xmpp(request.user.username, invite.id)
        invitation_seri = calendar_serializer(invite, request.user.id, 'Owner')
        invitation_seri.update({'comment_count': count, 'badge_notify': uread, 'is_join': True})
        invitation.append(invitation_seri)
        object_ids.append(invitation_seri['object_id'])

    #################### Get invited #################################
    for person in invited_people:
        invitation_seri = calendar_serializer(person.event, request.user.id, 'Guess')
        (count, uread) = get_from_xmpp(request.user.username, person.event.id)
        invitation_seri.update({'comment_count': count, 'badge_notify': uread, 'is_join': person.is_join})
        invitation.append(invitation_seri)
        object_ids.append(invitation_seri['object_id'])

    #################### Get like invitation #################################
    # event_like = Like.objects.only('object_id').filter(user=user, content_type=event_ctype).exclude(object_id__in=object_ids)
    # for like in event_like:
    #     invite = get_or_none(GolfCourseEvent, id=like.object_id)
    #     if invite:
    #         invitation_seri = calendar_serializer(invite, golfcourse_names, 'LikeUser')
    #         invitation.append(invitation_seri)
    #         object_ids.append(invitation_seri['object_id'])
    previous_date = ''
    pinned_top = []
    remain_data = []
    for i in invitation:
        date = i['start']
        if previous_date == date:
            i['same_day'] = True
        previous_date = date
        if i['semi_null'] == 0:
            del i['semi_null']
            pinned_top.append(i)
        else:
            del i['semi_null']
            remain_data.append(i)

    pinned_top.sort(key=lambda x: (x['start'], x['temp_time']), reverse=sort)
    remain_data.sort(key=lambda x: (x['start'], x['temp_time']), reverse=sort)
    invitation = pinned_top + remain_data
    date = datetime.datetime.today().date()
    notifications = Notice.objects.filter(to_user=request.user, notice_type__in=['I', 'G', 'FR'])
    notifications = list(
        filter(lambda x: (x.content_type == event_ctype and x.related_object and x.related_object.date_start >= date) or (x.content_type != event_ctype),
               notifications))
    unread = len(notifications)
    #previous_date = ''
    #for i in invitation:
    #    date = i['start']
    #    if previous_date == date:
    #        i['same_day'] = True
    #    previous_date = date

    data = {
        'book_events': [],
        'invite_events': invitation,
        'unread': unread
    }
    return Response(data, status=200)


@api_view(['POST'])
def send_push_notification(request):
    serializer = PushMessageSerializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)

    data = serializer.data
    send_notification(user_ids=[data['user']], message=data['message'],
                      translate_message=data.get('translate_message', None),
                      badge=data.get('badge', 0))
    return Response({'status': 200, 'detail': 'ok'}, status=200)

@api_view(['POST'])
def send_push_event_notification(request):
    serializer = PushEventMessageSerializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    data = request.DATA

    filter_condition1 = {
        'event_id': data['event_id'],
        'is_join': True
    }
    filter_condition2 = {
        'event_id': data['event_id'],
        'status': HOST
    }
    join_user_ids = EventMember.objects.filter(Q(**filter_condition1) | Q(**filter_condition2)).values_list('user_id',
                                                                                                    flat=True)
    push_user_ids = list(set(join_user_ids).intersection(data['user_id']))
    print(push_user_ids)
    send_notification(user_ids=push_user_ids, message=data['message'],
                      translate_message=data.get('translate_message', None),
                      badge=data.get('badge', 0), event_id=data['event_id'])
    return Response({'status': 200, 'detail': 'ok'}, status=200)

@api_view(['POST'])
def send_push_event_notification_v2(request):
    print (request.DATA)
    serializer = PushEventMessagev2Serializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    data = request.DATA
    display_name = User.objects.get(pk=data['from_user']).user_profile.display_name or "User"
    blocked_by = UserPrivacy.objects.filter(target_id=data['from_user'],action='D').values_list('user_id',flat=True)
    if not 'group' in data['event_id']:
        filter_condition1 = {
        'event_id': data['event_id'],
        'is_join': True
        }
        filter_condition2 = {
            'event_id': data['event_id'],
            'status': HOST
        }
        join_user_ids = EventMember.objects.filter(Q(**filter_condition1) | Q(**filter_condition2)).values_list('user_id',
                                                                                                        flat=True)
        online_user = data.get('online_user',[])
        push_user_ids = [x for x in join_user_ids if str(x) not in online_user and x not in list(blocked_by)]
        message = "Have a new comment from {}".format(display_name)
        trans = {
            'alert_vi': message,
            'alert_en': message
        }
        print (push_user_ids)
        for us in push_user_ids:
            badge = get_badge_xmpp(str(us))
            send_notification(user_ids=[us], message=message,
                          translate_message=trans,
                          badge= badge or 0, event_id=int(data['event_id']))
    else:
        join_user_ids = UserGroupChat.objects.filter(groupchat__group_id=data['event_id']).values_list('user_id',flat=True)
        online_user = data.get('online_user',[])
        push_user_ids = [x for x in join_user_ids if str(x) not in online_user and x not in list(blocked_by)]
        print (push_user_ids)
        message = "Have a new message from {}".format(display_name)
        trans = {
            'alert_vi': message,
            'alert_en': message
        }
        for us in push_user_ids:
            badge = get_badge_xmpp(str(us))
            send_notification(user_ids=[us], message=message,
                          translate_message=trans,
                          badge=badge or 0, group_id=data['event_id'])
    return Response({'status': '200','detail': 'OK'}, status=200)

def week_wed(date):
    year, week, dow = date.isocalendar()
    if dow == 7:
        start_date = date
        dow = 0
    if dow < 3:
        date = date - timedelta(3)
        return week_wed(date)
    else:
        start_date = date - timedelta(dow)
    end_date = start_date + timedelta(3)
    return end_date

def get_crawl_data_golfscape(golfcourse_id, day):
    headers = {
        'origin': 'https://course.golfscape.com',
        'accept-encoding': 'gzip, deflate, br',
        'x-requested-with': 'XMLHttpRequest',
        'accept-language': 'vi,en-US;q=0.8,en;q=0.6',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.63 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'accept': '*/*',
        'referer': 'https://course.golfscape.com/a0ed23/ho-chi-minh-city/vietnam-golf-country-club?v=vietnam-golf-country-club&n=2&id=bc241764-2618-1361-247b-cd333b363db1&s=http://vietnamgolfcc.com&a=1',
        'authority': 'course.golfscape.com',
        'cookie': '__cfduid=d42696eb07983c4298f84b9d7243579ed1464434309',
    }
    date = datetime.date.today() + timedelta(days=day)
    date = date.strftime('%Y-%m-%d')
    data = "data=%7B%22property_id%22%3A%22{0}%22%2C%22dateandtime%22%3A%22{1}%22%2C%22players%22%3A2%2C%22currency%22%3A%22VND%22%7D".format(golfcourse_id, date)

    r = requests.post('https://course.golfscape.com/load-teetime', data=data, headers=headers)
    try:
        res = r.json()
    except:
        send_email("[CRAWL] Cannot parse data from Golfscape", "This is an automatic email. CRAWL method and url changed or Wrong on server side of Golfscape",
                   SYSADMIN_EMAIL)
        return None
    finally:
        return res

#@task(name="get_crawl_data_golfcourse")
def get_crawl_data_golfcourse(list_golfcouse):
    day_crawl = 14
    message_template = '[<b>{golfcourse}</b>] Insert teetime on <b>{date}</b> at <b>{time}</b>'
    message = []
    for k,v in list_golfcouse.items():
        golfcourse_id = k
        golfscape_id = v
        for day in range(0,day_crawl):
            res = get_crawl_data_golfscape(golfscape_id, day)
            if res is None:
                return
            date = datetime.date.today() + timedelta(days=day)
            golfcourse = GolfCourse.objects.get(id=golfcourse_id)
            gtype = GuestType.objects.get(name='G')
            times = []
            ###Tuan Ly: Key price, online_discount and cash_discount to teetime after crawl
            base_discount_setup = Deal.objects.filter(golfcourse=golfcourse_id, is_base=True, active=True)
            base_discount = {'sun': 0, 'mon': 0, 'tue': 0, 'wed': 0, 'thu': 0, 'fri': 0, 'sat': 0}
            if base_discount_setup:
                bookingtime = BookingTime.objects.filter(deal=base_discount_setup)
                if bookingtime:
                    dealeffective_timerange = DealEffective_TimeRange.objects.filter(bookingtime=bookingtime[0])
                    if dealeffective_timerange:
                        for d in dealeffective_timerange:
                            base_discount[d.date.strftime("%a").lower()] = d.discount
            base_online_discount = 0
            base_online_discount_setup = GC24DiscountOnline.objects.filter(golfcourse=golfcourse_id).order_by('-created')
            if base_online_discount_setup.exists() and base_online_discount_setup:
                base_online_discount = base_online_discount_setup[0].discount
            key_price = GCKeyPrice.objects.filter(golfcourse=golfcourse_id).order_by('-created')
            key = "{0}_price"
            ###
            for item in res:
                for t in item.get('available_teetimes', []):
                    d = datetime.datetime.strptime(t['dateandtime'], '%Y-%m-%d %H:%M:%S')
                    times.append(d.time())
                    price = t['greensfee']
                    in_range_date = week_wed(datetime.date.today())
                    if d.date() <= (in_range_date + timedelta(days=11)):
                        obj, created = TeeTime.objects.get_or_create(golfcourse=golfcourse, time=d.time(), date=d.date(), available=True)
                    else:
                        continue
                    #### Check this teetime in deal yet
                    deal_teetime_temp = DealEffective_TeeTime.objects.filter(teetime=obj.id,
                                                                             bookingtime__deal__active= True,
                                                                             bookingtime__deal__is_base= False)
                    
                    deal_teetime_temp.exclude(bookingtime__deal__effective_date= obj.date,
                                              bookingtime__deal__effective_time__gte= obj.time)
                    deal_teetime_temp.exclude(bookingtime__deal__expire_date= obj.date,
                                              bookingtime__deal__expire_time__gte= obj.time)
                    deal_teetime_temp.exclude(bookingtime__deal__expire_date__lt= obj.date)

                    if deal_teetime_temp.exists():
                        continue
                    day = obj.date.strftime("%a").lower()
                    if day in ['sat','sun'] and golfcourse_id == 27:
                        obj.min_player = 3
                    payment_method = PaymentMethodSetting.objects.filter(golfcourse_id=golfcourse_id,date=day).order_by('-created').first()
                    if payment_method:
                        obj.allow_paygc = payment_method.allow_paygc
                        obj.allow_payonline = payment_method.allow_payonline
                    else:
                        obj.allow_paygc = True
                        obj.allow_payonline = False
                    obj.save()
                    online_discount = base_discount[day]
                    cash_discount = base_online_discount
                    if key_price.exists():
                        price = getattr(key_price[0], key.format(day))
                    if created:
                        TeeTimePrice.objects.create(teetime=obj, guest_type=gtype, hole=18, price=price,
                                                    online_discount=online_discount, cash_discount=cash_discount,
                                                    is_publish=True, gifts="", caddy=True)
                        m = message_template.format(golfcourse=golfcourse.name,date=obj.date,time=obj.time)
                        message.append(m)
                    crawl_teetime = CrawlTeeTime.objects.filter(golfcourse=golfcourse, date=d.date(), time=d.time()).first()
                    price = float(price) * (100 - online_discount - cash_discount)/100
                    if t['greensfee'] < price:
                        if not crawl_teetime:
                            CrawlTeeTime.objects.create(golfcourse=golfcourse, date=d.date(), time=d.time(),
                                                        price=t['greensfee'], higher_price=price)
                        else:
                            crawl_teetime.price = t['greensfee']
                            crawl_teetime.higher_price = price
                            crawl_teetime.is_sent = False
                            crawl_teetime.save()
                    else:
                        if crawl_teetime:
                            crawl_teetime.delete()
            TeeTime.objects.filter(golfcourse=golfcourse, date=date, is_booked=False, is_request=False, is_hold=False, available=True).exclude(
                time__in=times).delete()
    if message:
        message = '<br>'.join(message)
        if CURRENT_ENV == 'prod':
            email_title = "[PROD] New Crawl Teetime"
        else:
            email_title = "[DEV] New Crawl Teetime"
        send_email(email_title, message, SYSADMIN_EMAIL)

@api_view(['POST'])
def crawl_teetime(request):
    serializer = CrawlTeetimeSerializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    #get_crawl_data_golfcourse.delay(LIST_GOLFCOURSE_CRAWL)
    get_crawl_data_golfcourse(LIST_GOLFCOURSE_CRAWL)
    return Response({'status': 200, 'detail': 'ok'}, status=200)

@api_view(['POST'])
def send_email_lower_price(request):
    serializer = CrawlTeetimeSerializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    message_template = '[<b>{golfcourse}</b>] Teetime on <b>{date}</b> at <b>{time}</b> has price <b>{price}</b> lower than gc24 price <b>{higher_price}</b>'
    message = []
    teetimes = CrawlTeeTime.objects.filter(is_sent=False)
    for tt in teetimes:
        m = message_template.format(golfcourse=tt.golfcourse.name, date=tt.date, time=tt.time, price=int(tt.price),
                                    higher_price=int(tt.higher_price))
        message.append(m)
    if not message:
        return Response({'status': 200, 'detail': 'ok'}, status=200)
    message = '<br>'.join(message)

    if ADMIN_EMAIL_RECIPIENT:
        email_title = '[{0}] Crawl Higher Price Alert'.format(CURRENT_ENV.upper())
        send_email(email_title, message, ADMIN_EMAIL_RECIPIENT)

    for tt in teetimes:
        tt.is_sent = True
        tt.save()
    return Response({'status': 200, 'detail': 'ok'}, status=200)

@api_view(['POST'])
def crawl_currency_vietcombank(request):
    serializer = CrawlTeetimeSerializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    r = requests.get('http://www.vietcombank.com.vn/ExchangeRates/ExrateXML.aspx')
    with open(CURRENCY_PATH, 'wb') as outfile:
        outfile.write(r.content)
    return Response({'status': 200, 'detail': 'ok'}, status=200)

@api_view(['GET'])
def get_currency_vietcombank(request):
    with open(CURRENCY_PATH) as infile:
        input = infile.read()
        out = xml2json(input, '', '')
        return Response({'status': 200, 'detail': out['ExrateList']['Exrate']}, status=200)
