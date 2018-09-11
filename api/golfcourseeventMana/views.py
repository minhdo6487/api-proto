import datetime
import calendar
import json

import os.path
import re
import redis
import requests
from api.commentMana.serializers import CommentSerializer
from api.inviteMana.views import DOW
from bs4 import BeautifulSoup
from core.customer.models import Customer
from core.gallery.models import Gallery
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.models import Sum
from django.utils import timezone as django_timezone
from pytz import timezone, country_timezones
from rest_framework import mixins
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.utils import encoders
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

# from core.invitation.models import Invitation, InvitedPeople
from core.notice.models import Notice
from core.realtime.models import TimeStamp
from utils.django.models import get_or_none
from core.golfcourse.models import GolfCourseEvent, GolfCourseStaff, GroupOfEvent, EventPrize, TeeType, EventBlock, \
    Hole
from core.game.models import EventMember, Game, Score
from api.golfcourseeventMana.serializers import GolfCourseEventSerializer, PublicGolfCourseEventSerializer, \
    GroupOfEventSerializer, EventPrizeSerializer, AdvertiseEventSerializer, RegisterEventSerializer, \
    GolfCourseEventScheduleSerializer, GolfCourseEventMoreInfoSerializer, GolfCourseEventBannerSerializer, GolfCourseEventPriceInfoSerializer, GolfCourseEventHotelInfoSerializer
from api.gameMana.serializers import EventMemberSerializer, GameSerializer
from api.bookingMana.views import handle_gc_event_booking
from utils.rest.permissions import IsGolfStaff
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB
# from GolfConnect.celery import app
from api.noticeMana.tasks import send_email, get_from_xmpp
from GolfConnect.settings import CURRENT_ENV
from core.comment.models import Comment
from django.db.models import Q
redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

HDCP_SYSTEM = {'net': 'hdc_net',
               'system36': 'hdc_36', 'hdcus': 'hdc_us', 'callaway': 'hdc_callaway', 'stable_ford': 'hdc_stable_ford',
               'peoria': 'hdc_peoria', 'db_peoria': 'hdc_peoria'}

TECH_PRZIE_NAME = ['longest drive for man', 'longest drive for ladies',
                   'nearest to pin 1', 'nearest to pin 2', 'hole in one']
# 'best gross', '1st a', '2nd a', '3rd a', '1st b', '2nd b',
#                    '3rd b', '1st c', '2nd c', '3rd c',
GC_EVENT = 'GE'
PLAYER_EVENT = 'PE'
SCRAMBLE = 'scramble'
TPL_STR = CURRENT_ENV + '_user'


def ranking(event, date, group_by=None, cal_handicap=False):
    results = {}
    serializers = GolfCourseEventSerializer(event)
    results.update(serializers.data)
    # results['group'] = list(sorted(results['group'], key=lambda x: x.from_index))
    channel = 'event-' + str(serializers.data['id']) + '-' + str(date)
    try:
        ts, created = TimeStamp.objects.get_or_create(channel=channel)
        results.update({'ts': ts.time.timestamp()})
    except Exception:
        pass
    members = EventMember.objects.filter(event=event)
    serializers = EventMemberSerializer(members)
    register_members = list(filter(lambda x: x['is_active'] is True, serializers.data))
    results.update({'members': serializers.data,
                    'register_members': register_members})
    i = 0
    cal = HDCP_SYSTEM[event.calculation]
    tee_type_checker = {}
    hole_checker = {}
    subgolcourse_id = None
    pars = []
    for member in members:
        games = member.game.filter(date_play=date)[:1]
        if games:
            serializers = GameSerializer(games[0])
            if serializers.data['score']:
                tee_type_id = serializers.data['score'][0]['tee_type']
                if tee_type_id not in tee_type_checker:
                    tt = TeeType.objects.only('id', 'subgolfcourse_id', 'color').get(id=tee_type_id)
                    tee_type = {
                        'color': tt.color,
                        'id': tt.id,
                        'subgolfcourse': tt.subgolfcourse_id
                    }


                    if not subgolcourse_id:
                        subgolcourse_id = tt.subgolfcourse_id
                        results.update({'subgolfcourse': subgolcourse_id})
                    if tt.subgolfcourse_id not in hole_checker:
                        hole_ids = Hole.objects.filter(subgolfcourse_id=tt.subgolfcourse_id)\
                            .values_list('id', 'par', 'holeNumber', 'subgolfcourse_id')\
                            .order_by('holeNumber')
                        hole_checker.update({tt.subgolfcourse_id: list(hole_ids)})
                    tee_type_checker.update({tee_type_id: tee_type})
                j = 0
                temp_score = serializers.data['score'].copy()
                maxj = len(temp_score)

                current_game_subgolfcourse_id = tee_type_checker[tee_type_id]['subgolfcourse']

                for k, h in enumerate(hole_checker[current_game_subgolfcourse_id]):
                    if h[0] != temp_score[j]['hole']:
                        serializers.data['score'].insert(k, {
                            'hole': h[0],
                            'holeNumber': h[2],
                            'tee_type': tt.id,
                            'stroke': 0,
                            'game': serializers.data['id'],
                            'par': h[1]
                        })
                    else:
                        serializers.data['score'][k].update({
                            'par': h[1],
                            'holeNumber': h[2],
                        })
                        if j < maxj - 1:
                            j += 1
            if event.calculation == 'system36':
                results['members'][i]['handicap'] = serializers.data['handicap_36']

            results['members'][i].update({'game': serializers.data})
        i += 1
    if event.rule == SCRAMBLE:
        group_member = []

        for g in results['group']:
            for m in results['members']:
                if m['group'] == g['id'] and 'game' in m and m['game']['score']:
                    tee_type = tee_type_checker[m['game']['score'][0]['tee_type']]
                    temp = {
                        'game': m['game'],
                        'id': g['id'],
                        'handicap': g['from_index'],
                        'group_name': g['name'],
                        'tee_type': tee_type['id'],
                        'color': tee_type['color'],
                        'subgolfcourse': tee_type['subgolfcourse'],
                        'net': m['game'][cal],
                        'gross': m['game']['gross_score'],
                        'player_id': m['id'],
                    }
                    group_member.append(temp)
        results.update({'group_member': group_member})
    # for g in results['group']:
    # if g['name'] == 'lady':
    # lady_group_id = g['id']
    for m in results['members']:
        front_nine = 0
        back_nine = 0
        front_par = 0
        back_par = 0
        # if lady_group_id:
        # if m['group_']
        m.update({'thru': 0, 'gross': 0, 'net': '', 'front_nine': 0, 'back_nine': 0,
                  'hole_18': 0, 'rank_change': 0})
        if 'game' in m and m['game']['score']:
            for j in range(0, len(m['game']['score'])):
                try:
                    if j < 9:
                        front_nine += m['game']['score'][j]['stroke']
                        front_par += m['game']['score'][j]['par']
                    else:
                        back_nine += m['game']['score'][j]['stroke']
                        back_par += m['game']['score'][j]['par']
                except Exception:
                    pass
            if m['game']['is_finish'] == True:
                thru = 'F'
                left_thru = 0
            else:
                thru = len(list(filter(lambda x: x['stroke'] != 'x' and x['stroke'] > 0, m['game']['score'])))
                left_thru = 18 - thru
            if m['game']['is_quit']:
                thru = 'WD'
            m.update({'thru': thru, 'left_thru': left_thru, 'gross': m['game']['gross_score'],
                      'net': m['game'][cal], 'front_nine': front_nine, 'back_nine': back_nine,
                      'front_par': front_par, 'back_par': back_par}
                     )
            if cal_handicap:
                handicap = m['handicap'] if m['handicap'] else 0
                m['net'] = m['gross'] - handicap

    member_has_game = list(
        filter(lambda x: 'game' in x and x['game'] and x['game']['score'], results['members']))
    member_no_game = list(
        filter(lambda x: not ('game' in x and x['game'] and x['game']['score']), results['members']))
    if event.event_type == 'GE':
        if event.calculation == 'system36':
            sort_member = sorted(member_has_game,
                                 key=lambda m: ((1 if m['thru'] == 'WD' else 0),m['net'], m['left_thru']
                                                , m['handicap'], m['back_nine'], m['front_nine'],
                                                tuple(x['stroke'] for x in reversed(m['game']['score']))))
        else:
            sort_member = sorted(member_has_game,
                                 key=lambda m: ((1 if m['thru'] == 'WD' else 0),m['net'], m['left_thru'], m['back_nine'], m['front_nine'],
                                                tuple(x['stroke'] for x in reversed(m['game']['score']))))
    else:
        sort_member = sorted(member_has_game, key=lambda m: ((1 if m['thru'] == 'WD' else 0),m['net'], m['left_thru']))
    # Ranking
    if sort_member:
        rank = 1
        rank_temp = 1
        if sort_member[0]['rank']:
            sort_member[0]['rank_change'] = sort_member[0]['rank'] - rank
        sort_member[0]['rank'] = rank
        EventMember.objects.filter(id=sort_member[0]['id']).update(rank=rank)
        for i in range(1, len(sort_member)):
            rank_temp += 1
            if sort_member[i]['thru'] != sort_member[i - 1]['thru']:
                rank = rank_temp
            elif sort_member[i]['net'] > sort_member[i - 1]['net']:
                rank = rank_temp
            else:
                if event.event_type == 'GE':
                    if sort_member[i]['handicap'] and sort_member[i - 1]['handicap'] and sort_member[i]['handicap'] > \
                            sort_member[i - 1]['handicap']:
                        rank = rank_temp
                    elif sort_member[i]['back_nine'] > sort_member[i - 1]['back_nine']:
                        rank = rank_temp
                        sort_member[i].update({'count_back': 'Back-9: ' + str(sort_member[i]['back_nine'])})
                        sort_member[i - 1].update({'count_back': 'Back-9: ' + str(sort_member[i - 1]['back_nine'])})
                    elif sort_member[i]['front_nine'] > sort_member[i - 1]['front_nine']:
                        rank = rank_temp
                        sort_member[i].update({'count_back': 'Front-9: ' + str(sort_member[i]['front_nine'])})
                        sort_member[i - 1].update({'count_back': 'Front-9: ' + str(sort_member[i - 1]['front_nine'])})
                    else:
                        for j, e in reversed(list(enumerate(sort_member[i]['game']['score']))):
                            if e['stroke'] > sort_member[i - 1]['game']['score'][j]['stroke']:
                                sort_member[i].update({'count_back': 'Hole ' + str(j + 1) + ': ' + str(e['stroke'])})
                                sort_member[i - 1].update({'count_back': 'Hole ' + str(j + 1) + ': ' + str(
                                    sort_member[i - 1]['game']['score'][j]['stroke'])})
                                rank = rank_temp
                                break
            if sort_member[i]['rank']:
                sort_member[i]['rank_change'] = sort_member[i]['rank'] - rank
            sort_member[i]['rank'] = rank
            EventMember.objects.filter(id=sort_member[i]['id']).update(rank=rank)
    results['members'] = sort_member
    if event.rule == SCRAMBLE:
        results['members'] = sort_member + member_no_game
        for g in results['group_member']:
            member = [(m['name'], m['rank'], m['email'], m['front_nine'], m['back_nine'], m['hole_18'],
                       m['thru'], m['rank_change'])
                      for m in results['members'] if
                      m['group'] == g['id']]
            g.update({'members': []})
            for m in member:
                g['members'].append({
                    'name': m[0],
                    'email': m[2],
                })
                if m[1]:
                    g.update({'rank': m[1], 'front_nine': m[3], 'back_nine': m[4],
                              'hole_18': m[5], 'thru': m[6], 'rank_change': m[7]})
        results['group_member'] = sorted(results['group_member'], key=lambda m: (m['rank']))
    elif group_by == 'group':
        group_member = results['group'].copy()
        for g in group_member:
            g.update({'members': []})
            for m in results['members']:
                if g['from_index'] <= m['net'] <= g['to_index']:
                    g['members'].append(m)
        results.update({'group_member': group_member})

    results = json.dumps(results, cls=encoders.JSONEncoder)
    return results

def add_months(sourcedate,months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12 )
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return datetime.date(year,month,day)

class GolfCourseEventViewSet(viewsets.ModelViewSet):
    queryset = GolfCourseEvent.objects.all()
    serializer_class = GolfCourseEventSerializer
    parser_classes = (JSONParser, FormParser,)
    filter_fields = ('golfcourse',)

    @permission_classes((permissions.IsAuthenticated,))
    def create(self, request, *args, **kwargs):
        event_type = request.DATA.get('event_type', 'PE')
        if GC_EVENT == event_type:
            user = get_or_none(GolfCourseStaff, user=request.user)
            if not user:
                return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                                 'detail': 'You do not have permission to peform this action'}, status=401)
            else:
                request.DATA['golfcourse'] = user.golfcourse_id

        request.DATA['user'] = request.user.id
        if 'group' in request.DATA and request.DATA['group']:
            groups = request.DATA['group']
        else:
            groups = []
        if 'date_start' not in request.DATA:
            request.DATA.update({'date_start': str(datetime.date.today())})
        temp = []
        i = 0
        duplicate_group_checker = []
        for g in groups:
            g['name'] = g['name'].lower()
            if g['name'] not in temp:
                temp.append(g['name'])
            else:
                duplicate_group_checker.append(i)
            i += 1
        if duplicate_group_checker:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'Duplicate group', 'duplicate_group': duplicate_group_checker}, status=400)
        # if GolfCourseEvent.objects.filter(name=request.DATA['name'], golfcourse=user.golfcourse,).exists():
        # return Response({'status': '400', 'code': 'E_ALREADY_EXIST',
        # 'detail': 'This item is already existed'}, status=400)
        serializers = self.serializer_class(data=request.DATA)
        if not serializers.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializers.errors}, status=400)
        serializers.save()
        try:
            return Response(serializers.data, status=200)
        except Exception as e:
            print(e)
            return Response({'status': '400', 'code': 'E_ALREADY_EXIST',
                             'detail': 'This item is already existed'}, status=400)

    @permission_classes((permissions.IsAuthenticated,))
    def partial_update(self, request, pk=None):
        if not GolfCourseEvent.objects.filter(id=pk, user=request.user).exists():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        groups = request.DATA.get('group', [])
        i = 0
        duplicate_group_checker = []
        temp = []
        for g in groups:
            g['name'] = g['name'].lower()
            if g['name'] not in temp:
                if 'event' not in g or not g['event']:
                    g['event'] = int(pk)
                temp.append(g['name'])
            else:
                duplicate_group_checker.append(i)
            try:
                group = GroupOfEvent.objects.only('id').get(name=g['name'], event_id=pk)
                g.update({'id': group.id})
            except Exception:
                pass
            i += 1
        if duplicate_group_checker:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'Duplicate group', 'duplicate_group': duplicate_group_checker}, status=400)
        return super().partial_update(request, pk)

    @permission_classes((permissions.IsAuthenticated,))
    def destroy(self, request, pk=None):
        if not GolfCourseEvent.objects.filter(id=pk, user=request.user).exists():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
        return super().destroy(request, pk)

    @permission_classes((permissions.AllowAny,))
    def retrieve(self, request, pk=None):
        if not GolfCourseEvent.objects.filter(id=pk).exists():
            return Response({'detail': 'Not found'}, status=404)
        fields = request.QUERY_PARAMS.get('fields', '')
        fields = set(fields.split(','))
        results = {}
        gc_event = GolfCourseEvent.objects.get(id=pk)
        serializers = GolfCourseEventSerializer(gc_event)
        ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        results.update(serializers.data)
        real_prize = []
        one_prize = []
        if 'member' in fields:
            if 'ranking' in fields:
                date = request.QUERY_PARAMS.get('date', '')
                if not date or date == 'undefined':
                    date = gc_event.date_start
                if gc_event.event_type == 'GE':
                    if 'cal_handicap' in fields:
                        cal_handicap = True
                    else:
                        cal_handicap = False
                    # if gc_event.has_result:
                    # channel = 'event-' + str(gc_event.id) + '-' + str(date)
                    # data = redis_server.get(channel)
                    # if data:
                    #     results = data.decode()
                    # else:
                    #     results = ranking(gc_event, date)
                    results = ranking(gc_event, date, cal_handicap=cal_handicap)
                    results = json.loads(results)
                    if 'group' in fields:
                        group_member = results['group'].copy()
                        sort_member = list(sorted(results['members'], key=lambda x: x['gross']))
                        best_gross_name = sort_member[0]['name']
                        best_gross_group_name = sort_member[0]['group_name']
                        results.update({'best_gross': sort_member[0]})
                        for g in group_member:
                            g.update({'members': []})
                            rank = 1
                            rank_temp = 1
                            for j, m in enumerate(results['members']):
                                # if not m['group']:
                                #     flag = float(g['from_index']) <= float(m['handicap']) <= float(g['to_index'])
                                try:
                                    if (m['group'] and int(m['group']) == int(g['id'])) or (
                                                not m['group'] and float(g['from_index']) <= float(
                                                m['handicap']) <= float(g['to_index'])):
                                        # logging.error(m['name'])
                                        if results['members'][j - 1]:
                                            if results['members'][j]['rank'] != results['members'][j - 1]['rank']:
                                                results['members'][j].update({'rank_temp': rank_temp})
                                                rank = rank_temp
                                            else:
                                                results['members'][j].update({'rank_temp': rank})
                                        else:
                                            results['members'][j].update({'rank_temp': rank})
                                        rank_temp += 1
                                        g['members'].append(results['members'][j])
                                except Exception:
                                    pass
                        results.update({'rank_by_group': group_member})

                        real_prize.append({
                            'player_name': sort_member[0]['name'],
                            'prize_name': 'best gross',
                            'gross': sort_member[0]['gross'],
                            'handicap': sort_member[0]['handicap'],
                            'net': sort_member[0]['net']
                        })
                        one_prize.append({
                            'player_name': sort_member[0]['name'],
                            'prize_name': 'best gross',
                            'gross': sort_member[0]['gross'],
                            'handicap': sort_member[0]['handicap'],
                            'net': sort_member[0]['net']
                        })

                        for group in results['rank_by_group']:
                            for m in group['members']:
                                if m['rank_temp'] == 1:
                                    prize_name = '1st ' + group['name']
                                elif m['rank_temp'] == 2:
                                    prize_name = '2nd ' + group['name']
                                elif m['rank_temp'] == 3:
                                    prize_name = '3rd ' + group['name']
                                else:
                                    break
                                real_prize.append({
                                    'prize_name': prize_name,
                                    'player_name': m['name'],
                                    'gross': m['gross'],
                                    'net': m['net'],
                                    'handicap': m['handicap']
                                })

                        for group in results['rank_by_group']:
                            i = 1
                            for m in group['members']:
                                if i == 1:
                                    if m['name'] == best_gross_name:
                                        i = 1
                                        continue
                                    prize_name = '1st ' + group['name']
                                elif i == 2:
                                    prize_name = '2nd ' + group['name']
                                elif i == 3:
                                    prize_name = '3rd ' + group['name']
                                else:
                                    break
                                i += 1
                                one_prize.append({
                                    'prize_name': prize_name,
                                    'player_name': m['name'],
                                    'gross': m['gross'],
                                    'net': m['net'],
                                    'handicap': m['handicap']
                                })
                        for group in results['rank_by_group']:
                            if group['name'] == best_gross_group_name:
                                for idx, m in enumerate(group['members']):
                                    if m['name'] != best_gross_name:
                                        m['rank_temp'] -= 1
                                    elif m['name'] == best_gross_name:
                                        results.update({'best_gross': m})
                                        best_gross_idx = idx
                                if best_gross_idx >= 0:
                                    del group['members'][best_gross_idx]
                                break
                else:
                    results = ranking(gc_event, date)
                    results = json.loads(results)

            else:
                if gc_event.event_type == 'PE':
                    members = EventMember.objects.filter(event_id=pk, is_join=True)
                elif gc_event.event_type == 'GE':
                    members = EventMember.objects.filter(event_id=pk)
                if 'me' in fields:
                    members = members.filter(game__recorder=request.user)
                serializers = EventMemberSerializer(members)
                results.update({'members': serializers.data})
        if 'image' in fields:
            gallery = Gallery.objects.filter(content_type=ctype, object_id=pk).values_list('picture', flat=True)
            results.update({'gallery': gallery,
                            'location': gc_event.location,
                            'has_result': gc_event.has_result})
            try:
                schedule_seri = GolfCourseEventScheduleSerializer(gc_event.event_schedule.all())
                more_details = GolfCourseEventMoreInfoSerializer(gc_event.event_more_info.all())
                banner_seri = GolfCourseEventBannerSerializer(gc_event.event_banner.all())
                price_info = GolfCourseEventPriceInfoSerializer(gc_event.event_price_info.all())
                hotel_info = GolfCourseEventHotelInfoSerializer(gc_event.event_hotel_info.all())
                results.update({
                    'about': gc_event.advertise_info.about,
                    'about_en': gc_event.advertise_info.about_en,

                    'more_info': gc_event.advertise_info.more_info,
                    'more_info_en': gc_event.advertise_info.more_info_en,
                    'sponsor_html': gc_event.advertise_info.sponsor_html,

                    'detail_banner': gc_event.advertise_info.detail_banner,
                    'schedule': gc_event.advertise_info.schedule_html,
                    'plain_schedule': schedule_seri.data,
                    'more_details': more_details.data,
                    'price': price_info.data,
                    'hotel': hotel_info.data,
                    'description_html': gc_event.advertise_info.description_html,
                    'banners': banner_seri.data
                })
            except Exception:
                pass
        if 'cmt' in fields:
            comments = Comment.objects.filter(content_type=ctype, object_id=gc_event.id)
            cmt_serializer = CommentSerializer(comments)
            results.update({
                'comment': cmt_serializer.data
            })
        if 'prize' in fields:
            prize = EventPrize.objects.filter(event_id=pk)
            serializers = EventPrizeSerializer(prize)
            prize = serializers.data
            results.update({'prize': prize})

            if one_prize:
                results.update({'one_prize': one_prize})
            if real_prize:
                results.update({'real_prize': real_prize})
                if not prize:
                    results.update({'prize': one_prize})

            player_name = []
            for p in results['prize']:
                # check duplicate
                if p['player_name'] not in player_name:
                    p.update({'status': 1})
                    player_name.append(p['player_name'])
                else:
                    p.update({'status': 0})
                if 'members' in results:
                    for m in results['members']:
                        if m['name'] == p['player_name']:
                            p.update({
                                'gross': m['gross'],
                                'handicap': m['handicap'],
                                'net': m['net']
                            })
                            break

            for tech_prize in TECH_PRZIE_NAME:
                has_prize = False
                for p in results['prize']:
                    if p['prize_name'] == tech_prize:
                        has_prize = True
                        break
                if not has_prize:
                    results['prize'].append({
                        'prize_name': tech_prize,
                        'player_name': ""
                    })

        return Response(results, status=200)

    def list(self, request, *args, **kwargs):
        event_type = request.QUERY_PARAMS.get('event_type', '')

        if event_type:
            events = GolfCourseEvent.objects.filter(event_type=event_type, user=request.user)
        else:
            block_event_ids = EventBlock.objects.filter(user=request.user).values_list('event_id', flat=True)
            events = GolfCourseEvent.objects.exclude(id__in=block_event_ids).all()
        events = events.prefetch_related('tee_type',
                                         'user__user_profile',
                                         'golfcourse').order_by('-date_start')

        today = request.QUERY_PARAMS.get('date', '')
        if today == 'today':
            today = datetime.date.today()
            events = events.filter(date_start__lte=today, date_end__gte=today)
        serializers = GolfCourseEventSerializer(events)
        event = EventMember.objects.only('event_id').filter(user=request.user, is_active=True).values_list('event_id',
                                                                                                           flat=True)
        for data in serializers.data:
            if request.user.id == data['user']:
                data.update({'user_type': 'owner'})
            elif data['id'] in event:
                data.update({'user_type': 'invited'})
            else:
                data.update({'user_type': 'guest'})
            del data['user']
        return Response(serializers.data, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_my_event(request):
    event_member = EventMember.objects.select_related('event').filter(user=request.user, event__isnull=False).order_by(
        'event_id').distinct('event_id')
    result = []
    for e in event_member:
        for g in Game.objects.only('id', 'date_play').filter(event_member=e):
            temp = {
                'golfcourse': e.event.golfcourse.name,
                'date_play': g.date_play,
                'event_name': e.event.name,
                'gross': Score.objects.filter(game_id=g.id).aggregate(sum_stroke=Sum('stroke'))['sum_stroke'],
                'sum_putt': Score.objects.filter(game_id=g.id).aggregate(sum_putt=Sum('putt'))['sum_putt'],
                'event_id': e.event_id
            }
            result.append(temp)
    result = sorted(result, key=lambda x: x['date_play'], reverse=True)
    return Response(result, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def join_event(request):
    event_id = request.DATA.get('event', -1)
    event = get_or_none(GolfCourseEvent, id=event_id)
    if not event:
        return Response({'status': 404, 'code': 'E_NOT_FOUND', 'detail': 'event pk does not exist'}, status=404)
    pass_code = request.DATA.get('pass_code', '')
    if not EventMember.objects.filter(user=request.user, event=event,
                                      is_active=True).exists() and event.user != request.user and event.pass_code and event.pass_code != pass_code:
        return Response({'status': 400, 'code': 'E_INVALID_PARAMETER_VALUES', 'detail': 'Pass code mismatch'},
                        status=400)
    # member = get_or_none(EventMember, user=request.user, event=event)
    handicap = request.DATA.get('handicap', None)
    memberID = request.DATA.get('memberID', None)
    clubID = request.DATA.get('clubID', None)
    updated_values = {
        'handicap': handicap,
        'memberID': memberID,
        'clubID': clubID,
        'is_active': True,
        'is_join': True
    }
    member, created = EventMember.objects.update_or_create(user=request.user, event=event, defaults=updated_values)
    serializer = EventMemberSerializer(member)
    return Response({'detail': serializer.data, 'status': 200, 'code': 'OK'}, status=200)


@api_view(['POST'])
@permission_classes((AllowAny,))
def register_event(request):
    # check_pay_discount = {
    #     'N': 5,
    #     'F': 10
    # }
    event_id = request.DATA.get('event', -1)
    event = get_or_none(GolfCourseEvent, id=event_id)

    discount_now = event.payment_discount_value_now
    discount_later = event.payment_discount_value_later
    if not event:
        return Response({'status': 404, 'code': 'E_NOT_FOUND', 'detail': 'event pk does not exist'}, status=404)
    # elif event.payment_discount != request.DATA.get('payment_type') and event.payment_discount != 'A':
    #     detail_allert = 'This golfcourse event only allow payment type: {}'.format(event.payment_discount)
    #     return Response({'detail': detail_allert}, status=404)
    # elif request.DATA.get('discount') != event.payment_discount_value:
    #     return Response({'detail': 'select another discount'}, status=404)

    elif request.DATA.get('payment_type') == 'F' and request.DATA.get('discount') != discount_now:
        return Response({'detail': 'wrong discount check again'}, status=404)
    elif request.DATA.get('payment_type') == 'N' and request.DATA.get('discount') != discount_later:
        return Response({'detail': 'wrong discount check again'}, status=404)


    if event.event_type == 'GE':
        serializer = RegisterEventSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        updated_values = {
            'is_active': True,
            'is_join': True,
            'status': 'A'
        }
        #EventMember.objects.update_or_create(user=request.user, event=event, defaults=updated_values)
        #member, created = EventMember.objects.update_or_create(user=request.user, event=event, defaults=updated_values)
        ### all golf user
        list_cus = []
        #########
        golfer_joined_number = request.DATA.get('golfer_joined_number')
        if not request.user.is_anonymous():
            ### user booked
            member, created = EventMember.objects.get_or_create(user=request.user, event_id=event_id)
            member.is_active = True
            member.is_join = True
            member.status = 'A'
            member.save(update_fields=['is_active', 'is_join', 'status'])

            # list_cus.append(member.customer)
            ### add golfer not userbookeds
            for index_item in range(golfer_joined_number):

                name = request.DATA.get('golfer_joined_detail')[index_item]['name']
                email = request.DATA.get('golfer_joined_detail')[index_item]['email']
                phone = request.DATA.get('golfer_joined_detail')[index_item]['phone']
                if event.event_price_info.all().count() > 0:
                    customer = Customer.objects.create(name=name,
                                                       email=email,
                                                       phone_number=phone)
                    if 'handicap' in request.DATA.get('golfer_joined_detail')[index_item].keys():
                        customer.handicap = request.DATA.get('golfer_joined_detail')[index_item]['handicap']
                    else:
                        customer.handicap = None
                    if 'golfcourse' in serializer.data.keys():
                        # customer.golfcourse_id = int(serializer.data['golfcourse'])
                        customer.golfcourse_id = (serializer.data['golfcourse'])
                    customer.save()
                    member_join = EventMember.objects.create(customer=customer, event_id=event_id)
                    member_join.is_active = True
                    member_join.is_join = True
                    member_join.status = 'A'
                    member_join.save(update_fields=['is_active', 'is_join', 'status'])

                    list_cus.append(customer)
                    # if created:
                    # ctype = ContentType.objects.get_for_model(GolfCourseEvent)
                    # Invitation.objects.create(content_type=ctype, object_id=event.id, user=request.user,
                    #                               golfcourse=event.name,
                    #                               time=event.time, date=event.date_start)
        else:
            for index_item in range(golfer_joined_number):
                if index_item != 0:
                    name = request.DATA.get('golfer_joined_detail')[index_item]['name']
                    email = request.DATA.get('golfer_joined_detail')[index_item]['email']
                    phone = request.DATA.get('golfer_joined_detail')[index_item]['phone']

                    customer = Customer.objects.create(name=name,
                                                       email=email,
                                                       phone_number=phone)
                    if 'handicap' in request.DATA.get('golfer_joined_detail')[index_item].keys():
                        customer.handicap = request.DATA.get('golfer_joined_detail')[index_item]['handicap']
                    if 'golfcourse' in serializer.data.keys():
                        # customer.golfcourse_id = int(serializer.data['golfcourse'])
                        customer.golfcourse_id = (serializer.data['golfcourse'])
                    customer.save()

                    member_join = EventMember.objects.create(customer=customer, event_id=event_id)
                    member_join.is_active = True
                    member_join.is_join = True
                    member_join.status = 'A'
                    member_join.save(update_fields=['is_active', 'is_join', 'status'])
                    # list_cus.append(customer)
                elif index_item == 0:
                    name = request.DATA.get('golfer_joined_detail')[index_item]['name']
                    email = request.DATA.get('golfer_joined_detail')[index_item]['email']
                    phone = request.DATA.get('golfer_joined_detail')[index_item]['phone']

                    customer = Customer.objects.create(name=name,
                                                       email=email,
                                                       phone_number=phone)
                    if 'handicap' in request.DATA.get('golfer_joined_detail')[index_item].keys():
                        customer.handicap = request.DATA.get('golfer_joined_detail')[index_item]['handicap']
                    if 'golfcourse' in serializer.data.keys():
                        # customer.golfcourse_id = int(serializer.data['golfcourse'])
                        customer.golfcourse_id = (serializer.data['golfcourse'])
                    customer.save()

                    member = EventMember.objects.create(customer=customer, event_id=event_id)
                    member.is_active = True
                    member.is_join = True
                    member.status = 'A'
                    member.save(update_fields=['is_active', 'is_join', 'status'])
                list_cus.append(customer)

        if event.event_price_info.all().count() > 0:
            return handle_gc_event_booking(request, member, list_cus)
        """
        minh try comment 2017Jan06
        """
        # detail_html = '<br><br><br><b>Chào bạn,</b><br><br>' + str(
        #     serializer.data['name']) + ' đã đăng kí sự kiện <b>' + str(
        #     event.name) + '</b> với thông tin sau: <br>' + 'Tên: ' + str(
        #     serializer.data['name']) + '<br>' + 'Số điện thoại: ' + str(
        #     serializer.data['phone']) + '<br>' + 'Email: ' + str(serializer.data['email'])
        #
        # detail_htmlen = '<b>Hi,</b><br><br>' + str(
        #     serializer.data['name']) + ' registered the event <b> ' + str(
        #     event.name) + '</b> with following details: <br>' + 'Name: ' + str(
        #     serializer.data['name']) + '<br>' + 'Phone: ' + str(
        #     serializer.data['phone']) + '<br>' + 'Email: ' + str(
        #     serializer.data['email'])
        #
        # subject = str(event.name) + ' Registration'
        #
        # html_content = detail_htmlen + detail_html
        # if CURRENT_ENV == 'prod':
        #     send_email.delay(subject, html_content, ['support@golfconnect24.com'])
    else:
        serializer = RegisterEventSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        updated_values = {
            'is_active': True,
            'is_join': True,
            'status': 'A'
        }
        # EventMember.objects.update_or_create(user=request.user, event=event, defaults=updated_values)
        # member, created = EventMember.objects.update_or_create(user=request.user, event=event, defaults=updated_values)
        ### all golf user
        list_cus = []
        #########
        golfer_joined_number = request.DATA.get('golfer_joined_number')
        if not request.user.is_anonymous():
            ### user booked
            member, created = EventMember.objects.get_or_create(user=request.user, event_id=event_id)
            member.is_active = True
            member.is_join = True
            member.status = 'A'
            member.save(update_fields=['is_active', 'is_join', 'status'])

            # list_cus.append(member.customer)
            ### add golfer not userbooked
            for index_item in range(golfer_joined_number):

                name = request.DATA.get('golfer_joined_detail')[index_item]['name']
                email = request.DATA.get('golfer_joined_detail')[index_item]['email']
                phone = request.DATA.get('golfer_joined_detail')[index_item]['phone']
                if event.event_price_info.all().count() > 0:
                    customer = Customer.objects.create(name=name,
                                                       email=email,
                                                       phone_number=phone)
                    if 'handicap' in request.DATA.get('golfer_joined_detail')[index_item].keys():
                        customer.handicap = request.DATA.get('golfer_joined_detail')[index_item]['handicap']
                    else:
                        customer.handicap = None
                    if 'golfcourse' in serializer.data.keys():
                        # customer.golfcourse_id = int(serializer.data['golfcourse'])
                        customer.golfcourse_id = (serializer.data['golfcourse'])
                    customer.save()
                    member_join = EventMember.objects.create(customer=customer, event_id=event_id)
                    member_join.is_active = True
                    member_join.is_join = True
                    member_join.status = 'A'
                    member_join.save(update_fields=['is_active', 'is_join', 'status'])

                    list_cus.append(customer)
                    # if created:
                    # ctype = ContentType.objects.get_for_model(GolfCourseEvent)
                    # Invitation.objects.create(content_type=ctype, object_id=event.id, user=request.user,
                    #                               golfcourse=event.name,
                    #                               time=event.time, date=event.date_start)
        else:
            for index_item in range(golfer_joined_number):
                if index_item != 0:
                    name = request.DATA.get('golfer_joined_detail')[index_item]['name']
                    email = request.DATA.get('golfer_joined_detail')[index_item]['email']
                    phone = request.DATA.get('golfer_joined_detail')[index_item]['phone']

                    customer = Customer.objects.create(name=name,
                                                       email=email,
                                                       phone_number=phone)
                    if 'handicap' in request.DATA.get('golfer_joined_detail')[index_item].keys():
                        customer.handicap = request.DATA.get('golfer_joined_detail')[index_item]['handicap']
                    if 'golfcourse' in serializer.data.keys():
                        # customer.golfcourse_id = int(serializer.data['golfcourse'])
                        customer.golfcourse_id = (serializer.data['golfcourse'])
                    customer.save()

                    member_join = EventMember.objects.create(customer=customer, event_id=event_id)
                    member_join.is_active = True
                    member_join.is_join = True
                    member_join.status = 'A'
                    member_join.save(update_fields=['is_active', 'is_join', 'status'])
                    # list_cus.append(customer)
                elif index_item == 0:
                    name = request.DATA.get('golfer_joined_detail')[index_item]['name']
                    email = request.DATA.get('golfer_joined_detail')[index_item]['email']
                    phone = request.DATA.get('golfer_joined_detail')[index_item]['phone']

                    customer = Customer.objects.create(name=name,
                                                       email=email,
                                                       phone_number=phone)
                    if 'handicap' in request.DATA.get('golfer_joined_detail')[index_item].keys():
                        customer.handicap = request.DATA.get('golfer_joined_detail')[index_item]['handicap']
                    if 'golfcourse' in serializer.data.keys():
                        # customer.golfcourse_id = int(serializer.data['golfcourse'])
                        customer.golfcourse_id = (serializer.data['golfcourse'])
                    customer.save()

                    member = EventMember.objects.create(customer=customer, event_id=event_id)
                    member.is_active = True
                    member.is_join = True
                    member.status = 'A'
                    member.save(update_fields=['is_active', 'is_join', 'status'])
                list_cus.append(customer)

        if event.event_price_info.all().count() > 0:
            return handle_gc_event_booking(request, member, list_cus)

        # if request.user.is_anonymous():
        #     return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
        #                      'detail': 'You do not have permission to peform this action'}, status=401)
        # if EventMember.objects.filter(user_id=request.user.id, status='A', event=event).exists():
        #     return Response({'status': 400, 'code': 'E_ALREADY_EXIST', 'detail': 'You already joined this'},
        #                     status=400)
        # if event.is_publish is False:
        #     pass_code = request.DATA.get('pass_code', '')
        #     if event.pass_code and not EventMember.objects.filter(user=request.user, event=event,
        #                                                           is_active=True).exists() and event.user != request.user and event.pass_code != pass_code:
        #         return Response({'status': 400, 'code': 'E_INVALID_PARAMETER_VALUES', 'detail': 'Pass code mismatch'},
        #                         status=400)
        # # member = get_or_none(EventMember, user=request.user, event=event)
        # handicap = request.DATA.get('handicap', None)
        # memberID = request.DATA.get('memberID', None)
        # clubID = request.DATA.get('clubID', None)
        # updated_values = {
        #     'handicap': handicap,
        #     'memberID': memberID,
        #     'clubID': clubID,
        #     'is_active': True,
        #     'is_join': True,
        #     'status': 'A'
        # }
        # member, created = EventMember.objects.update_or_create(user=request.user, event=event, defaults=updated_values)
        # #
        # message = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
        #     request.user.user_profile.display_name) + '</a> tham gia sự kiện tại <b>' + event.golfcourse.name + '</b>'
        # if event.time:
        #     message += ' lúc <b>' + str(event.time.strftime('%H:%M')) + '</b>'
        # message += ' vào <b>' + DOW[str(event.date_start.strftime('%A'))] + ', ' + str(
        #     event.date_start.strftime('%d-%m-%Y')) + '</b>'
        #
        # message_en = '<a href=/#/profile/' + str(request.user.id) + '/>' + str(
        #     request.user.user_profile.display_name) + '</a>  joined the event at <b>' + event.golfcourse.name + '</b>'
        # if event.time:
        #     message_en += ' at <b>' + str(event.time.strftime('%H:%M')) + '</b>'
        # message_en += ' on <b>' + str(event.date_start.strftime('%A')) + ', ' + str(
        #     event.date_start.strftime('%d-%m-%Y')) + '</b>'
        #
        # message_notify_en = str(
        #     request.user.user_profile.display_name) + '  joined the event at ' + event.golfcourse.name
        # if event.time:
        #     message_notify_en += ' at ' + str(event.time.strftime('%H:%M'))
        # message_notify_en += ' on ' + str(event.date_start.strftime('%A')) + ', ' + str(
        #     event.date_start.strftime('%d-%m-%Y'))
        #
        # message_notify_vi = str(
        #     request.user.user_profile.display_name) + '  tham gia sự kiện tại ' + event.golfcourse.name
        # if event.time:
        #     message_notify_vi += ' lúc ' + str(event.time.strftime('%H:%M'))
        # message_notify_vi += ' vào ' + str(event.date_start.strftime('%A')) + ', ' + str(
        #     event.date_start.strftime('%d-%m-%Y'))
        #
        # translate_notify = {
        #     'alert_vi': message_notify_vi,
        #     'alert_en': message_notify_en
        # }
        #
        # event_member = event.event_member.all()
        # ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        #
        # for m in event_member:
        #     if m.user:
        #         Notice.objects.create(content_type=ctype,
        #                               object_id=event.id,
        #                               to_user=m.user,
        #                               detail=message,
        #                               detail_en=message_en,
        #                               notice_type='IN',
        #                               from_user=request.user,
        #                               send_email=False)
        #         # send_notification.delay([m.user.id], message_notify_en, translate_notify)
        #
        # Notice.objects.create(content_type=ctype,
        #                       object_id=event.id,
        #                       to_user=event.user,
        #                       detail=message,
        #                       detail_en=message_en,
        #                       notice_type='IN',
        #                       from_user=request.user,
        #                       send_email=False)
        # Notice.objects.filter(content_type=ctype,
        #                       object_id=event.id,
        #                       to_user=request.user,
        #                       notice_type='I').delete()
        # send_notification.delay([event.user.id], message_notify_en, translate_notify)
    return Response({'status': '200', 'code': 'OK', 'detail': 'OK'},
                    status=200)


# This view show pulic events
class LeaderBoardEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GolfCourseEvent.objects.all()
    serializer_class = PublicGolfCourseEventSerializer
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        today = datetime.date.today()
        return GolfCourseEvent.objects.filter(date_start__lte=today, date_end__gte=today)


# This view show advertise events
class AdvertiseEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GolfCourseEvent.objects.all()
    serializer_class = AdvertiseEventSerializer
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        return GolfCourseEvent.objects.filter(is_advertise=True)

    def list(self, request, *args, **kwargs):
        country = request.GET.get('country', None)
        if country:
            events = GolfCourseEvent.objects.filter(is_advertise=True,
                                                    golfcourse__country__short_name=country).order_by('-date_start')
        else:
            events = GolfCourseEvent.objects.filter(is_advertise=True).order_by('-date_start')
        serializers = AdvertiseEventSerializer(events)
        return Response(serializers.data, status=200)


class PublishEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GolfCourseEvent.objects.all()
    serializer_class = PublicGolfCourseEventSerializer
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        today = datetime.date.today()
        country = request.GET.get('country', None)

        if country:
            tz = timezone(country_timezones(country)[0])
            if tz:
                today = django_timezone.make_aware(datetime.datetime.now(), tz).date()
        else:
            today = datetime.date.today()
        first_today = today.replace(day=1)
        #try:
        #	year = int(request.GET.get('year', today.year))
        #except:
        #	pass
        if country:
            # golfcourse_name = GolfCourse.objects.filter(country__short_name=country).values_list('name', flat=True)
            #month = int(request.GET.get('month', today.month))
            #to_month = int(request.GET.get('to_month', today.month))
            from_date = first_today - datetime.timedelta(days=1)
            from_date = from_date.replace(day=1)
            #to_month += 1
            #delta = to_month - month
            #if delta < 0:
            #    delta += 12
            to_date = add_months(first_today,2)
            filter_condition1 = {
                'is_publish':True, 
                'date_start__gte':from_date,
                'date_start__lt':to_date,
                'golfcourse__country__short_name':country
            }
            filter_condition2 = {
                'is_publish':True, 
                'date_start__gte':from_date,
                'date_start__lt':to_date,
                'golfcourse__pk':0
            }
            semi_null = {
                'semi_null': 'coalesce(\"golfcourse_golfcourseevent\".\"banner\",\'\')=\'\''
            }
            gc_event = GolfCourseEvent.objects.filter(Q(**filter_condition1)|Q(**filter_condition2)).exclude(event_type='GE', date_end__lt=(datetime.date.today()- datetime.timedelta(days=14))).extra(select=semi_null, order_by=['semi_null','-date_start'])
            # invitation = Invitation.objects.filter(is_publish=True, date__gte=today, golfcourse__in=golfcourse_name)
        else:
            semi_null = {
                'semi_null': 'coalesce(\"golfcourse_golfcourseevent\".\"banner\",\'\')=\'\''
            }
            gc_event = GolfCourseEvent.objects.filter(is_publish=True, date_end__gte=today).exclude(event_type='GE', date_end__lt=(datetime.date.today()- datetime.timedelta(days=14))).extra(select=semi_null, order_by=['semi_null','-date_start'])
            # invitation = Invitation.objects.filter(is_publish=True, date__gte=today)
        gc_event_seri = PublicGolfCourseEventSerializer(gc_event)
        # invitation_seri = InvitationSerializer(invitation)
        if request.user.is_anonymous():
            user = None
        else:
            # user_ctype = ContentType.objects.get_for_model(User)
            user = request.user
        username = user.username if user else None
        for item in gc_event_seri.data:
            item.update({'is_join': False})
            item.update({'is_invited': False})
            if user:
                if EventMember.objects.filter(user=user, event_id=item['id']).exists() or item[
                    'user'] == request.user.id:
                    item.update({'is_join': True})
                if EventMember.objects.filter(user=user, event_id=item['id'], status='P').exists():
                    item.update({'is_invited': True})

            (count, uread) = get_from_xmpp(username, item['id'])
            item.update({'type': 'Event',
                         'object_id': item['id'],
                         'badge_notify': uread,
                         'comment_count': count})
        temp = list(gc_event_seri.data)
        return Response(temp, status=200)


class GroupEventViewSet(mixins.DestroyModelMixin, GenericViewSet):
    queryset = GroupOfEvent.objects.all()
    serializer_class = GroupOfEventSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated,)

    def destroy(self, request, pk=None):
        try:
            group = GroupOfEvent.objects.get(id=pk)
            if group.event_member.exists():
                return Response({'status': '400', 'code': 'E_NOT_DELETE',
                                 'detail': 'Not allow to delete this item'}, status=400)
            return super().destroy(request, pk)
        except Exception as e:
            return Response({'status': '400', 'code': 'E_EXCEPTION',
                             'detail': e}, status=400)


class EventMemberViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    queryset = EventMember.objects.all()
    serializer_class = EventMemberSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, IsGolfStaff)
    filter_fields = ('event',)

    def destroy(self, request, pk=None):
        try:
            if Game.objects.filter(event_member_id=pk).exists():
                return Response({'status': '400', 'code': 'E_NOT_DELETE',
                                 'detail': 'Not allow to delete this item'}, status=400)
            return super().destroy(request, pk)
        except Exception as e:
            return Response({'status': '400', 'code': 'E_EXCEPTION',
                             'detail': e}, status=400)

    def create(self, request, *args, **kwargs):
        # if not GolfCourseStaff.objects.filter(user_id=request.user.id).exists():
        # return Response({'status': '400', 'code': 'E_USER_NOT_FOUND',
        # 'detail': 'User can not be looked up'}, status=400)
        members = request.DATA['members']
        check_data = members[0]
        # event = get_or_none(GolfCourseEvent, id=int(check_data['event']))
        if not GolfCourseEvent.objects.filter(id=int(check_data['event'])).exists():
            return Response({'status': '400', 'code': 'E_EXCEPTION',
                             'detail': 'This event does not exist'}, status=400)
        check_group = {}
        # groups = event.group_event.all().only('id','name')
        # for g in groups:
        # check_group.update({g.name: g.id})
        event = int(check_data['event'])
        # memberIDs = [x['memberID'] for x in members if not 'id' in x and x['memberID']]


        group_ids = GroupOfEvent.objects.filter(event_id=event).values_list('id', flat=True)
        registered_member = list(EventMember.objects.filter(event_id=event).values('customer__name', 'id'))
        register_name = {}
        member_names = []
        for m in registered_member:
            register_name.update({
                m['customer__name']: m['id']
            })
        for data in members:
            if data['group'] and int(data['group']) not in group_ids:
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'Member ' + str(data['memberID']) + ' has invalid group'}, status=400)
            if 'handicap' in data and data['handicap']:
                try:
                    float(data['handicap'])
                except ValueError:
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Member ' + str(data['memberID']) + ' has invalid handicap'}, status=400)
            if data['name'] in register_name:
                data.update({'id': register_name[data['name']]})
            member_names.append(data['name'])
        # serializers = EventMemberSerializer(data=create_members, many=True)
        # if not serializers.is_valid():
        # return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
        # 'detail': serializers.errors}, status=400)

        create_member = []
        # EventMember.objects.filter(event_id=event).delete()
        # x = redis_server.keys('event-' +str(event) + '-*')
        # for key in x:
        # redis_server.delete(key)
        for data in members:
            event = int(data['event'])
            memberID = data['memberID']
            clubID = data['clubID']
            gender = data['gender']
            if 'handicap' in data and data['handicap']:
                handicap = data['handicap']
            else:
                handicap = None
            if data['group']:
                group = int(data['group'])
            else:
                group = None
            if 'email' not in data:
                data.update({'email': ''})
            # group = None
            # if group_data in check_group:
            # group = check_group[group_data]
            # data['group'] = group
            if 'id' in data and data['id']:
                try:
                    member = EventMember.objects.get(id=int(data['id']))
                    member.memberID = memberID
                    member.clubID = clubID
                    member.group_id = group
                    member.handicap = handicap
                    member.gender = gender
                    member.is_active = True
                    member.save()
                    # if member.customer:
                    # member.customer.name = data['name']
                    # member.customer.handicap = data['handicap']
                    # member.customer.email = data['email']
                    # member.customer.save(update_fields=['name', 'handicap', 'email'])
                except (Exception, IntegrityError) as e:
                    return Response({'status': '400', 'code': 'E_EXCEPTION',
                                     'detail': e}, status=400)
            else:
                try:
                    # num = EventMember.objects.filter(memberID=memberID, clubID=clubID, event_id=event).update(
                    # group_id=group)
                    # member = get_or_none(EventMember, memberID=memberID, clubID=clubID, event_id=event)
                    # if num == 0:
                    c = Customer.objects.create(name=data['name'], handicap=handicap, email=data['email'])
                    # EventMember.objects.create(memberID=memberID, clubID=clubID, event_id=event, group_id=group,
                    # customer=c)
                    create_member.append(
                        EventMember(memberID=memberID, clubID=clubID, event_id=event, group_id=group, customer=c,
                                    gender=gender,
                                    is_active=True))
                except (Exception, IntegrityError) as e:
                    return Response({'status': '400', 'code': 'E_EXCEPTION',
                                     'detail': str(e)}, status=400)
        try:
            EventMember.objects.bulk_create(create_member)
        except (Exception, IntegrityError) as e:
            return Response({'status': '400', 'code': 'E_EXCEPTION',
                             'detail': str(e)}, status=400)
        member_delete = []
        for m in registered_member:
            if m['customer__name'] not in member_names:
                member_delete.append(m['id'])
        if member_delete:
            EventMember.objects.filter(id__in=member_delete).delete()
            x = redis_server.keys('event-' + str(event) + '-*')
            for key in x:
                redis_server.delete(key)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)

    def list(self, request, *args, **kwargs):
        user = self.request.user
        golfstaff = user.golfstaff.all()
        gc_id = []
        for gs in golfstaff:
            gc_id.append(gs.golfcourse_id)
        event = request.QUERY_PARAMS.get('event', '')
        get_result = request.QUERY_PARAMS.get('result', False)
        results = {'members': [], 'hdc_system': ''}
        result = []

        if event:
            try:
                e = GolfCourseEvent.objects.get(id=int(event))
                if get_result:
                    calculation = request.QUERY_PARAMS.get('cal', '')
                    groups = e.group_event.all()
                    if calculation == 'stable_ford':
                        sort_type = '-hdc_stable_ford'
                    elif calculation == 'hdcus':
                        sort_type = 'hdc_us'
                    elif calculation == 'callaway':
                        sort_type = 'hdc_callaway'
                    elif calculation == 'peoria' or calculation == 'db_peoria':
                        sort_type = 'hdc_peoria'
                    elif calculation == 'system36':
                        sort_type = 'hdc_36'
                    else:
                        sort_type = 'hdcp'
                    for group in groups:
                        temp = group.event_member.all().order_by(sort_type)
                        serializer = EventMemberSerializer(temp, many=True)
                        i = 1
                        for res in serializer.data:
                            res.update({'rank': i})
                            i += 1
                        result += serializer.data
                        results = {'members': result, 'hdc_system': calculation}
                else:
                    members = e.event_member.all()
                    serializers = self.serializer_class(members)
                    results = {'members': serializers.data}
            except Exception as e:
                return Response({'status': '400', 'code': 'E_EXCEPTION',
                                 'detail': e}, status=400)
        return Response(results, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def delete_list_member(request):
    from api.golfcourseeventMana.tasks import async_ranking
    member_list = request.DATA.get('member_list', [])
    try:
        if member_list:
            event_member = EventMember.objects.filter(id=member_list[0]).first()
            if not event_member:
                return Response({'status': 404, 'detail': 'Member not found'}, status=404)
            EventMember.objects.filter(id__in=member_list).delete()
            if event_member.event:
                # results = ranking(event_member.event, date_play)
                # channel = 'event-' + str(event_member.event.id) + '-' + str(date_play)
                try:
                    async_ranking.delay(event_member.event.id, str(event_member.event.date_start))
                except Exception as e:
                    print(e)
                    pass
            return Response({'status': 200, 'detail': 'OK'}, status=200)
    except Exception as e:
        return Response({'detail': str(e)}, status=400)


p = re.compile(r'(?P<name>[^/]+) \((?P<id>[^/]+)\)')


class ListMember(APIView):
    def get(self, request):
        page = 0
        clubID = request.QUERY_PARAMS.get('clubID', '')
        if os.path.isfile(clubID):
            json_data = open(clubID)
            data = json.load(json_data)

        result = redis_server.get(clubID)

        if not result:
            result = []
            while 1:
                r = requests.get(
                    'http://www.ehandicap.net/cgi-bin/hcapstat.exe?CID=' + clubID + '&GID=&MID=&START=' + str(
                        page) + '&ACTION=Search')
                soup = BeautifulSoup(r.text)
                tds = soup.find_all('td')
                if len(tds) <= 3:
                    break
                for i in range(0, len(tds)):
                    if tds[i].a:
                        m = p.match(tds[i].a.text)
                        if m:
                            temp = {'name': '', 'memberID': '', 'handicap': '', 'clubID': clubID, 'index': ''}
                            temp['name'] = m.group('name')
                            temp['memberID'] = m.group('id')

                            i += 1
                            # l = len(tds[i].text) - 1
                            temp['index'] = tds[i].text

                            i += 2
                            temp['handicap'] = tds[i].text
                            result.append(temp)
                page += 20
            result = json.dumps(result, cls=encoders.JSONEncoder)
            redis_server.set(clubID, result)
        else:
            result = result.decode()
        result = json.loads(result)
        memberID = request.QUERY_PARAMS.get('member', '')
        if memberID:
            member = next((item for item in result if item["memberID"] == memberID), {})
            return Response(member, status=200)
        name = request.QUERY_PARAMS.get('name', '')
        if name:
            member = next((item for item in result if item["name"] == name), {})
            return Response(member, status=200)
        return Response(result, status=200)


class EventPrizeViewSet(mixins.CreateModelMixin,
                        GenericViewSet):
    queryset = EventPrize.objects.all()
    serializer_class = EventPrizeSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (permissions.IsAuthenticated, IsGolfStaff)

    def create(self, request, *args, **kwargs):
        prize_list = request.DATA['prize_list']
        result = []
        serializers = self.serializer_class(data=prize_list, many=True)
        if not serializers.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializers.errors}, status=400)
        for item in prize_list:
            item['prize_name'] = item['prize_name'].lower()
            if 'id' in item and item['id']:
                prize = EventPrize.objects.get(id=int(item['id']))
                prize.player_name = item['player_name']
                prize.prize_name = item['prize_name']
                if 'description' in item:
                    prize.description = item['description']
                prize.save()
                serializers = EventPrizeSerializer(prize)
            else:
                serializers = self.serializer_class(data=item)
                serializers.is_valid()
                serializers.save()
            result.append(serializers.data)
        return Response({'status': '200', 'code': 'OK',
                         'detail': {'prize': result}},
                        status=200)
