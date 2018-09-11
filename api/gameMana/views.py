import datetime
import json
import logging
import uuid
from queue import Queue
from threading import Thread

import redis
from GolfConnect.celery import celery_is_up
from api.gameMana.tasks import async_calculate_game
from api.userMana.tasks import log_activity
from copy import deepcopy
from core.notice.models import Notice
from core.user.models import UserActivity
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Avg
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PaginationSerializer
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.customer.models import Customer
from core.game.models import Game, Score, EventMember, GameFlight
from core.golfcourse.models import GroupOfEvent, GolfCourseEvent, Hole
from api.gameMana.serializers import GameSerializer, ScoreSerializer, MiniGameSerializer, GameFlightSerializer
from api.golfcourseMana.serializers import GolfCourseListSerializer
from utils.rest.permissions import UserIsOwnerOrReadOnly
from utils.django.models import get_or_none
from utils.rest.code import code
from utils.rest.viewsets import CreateOnlyViewSet, ListOnlyViewSet
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB
from api.golfcourseeventMana.tasks import async_ranking
from utils.rest.handicap import handicap_index
from django.db.models import Q


redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


# p = redis_server.pubsub(ignore_subscribe_messages=True)

class CalculateWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            game_id = self.queue.get()
            async_calculate_game(game_id, normal=True, hdcus=True, system36=True, hdc_net=True)
            self.queue.task_done()


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def delete_list_game(request):
    game_list = request.DATA.get('game_list', [])
    try:
        if game_list:
            game = Game.objects.only('event_member_id', 'date_play').get(id=game_list[0])
            event_member_id = game.event_member_id
            date_play = game.date_play
            Game.objects.filter(id__in=game_list).delete()
            event_member = EventMember.objects.only('event_id').get(id=event_member_id)
            if event_member.event:
                # results = ranking(event_member.event, date_play)
                # channel = 'event-' + str(event_member.event.id) + '-' + str(date_play)
                try:
                    async_ranking.delay(event_member.event.id, str(date_play))
                except Exception as e:
                    print(e)
                    pass
            return Response({'status': 200, 'detail': 'OK'}, status=200)
    except Exception as e:
        return Response({'detail': str(e)}, status=400)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_maps(request):
    player = get_or_none(User, pk=request.user.id)
    if player is None:
        return Response({'status': '404', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=404)
    # ctype = ContentType.objects.get_for_model(player)

    # Check In
    # checkin = Checkin.objects.filter(content_type=ctype, object_id=player.id)
    # checkin = list(
    # sorted(checkin, key=lambda x: x.date and x.time, reverse=True))
    detail = []
    # ctype = ContentType.objects.get_by_natural_key('checkin', 'checkin')
    # for ite in checkin:
    #     try:
    #         game = get_or_none(
    #             Game, content_type=ctype.id, object_id=ite.id, event_member__user_id=request.user.id)
    #         if game is None:
    #             detail.append(
    #                 {'id': ite.id, 'date': ite.date, 'golfcourse': ite.golfcourse.name,
    #                  'golfcourse_id': ite.golfcourse.id, 'reservation_code': ite.reservation_code, 'type': 'C'})
    #     except Exception:
    #         pass
    # Invitation
    invite = GolfCourseEvent.objects.filter(user=player)

    ctype = ContentType.objects.get_for_model(GolfCourseEvent)
    for ite in invite:
        try:
            game = get_or_none(
                Game, content_type=ctype.id, object_id=ite.id, event_member__user_id=request.user.id)
            if game is None:
                # golfcourse = get_or_none(GolfCourse, name=ite.golfcourse)
                # if golfcourse is None:
                #     golfcourse_id = 0
                # else:
                #     golfcourse_id = golfcourse.id
                detail.append({'id': ite.id, 'date': ite.date_start, 'golfcourse': ite.golfcourse.name,
                               'golfcourse_id': ite.golfcourse.id, 'type': 'I'})
        except Exception:
            pass

    # invited people
    invited = EventMember.objects.filter(user=player)
    for ite in invited:
        invite = ite.event
        try:
            game = get_or_none(
                Game, content_type=ctype.id, object_id=invite.id, event_member__user_id=request.user.id)
            if game is None:
                detail.append({'id': invite.id, 'date': invite.date_start, 'golfcourse': invite.golfcourse.name,
                               'golfcourse_id': invite.golfcourse.id, 'type': 'I'})
        except Exception:
            pass
    detail = list(sorted(detail, key=lambda x: x['date'], reverse=True))
    return Response(detail, status=200)


class ScoreViewSet(CreateOnlyViewSet):
    queryset = Score.objects.all()
    serializer_class = ScoreSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def create(self, request, *args, **kwargs):
        score_list = request.DATA
        data = []
        if type(score_list) == type([]):
            data = score_list
        else:
            if 'score_list' in request.DATA:
                data = request.DATA['score_list']
            else:
                data.append(request.DATA)
        saved_score = []
        game_ids = []
        score_ids = []

        # --------------------------- Validate data ----------------------------------------------#
        for d in data:
            game_id = int(d['game'])
            if game_id not in game_ids:
                game_ids.append(game_id)
            try:
                score = Score.objects.only('id').get(hole_id=int(d['hole']), game_id=int(d['game']))
                d.update({'id': score.id})
            except Exception:
                pass
            if 'id' in d and d['id']:
                if not isinstance(d['stroke'], int):
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Stroke must be integer'},
                                    status=400)
                score_ids.append(int(d['id']))
            else:
                serializers = self.serializer_class(data=d)

                if not serializers.is_valid():
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': serializers.errors},
                                    status=400)
                if Game.objects.filter(id=int(d['game']), event_member__is_active=False).exists() \
                        and not Game.objects.filter(id=int(d['game']), event_member__event__user=request.user).exists():
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Game is not activated'},
                                    status=400)
        # --------------------------- Save game ----------------------------------------------#
        create_score = []
        for d in data:
            if 'putt' in d:
                putt = d['putt']
            else:
                putt = 0
            if 'id' in d and d['id']:
                # score = Score.objects.only('stroke').get(id=int(d['id']))
                # score.stroke = int(d['stroke'])
                # score.save(update_fields=['stroke'])
                Score.objects.filter(id=int(d['id'])).update(stroke=int(d['stroke']), putt=putt)
            else:
                score = Score(game_id=int(d['game']), hole_id=int(d['hole']),
                              tee_type_id=int(d['tee_type']), stroke=int(d['stroke']), putt=putt)
                create_score.append(score)
        if create_score:
            Score.objects.bulk_create(create_score)
        games = Game.objects.filter(id__in=game_ids)
        for game in games:
            game.calculate_handicap(hdc_net=True)
        today = datetime.date.today()
        if games and games[0].event_member.event.date_start == today:
            async_ranking.delay(games[0].event_member.event_id, str(today))
        return Response({'status': '200', 'code': 'OK',
                         'detail': {'saved_score': saved_score}},
                        status=200)


class GameViewSet(viewsets.ModelViewSet):
    """ Handle for games
    """
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)
    paginate_by = 10

    def create(self, request, *args, **kwargs):
        """ In: reservation_code
            Out:
                201 - New Game Info
                400 - Game Info if game is exist
                404 - Not Found
        """
        game_list = request.DATA
        data = []
        if type(game_list) == type([]):
            data = game_list
        else:
            if 'game_list' in request.DATA:
                data = request.DATA['game_list']
            else:
                data.append(request.DATA)

        # --------------------------- Validate data ----------------------------------------------#
        not_register_member = []  # check inactive members for event
        duplicate_member = []  # check duplicate members for event
        duplicate_checker_memberID = []  # check duplicate member ID for event
        duplicate_member_userID = []  # check duplicate user id for event
        duplicate_game = []  # check duplicate game

        duplicate_checker_group = []
        duplicate_checker_name = []
        duplicate_group = []
        not_exist_group = []

        valid = True
        event_id = None
        group_event = None
        is_user_member = False
        group_has_member = []
        gc_event = None
        pre_save_game = []
        pre_save_score = []
        first_event_id = None
        # data = list(filter(lambda x: 'id' not in x, data))
        event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        if data:
            d = data[0]
            all_member_name = []
            valid_members = []
            if 'event' in d and d['event']:
                first_event_id = int(d['event'])
                gc_event = GolfCourseEvent.objects.get(id=first_event_id)
                group_has_member = GroupOfEvent.objects.filter(event_id=first_event_id,
                                                               event_member__isnull=False).values_list(
                    'name', flat=True)
                all_members = list(EventMember.objects.filter(event_id=first_event_id).values_list(
                    'customer__name', 'is_active'))
                valid_members = [x[0] for x in all_members if x[1] is True]
                all_member_name = [x[0] for x in all_members]
            date_play = None
            if 'date_play' in d and d['date_play']:
                date_play = datetime.datetime.strptime(d['date_play'], '%Y-%m-%d').date()
            # get cached result
            if date_play and gc_event:
                if gc_event.rule == 'normal':
                    try:
                        channel = 'event-' + str(gc_event.id) + '-' + str(date_play)
                        cache_results = redis_server.get(channel)
                        if cache_results:
                            cache_results = json.loads(cache_results.decode())
                            # Get all members had game
                            member_names = [x['name'] for x in cache_results['members'] if
                                            x['game'] and x['game']['score']]
                            temp_data = []
                            for i, d in enumerate(data):
                                try:
                                    # Get inx of scored member
                                    member_idx = member_names.index(d['name'])

                                    temp = []
                                    # Only get score not saved
                                    for score in d['score']:
                                        for cache_score in cache_results['members'][member_idx]['game']['score']:
                                            if score['hole'] == cache_score['hole']:
                                                if str(score['stroke']) != str(cache_score['stroke']):
                                                    temp.append(score)
                                                break
                                    d['score'] = temp
                                    if 'group' in d:
                                        if d['group'] == cache_results['members']['group']:
                                            d.update({
                                                'same_group': True
                                            })
                                        else:
                                            d.update({'same_group': False})
                                    if 'memberID' in d:
                                        if d['memberID'] == cache_results['members']['memberID']:
                                            d.update({
                                                'same_memberID': True
                                            })
                                        else:
                                            d.update({'same_memberID': False})
                                except ValueError:
                                    pass
                                temp_data.append(d)
                            logging.error(temp_data)
                            data = temp_data
                    except Exception:
                        pass
        else:
            return Response({'detail': 'OK', 'status': 200}, status=200)
        for i, d in enumerate(data):
            if 'user' in d and d['user']:
                user = int(d['user'])
            else:
                user = None

            if 'event' in d and d['event']:
                event = int(d['event'])
                d['score'] = list(filter(lambda x: 'stroke' in x and x['stroke'], d['score']))
                if not event_id:
                    if not 'golfcourse' in d:
                        d.update({'golfcourse': gc_event.golfcourse_id})
                    event_id = event

            else:
                event = None
            if event_id != event:
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'There are more 2 events in this request'}, status=400)

            if 'memberID' in d and d['memberID']:
                memberID = d['memberID']
            else:
                memberID = None
            if 'content_type' in d:
                if d['content_type'] == 'Event':
                    d['content_type'] = event_ctype.id
                    if 'object_id' in d:
                        d.update({'event': d['object_id']})
                        if not gc_event:
                            try:
                                gc_event = GolfCourseEvent.objects.only('id', 'event_type').get(id=d['object_id'])
                            except Exception:
                                return Response(
                                    {'status': 404, 'code': 'E_NOT_FOUND', 'detail': 'Not found this event'})
            if event:
                if 'name' in d and d['name']:
                    name = d['name']
                else:
                    name = None
                if 'group_name' in d and d['group_name']:
                    group_name = d['group_name'].lower()
                else:
                    group_name = None
                if gc_event.rule == 'scramble':
                    if group_name:
                        if not group_event:
                            group_event = GroupOfEvent.objects.filter(event_id=event).values_list('name', flat=True)
                        if group_name not in group_event:
                            not_exist_group.append(i)
                            valid = False
                        if group_name not in duplicate_checker_group:
                            duplicate_checker_group.append(group_name)
                        else:
                            duplicate_group.append(i)
                            valid = False
                        if group_name not in group_has_member:
                            not_register_member.append(i)
                            # valid = False
                else:
                    if gc_event.event_type == 'GE':
                        if name:
                            # exists = EventMember.objects.filter(customer__name=name, event_id=event,
                            # is_active=True).exists()
                            if name not in valid_members:
                                # valid = False
                                not_register_member.append(i)
                            if name not in duplicate_checker_name:
                                duplicate_checker_name.append(name)
                            else:
                                duplicate_member.append(i)
                                valid = False
                        else:
                            # valid = EventMember.objects.filter(memberID=memberID, user_id=user, event_id=event,
                            # is_active=True).exists()
                            # if not valid:
                            not_register_member.append(i)
                    else:
                        if not is_user_member:
                            if not EventMember.objects.filter(user=request.user, event_id=event,
                                                              is_active=True).exists() and not GolfCourseEvent.objects.filter(
                                user=request.user, id=event).exists():
                                return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                                                 'detail': 'You do not have permission to peform this action'},
                                                status=401)
                            else:
                                is_user_member = True
            if memberID:
                memberID = d['memberID']
                if memberID not in duplicate_checker_memberID:
                    duplicate_checker_memberID.append(memberID)
                else:
                    valid = False
                    duplicate_member.append(i)
            elif user:
                user = d['user']
                if user not in duplicate_member_userID:
                    duplicate_member_userID.append(user)
                else:
                    valid = False
                    duplicate_member.append(i)

            if 'game_type' in d:
                ctype = None
                game_type = d['game_type']
                if game_type == 'I':
                    ctype = ContentType.objects.get_for_model(GolfCourseEvent)
                if ctype is not None:
                    d['content_type'] = ctype.id

        if not valid:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': {
                                 'duplicate_member': duplicate_member,
                                 'duplicate_game': duplicate_game,
                                 'duplicate_group': duplicate_group,
                                 'not_exist_group': not_exist_group}},
                            status=400)
        # --------------------------- Save game ----------------------------------------------#
        group_link = str(uuid.uuid1())
        # flight = Flight.objects.create(event_id=event_id)
        saved_game = []
        saved_member = []
        # user_display_name = UserProfile.objects.only('display_name').get(user=request.user).display_name
        for idx, d in enumerate(data):
            if 'handicap' in d and d['handicap']:
                try:
                    handicap = float(d['handicap'])
                except:
                    handicap = None
            else:
                handicap = None

            if 'event' in d and d['event']:
                try:
                    event = int(d['event'])
                except:
                    event = None
            else:
                event = None

            if 'user' in d and d['user']:
                try:
                    user = int(d['user'])
                except:
                    user = None
            else:
                user = None

            if 'group_name' in d and d['group_name']:
                group_name = d['group_name'].lower()
            else:
                group_name = None

            if 'name' in d and d['name']:
                name = d['name']
            else:
                name = None
            if 'id' in d and d['id']:
                member_id = d['id']
            else:
                member_id = None
            if 'date_play' not in d or not d['date_play']:
                d.update({'date_play': datetime.date.today()})
            else:
                d['date_play'] = datetime.datetime.strptime(d['date_play'], '%Y-%m-%d').date()
            # for update game
            member = None
            if member_id:
                member = EventMember.objects.get(id=d['id'])
                member.customer.name = name
                member.customer.save(update_fields=['name'])
                if name not in valid_members:
                    member.is_active = False
                else:
                    member.is_active = True
                member.save(update_fields=['is_active'])
            if not member:
                if idx in not_register_member:
                    if name in all_member_name:
                        member = EventMember.objects.get(customer__name=name, event_id=event, is_active=False)
                    else:
                        c = Customer.objects.create(name=name)
                        member = EventMember.objects.create(customer=c, event_id=event, is_active=False)
            if event and gc_event.event_type == 'GE':
                d.update({'golfcourse': gc_event.golfcourse_id})
                if not member:
                    if gc_event.rule == 'scramble':
                        if group_name:
                            members = EventMember.objects.only('id').filter(group__name=group_name, event_id=event,
                                                                            game__isnull=False)[:1]
                            if members:
                                member = members[0]
                    if name:
                        member = EventMember.objects.only('id').get(customer__name=name, event_id=event, is_active=True)
                if member:
                    # if 'gender' in d:
                    #     if d['gender'] == 'F':
                    #         lady_member.append(member.id)
                    #     else:
                    #         man_member.append(member.id)
                    # is_save_member = False
                    if 'group' in d and d['group']:
                        member.group_id = d['group']
                    if 'memberID' in d and d['memberID']:
                        member.memberID = d['memberID']
                    member.save(update_fields=['memberID', 'group'])
                    try:
                        game = Game.objects.only('id').get(event_member_id=member.id, date_play=d['date_play'])
                        scores = d['score']
                        save_score = []
                        for score in scores:
                            # if 'id' in score and score['id']:
                            num_update_score = Score.objects.filter(game=game, hole_id=int(score['hole'])).update(
                                stroke=int(score['stroke']), tee_type_id=int(score['tee_type']))
                            if num_update_score == 0:
                                s = Score(game=game, stroke=int(score['stroke']), hole_id=score['hole'],
                                          tee_type_id=score['tee_type'])
                                save_score.append(s)
                        if save_score:
                            Score.objects.bulk_create(save_score)
                        if scores:
                            game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
                        # game.update_hdcp_index()
                        saved_game.append(game.id)
                        saved_member.append(member.id)
                        continue
                    except Exception as e:
                        print(e)

            # else
            created = False
            if not user:
                if event and gc_event.event_type == 'GE':  # save games for event
                    # pass
                    if group_name and gc_event.rule == 'scramble':
                        members = EventMember.objects.only('id', 'customer_id').filter(group__name=group_name,
                                                                                       event_id=event)[:1]
                        member = members[0]
                    else:
                        member = EventMember.objects.only('id').get(customer__name=name, event_id=event)

                    if 'handicap' not in d or not d['handicap']:
                        if member.group and member.group.from_index:
                            d.update({'handicap': member.group.from_index})

                    c = Customer.objects.only('email').get(id=member.customer_id)
                else:  # save for normal user
                    customer_email = d['email'] if 'email' in d else None

                    usr = get_or_none(User, username=customer_email) if customer_email else None
                    if usr:
                        member, created = EventMember.objects.get_or_create(user=usr, event_id=event)
                    else:
                        customer_name = d['name'] if 'name' in d else None
                        customer_avatar = d['avatar'] if 'avatar' in d else None
                        customer_phone = d['phone_number'] if 'phone_number' in d else None
                        try:
                            if customer_phone:
                                c = EventMember.objects.only('customer_id').get(customer__phone_number=customer_phone,
                                                                                event_id=event)
                            elif customer_email:
                                c = EventMember.objects.only('customer_id').get(customer__email=customer_email,
                                                                                event_id=event)
                            d.update({'customer': c.customer_id})
                        except Exception:
                            pass
                        if 'customer' in d and d['customer']:
                            customer_id = int(d['customer'])
                            member, created = EventMember.objects.only('id').get_or_create(customer_id=customer_id,
                                                                                           event_id=event)
                        else:
                            if not handicap:
                                c = Customer.objects.create(name=customer_name, email=customer_email,
                                                            avatar=customer_avatar, phone_number=customer_phone)
                            else:
                                c = Customer.objects.create(name=customer_name, email=customer_email,
                                                            avatar=customer_avatar, handicap=handicap,
                                                            phone_number=customer_phone)
                            customer_id = c.id
                            created = True
                            member = EventMember.objects.create(customer_id=customer_id, event_id=event, is_active=True)
            else:
                member, created = EventMember.objects.only('id').get_or_create(user_id=user, event_id=event)
            d.update({'event_member': member.id})
            if idx not in not_register_member:
                member.is_active = True
            else:
                member.is_active = False
            member.is_join = True
            member.save(update_fields=['is_active', 'is_join'])
            d.update({'recorder': request.user.id})

            if user == request.user.id:
                d.update({'active': True})

            d.update({'group_link': group_link})
            # update score for registered member
            if not created:
                if event and gc_event.event_type == 'PE':  # update game if it already existed
                    games = Game.objects.only('id', 'handicap').filter(event_member_id=d['event_member'],
                                                                       date_play=d['date_play'])
                    if games:
                        if games.count() > 1:
                            return Response(
                                {'detail': 'Event member ' + str(d['event_member']) + ' has 2 events on same day',
                                 'status': 400}, status=400)
                        game = games[0]
                        game.handicap = handicap
                        game.save(update_fields=['handicap'])
                        scores = d['score']
                        save_score = []
                        for score in scores:
                            # if 'id' in score and score['id']:
                            num_update_score = Score.objects.filter(game=game, hole_id=int(score['hole'])).update(
                                stroke=int(score['stroke']), tee_type_id=int(score['tee_type']))
                            if num_update_score == 0:
                                s = Score(game=game, stroke=int(score['stroke']), hole_id=score['hole'],
                                          tee_type_id=score['tee_type'])
                                save_score.append(s)
                        if save_score:
                            Score.objects.bulk_create(save_score)

                        if game.score.exists():
                            game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
                            game.update_hdcp_index()
                        group_link = game.group_link
                        saved_game.append(game.id)
                        continue

            if event and gc_event.event_type == 'GE':
                # pre_save_game.append(Game(
                # date_play = serializer.data['date_play'],
                #     event=serializer.data['event'],
                #     golfcourse=serializer.data['golfcourse'],
                #     event_member_id=serializer.data['event_member'],
                #     recorder = serializer.data['recorder']
                # ))

                g = Game.objects.create(
                    date_play=date_play,
                    golfcourse_id=d['golfcourse'],
                    event_member_id=d['event_member'],
                    recorder_id=d['recorder']
                )
                pre_save_game.append(g)
                saved_game.append(g.id)
                saved_member.append(member.id)
                for s in d['score']:
                    pre_save_score.append(Score(
                        game=g,
                        hole_id=s['hole'],
                        tee_type_id=s['tee_type'],
                        stroke=s['stroke']
                    ))
                continue
            serializer = self.serializer_class(data=d)
            if not serializer.is_valid():
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': serializer.errors, 'data': serializer.data, 'd': d}, status=400)
            game = serializer.save()
            # GameFlight.objects.create(flight=flight, member=member, game=game)

            if not game.time_play:
                game.time_play = datetime.datetime.now().time()
                game.save(update_fields=['time_play'])

            if game.score.exists():
                game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
                game.update_hdcp_index()
            saved_game.append(game.id)
        if gc_event and gc_event.date_start == datetime.date.today():
            Score.objects.bulk_create(pre_save_score)
            queue = Queue()
            for x in range(2):
                worker = CalculateWorker(queue)
                # Setting daemon to True will let the main thread exit even though the workers are blocking
                worker.daemon = True
                worker.start()
            for g in pre_save_game:
                queue.put(g.id)
            queue.join()
            if celery_is_up():
                try:
                    async_ranking.delay(gc_event.id, str(date_play))
                except Exception as e:
                    pass

        return Response(
            {'status': '200', 'detail': {'saved_member': saved_member, 'saved_game': saved_game,
                                         'not_register_member': not_register_member, 'event': first_event_id},
             'code': 'OK'},
            status=200)

    def partial_update(self, request, pk=None):
        temp = super(GameViewSet, self).partial_update(request, pk)
        if temp.status_code == 200:
            game = Game.objects.get(id=pk)
            game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
            game.update_hdcp_index()
            serializer = self.serializer_class(game)
            return Response(serializer.data, status=200)
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)

    def list(self, request):
        """ Use this api like this: api/game/?user=3&from_date=2014-09-20&to_date=2014-09-21"""
        recent = request.QUERY_PARAMS.get('recent', '')
        # Get recent game
        if recent == 'true':
            today = datetime.date.today()

            game_ids = Game.objects.filter(event_member__user=request.user).order_by('golfcourse_id',
                                                                                     '-date_create').distinct(
                'golfcourse_id')
            games = Game.objects.filter(id__in=game_ids).order_by('-date_create')[:5]
            result = []
            gc_id = []
            for game in games:
                if game.golfcourse.id not in gc_id:
                    gc_id.append(game.golfcourse.id)
                    gc_seri = GolfCourseListSerializer(game.golfcourse)
                    result.append(gc_seri.data)
            return Response(result, status=200)

        invited_player = request.QUERY_PARAMS.get('invited-player', '')
        if invited_player == 'true':
            event_id = request.QUERY_PARAMS.get('event_id')
            result = []
            try:
                int(event_id)
            except ValueError:
                return Response(result, status=200)
            recent_members = EventMember.objects.filter(event_id=event_id,
                                                        user_id__isnull=False) \
                .exclude(user=request.user) \
                .order_by('user_id').distinct('user_id')

            for member in recent_members:
                result.append({
                    'user': member.user.id, 'email': member.user.username,
                    'name': member.user.user_profile.display_name,
                    'handicap': member.user.user_profile.handicap_us,
                    'avatar': member.user.user_profile.profile_picture
                })
            return Response(result, status=200)

        # Get recent player play with
        recent_player = request.QUERY_PARAMS.get('recent-player', '')
        if recent_player == 'true':
            today = datetime.date.today()
            games = Game.objects.filter(date_play__month=today.month, event_member__user=request.user)
            result = []
            user_id = []
            cus_id = []
            user_id.append(request.user.id)
            for game in games:
                if game.group_link:
                    related_games = Game.objects.filter(group_link=game.group_link)
                    for game in related_games:
                        g = game.event_member
                        if g.user and g.user.id not in user_id:
                            result.append({'customer': '', 'user': g.user.id, 'email': g.user.username,
                                           'name': g.user.user_profile.display_name,
                                           'handicap': g.user.user_profile.handicap_us,
                                           'avatar': g.user.user_profile.profile_picture})
                            user_id.append(g.user.id)
                        elif g.customer and g.customer.id not in cus_id:
                            result.append({'customer': g.customer.id, 'user': "", 'email': g.customer.email,
                                           'name': g.customer.name, 'handicap': g.customer.name,
                                           'avatar': g.customer.avatar})
                            cus_id.append(g.customer.id)
            return Response(result, status=200)

        filter_params = {
            'event_member__user_id': request.QUERY_PARAMS.get('user', request.user.id),
        }
        if request.QUERY_PARAMS.get('is_finish'):
            filter_params.update({'is_finish': request.QUERY_PARAMS.get('is_finish'), 'active': True})
        games = Game.objects.filter(**filter_params).order_by('-date_play', '-id')
        #hdcp_avg = games.filter(is_finish=True, golfcourse__number_of_hole__gte=18).aggregate(Avg('hdcp'))
        hdcp_avg = {'hdcp__avg':0}
        #hdus_avg = games.filter(is_finish=True, golfcourse__number_of_hole__gte=18).aggregate(Avg('hdc_36'))
        hdus_avg = {'hdc_36__avg':0}
        #handicap_us
        handicap_us = {'handicap_us': request.user.user_profile.handicap_us or 'N/A'}
        # filter by date
        from_date = request.QUERY_PARAMS.get('from_date', '')
        if from_date != '':
            from_date = datetime.datetime.strptime(
                from_date, '%Y-%m-%d').date()
            games = list(filter(lambda x: x.date_play >= from_date, games))

        to_date = request.QUERY_PARAMS.get('to_date', '')
        if to_date != '':
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
            games = list(filter(lambda x: x.date_play <= to_date, games))
        items = request.QUERY_PARAMS.get('item', 10)
        list_result = []
        temp_hole = {}
        temp_holetee = {}
        for game in games:
            game_serializer = GameSerializer(game)
            scores = game.score.all().order_by('hole_id')
            game_serializer.data.update(
                {"golfcourse_name": game.golfcourse.name})
            if scores:
                teetype = scores[0].tee_type
                subgolfcourse = teetype.subgolfcourse

                if subgolfcourse.id not in temp_hole:
                    temp_hole.update({subgolfcourse.id: []})
                    add_new_hole = True
                else:
                    add_new_hole = False

                if teetype.id not in temp_holetee:
                    temp_holetee.update({teetype.id: []})
                    add_new_holetee = True
                else:
                    add_new_holetee = False

                teetype_serializer = {'slope': teetype.slope, 'rating': teetype.rating,
                                      'color': teetype.color, 'subgolfcourse': subgolfcourse.id}
                game_serializer.data.update(teetype_serializer)
                if add_new_hole:
                    holes = subgolfcourse.hole.all().only('par', 'hdcp_index', 'id')
                    for h in holes:
                        temp_hole[subgolfcourse.id].append({'par': h.par, 'hdcp_index': h.hdcp_index, 'id': h.id})
                if add_new_holetee:
                    holetee = teetype.holetee.all().only('yard')
                    for h in holetee:
                        temp_holetee[teetype.id].append(h.yard)
                i = 0
                sum_putt = 0
                for s in game_serializer.data['score']:
                    if s['putt']:
                        sum_putt += s['putt']
                    s.update({'par': temp_hole[subgolfcourse.id][i]['par'],
                              'hdcp_index': temp_hole[subgolfcourse.id][i]['hdcp_index'],
                              'yard': temp_holetee[teetype.id][i]})
                    i += 1
                game_serializer.data.update({'sum_putt': sum_putt})

            list_result.append(game_serializer.data)
        paginator = Paginator(list_result, items)

        page = request.QUERY_PARAMS.get('page')

        try:
            games = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            games = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999),
            # deliver last page of results.
            games = paginator.page(paginator.num_pages)
        serializer = PaginationSerializer(instance=games)
        serializer.data.update(hdcp_avg)
        serializer.data.update(hdus_avg)
        serializer.data.update(handicap_us)
        return Response(serializer.data, status=200)

    def retrieve(self, request, pk=None):
        try:
            game = Game.objects.get(id=pk)
            serializers = GameSerializer(game)
            if serializers.data['score']:
                hole_ids = [s['hole'] for s in serializers.data['score']]
                pars = list(Hole.objects.filter(id__in=hole_ids).values_list('par', flat=True))
                i = 0
                for s in serializers.data['score']:
                    s.update({'par': pars[i]})
                    i += 1
            fields = request.QUERY_PARAMS.get('fields', '')
            fields = set(fields.split(','))
            if 'report' in fields:
                partner_game = Game.objects.filter(group_link=game.group_link).exclude(id=game.id).exclude(is_quit=True)
                if game.event_member.customer:
                    name = game.event_member.customer.name
                    avatar = game.event_member.customer.avatar
                else:
                    name = game.event_member.user.user_profile.display_name
                    avatar = game.event_member.user.user_profile.profile_picture
                serializers.data.update({
                    'name': name,
                    'avatar': avatar
                })
                serializers.data.update({'partner_game': []})
                for g in partner_game:
                    partner_game_serializer = GameSerializer(g)
                    i = 0
                    if g.event_member.customer:
                        name = g.event_member.customer.name
                        avatar = g.event_member.customer.avatar
                    else:
                        name = g.event_member.user.user_profile.display_name
                        avatar = g.event_member.user.user_profile.profile_picture
                    partner_game_serializer.data.update({
                        'name': name,
                        'avatar': avatar
                    })
                    if partner_game_serializer.data['score']:
                        for s in partner_game_serializer.data['score']:
                            s.update({'par': pars[i]})
                            i += 1
                    serializers.data['partner_game'].append(partner_game_serializer.data)
            return Response(serializers.data, status=200)
        except Exception as e:
            return Response(e, status=404)

    def destroy(self, request, pk=None):
        game = Game.objects.only('event_member_id', 'date_play').get(id=pk)
        event_member_id = game.event_member_id
        date_play = game.date_play
        game.delete()
        event_member = EventMember.objects.only('event_id').get(id=event_member_id)
        if event_member.event:
            async_ranking.delay(event_member.event.id, str(date_play))
        members = EventMember.objects.filter(user=event_member.user)
        games = Game.objects.filter(event_member__in=members, is_finish=True, active=True).order_by('-date_play')[:20]
        if len(games) >= 5:
            handicap_differentials = []
            for game in games:
                strokes = list(Score.objects.filter(game_id=game.id).values_list('stroke', flat=True))
                valid = True
                for stroke in strokes:
                    if stroke == 0:
                        valid = False
                        break
                if not valid:
                    continue
                if game.score.count() != 18:
                    continue
                if game.hdc_us and game.score.count() == 18:
                    handicap_differentials.append(game.hdc_us)
            handicap_differentials.sort()
            if not len(handicap_differentials) >= 5:
                event_member.user.user_profile.handicap_us = 'N/A'
                event_member.user.user_profile.save()
                return Response({'status': 200, 'detail': 'OK'}, status=200)
            if handicap_differentials:
                hdcp_index = handicap_index(handicap_differentials)
                event_member.user.user_profile.handicap_us = hdcp_index
                event_member.user.user_profile.save()
        else:
            event_member.user.user_profile.handicap_us = "N/A"
            event_member.user.user_profile.save()

        return Response({'status': 200, 'detail': 'OK'}, status=200)



class GameFlightViewSet(ListOnlyViewSet):
    queryset = GameFlight.objects.all()
    serializer_class = GameFlightSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        flight = request.QUERY_PARAMS.get('flight', None)
        if flight:
            game_flights = GameFlight.objects.filter(flight_id=flight)
            valid = False
            for flight in game_flights:
                if flight.member.user == request.user:
                    valid = True
                    break
            if not valid:
                return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                                 'detail': 'You do not have permission to peform this action'}, status=401)
            serializers = GameFlightSerializer(game_flights)
            return Response(serializers.data, status=200)
        return Response([], status=200)


@api_view(['POST'])
def finish_game(request):
    game_list = request.DATA.get('game_list')
    games = Game.objects.filter(id__in=game_list,  recorder=request.user)
    # disable this by requirement (Harry)
    # if len(game_list) != games.count():
    #    return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
    #                     'detail': 'You do not have permission to peform this action'}, status=401)

    for g in games:
        num_hole = g.golfcourse.number_of_hole if g.golfcourse.number_of_hole <= 18 else 18
        if g.score.count() < num_hole:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'You need to complete all rounds'}, status=400)

    for g in games:
        g.is_finish = True
        g.save()

    return Response({'status': '200', 'code': 'OK',
                     'detail': 'FINISH OK'}, status=200)


@api_view(['POST'])
def cancel_game(request):
    game_list = request.DATA.get('game_list')
    for i in game_list:
        if not Game.objects.filter(id=i, recorder=request.user).exists():
            return Response({'status': '401', 'code': 'E_NOT_PERMISSION',
                             'detail': 'You do not have permission to peform this action'}, status=401)
    Game.objects.filter(id__in=game_list).delete()
    return Response({'status': '200', 'code': 'OK',
                     'detail': 'CANCEL OK'}, status=200)


@api_view(['GET'])
def get_mini_list(request):
    queryset = Game.objects.filter(user=request.user.id)
    return_data = []
    for item in queryset:
        serializer = MiniGameSerializer(item)
        serializer.data.update({"golfcourse_name": item.golfcourse.name})
        return_data.append(serializer.data)
    return Response(return_data, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def compare(request):
    game_id = request.QUERY_PARAMS.get('game_id', '')
    if not game_id:
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)

    game = get_or_none(Game, pk=game_id)
    if game is None:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': code['E_NOT_FOUND']}, status=400)

    if game.object_id is None:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': 'This Game do not have compare'}, status=400)

    list_game = Game.objects.filter(
        content_type=game.content_type_id, object_id=game.object_id)
    if list_game is None:
        return Response({'status': '404', 'code': 'E_NOT_FOUND',
                         'detail': code['E_NOT_FOUND']}, status=400)

    return_list_obj = []

    for ite in list_game:
        if ite.event_member.user:
            user = ite.event_member.user.user_profile.display_name
        else:
            user = ite.event_member.customer.name
        score_list = Score.objects.filter(game=ite.id)
        score_list = list(
            sorted(score_list, key=lambda x: x.hole_id, reverse=False))
        game = {'user': user, 'score': []}
        if score_list is not None:
            for score in score_list:
                score_info = {
                    'hole': score.hole_id, 'par': score.hole.par, 'stroke': score.stroke}
                game['score'].append(score_info)
        return_list_obj.append(game)

    return Response(return_list_obj, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_handicap_index(request):
    members = request.user.event_member.all()
    count = 0
    hdcp_index = ''
    for m in members:
        count += m.game.count()
        if count >= 5:
            hdcp_index = request.user.user_profile.handicap_us
            break
    return Response({'hdcp_index': hdcp_index}, status=200)


class ResultRecordUnderGameViewSet(viewsets.ReadOnlyModelViewSet):
    """ Handle for result record of the game
    """
    queryset = Score.objects.all()
    serializer_class = ScoreSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def get_queryset(self):
        """ Get all friend request to current use
        """
        return Score.objects.filter(game=self.kwargs['game_pk'])


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def cal_aver_par(request):
    game_id = request.QUERY_PARAMS.get('game_id', '')
    if not game_id:
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)

    game = get_or_none(Game, id=game_id)
    if not game:
        return Response({'status': '404', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=404)

    score = Score.objects.filter(game=game_id)
    par3 = 0
    par3_count = 0
    par4 = 0
    par4_count = 0
    par5 = 0
    par5_count = 0
    for ite in score:
        if ite.hole.par == 3:
            par3_count += 1
            par3 += ite.stroke
        elif ite.hole.par == 4:
            par4_count += 1
            par4 += ite.stroke
        elif ite.hole.par == 5:
            par5_count += 1
            par5 += ite.stroke
    if par3_count == 0:
        par3_count = 1
    if par4_count == 0:
        par4_count = 1
    if par5_count == 0:
        par5_count = 1
    return Response({'3': par3 / par3_count, '4': par4 / par4_count, '5': par5 / par5_count}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def score_distribute(request):
    game_id = request.QUERY_PARAMS.get('game_id', '')
    if not game_id:
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)

    game = get_or_none(Game, id=game_id)
    if not game:
        return Response({'status': '404', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=404)

    score = Score.objects.filter(game=game_id)
    ostrich = 0
    condor = 0
    albatross = 0
    eagle = 0
    birdie = 0
    par = 0
    bogey = 0
    double_bogey = 0
    triple_bogey = 0
    quadruple_bogey = 0
    over5 = 0
    over6 = 0

    for ite in score:
        hdc = int(ite.stroke) - int(ite.hole.par)
        if hdc == -5:
            ostrich += 1
        elif hdc == 4:
            condor += 1
        elif hdc == -3:
            albatross += 1
        elif hdc == -2:
            eagle += 1
        elif hdc == -1:
            birdie += 1
        elif hdc == 0:
            par += 1
        elif hdc == 1:
            bogey += 1
        elif hdc == 2:
            double_bogey += 1
        elif hdc == 3:
            triple_bogey += 1
        elif hdc == 4:
            quadruple_bogey += 1
        elif hdc == 5:
            over5 += 1
        elif hdc == 6:
            over6 += 1

    return Response(
        {'ostrich': ostrich, 'condor': condor, 'albatross': albatross, 'eagle': eagle, 'birdie': birdie, 'par': par,
         'bogey': bogey, 'double_bogey': double_bogey, 'triple_bogey': triple_bogey, 'quadruple_bogey': quadruple_bogey,
         'over5': over5, 'over6': over6}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def game_analysis(request, game_id):
    game = Game.objects.filter(id=game_id).first()
    if not game:
        return Response({'status': '404', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': code['E_INVALID_PARAMETER_VALUES']}, status=404)

    score = Score.objects.filter(game=game_id)
    result = calc_game_stat(score)
    prev_games = Game.objects.filter(event_member__user=request.user, date_play__lte=game.date_play, is_finish=True, active=True,
                                     golfcourse__number_of_hole__gte=18).exclude(id=game.id).order_by('-date_play',
                                                                                                      '-time_play')[:5]
    prev_game_stat = []

    for g in prev_games:
        score = Score.objects.filter(game=g.id)
        prev_game_stat.append(calc_game_stat(score))
    compare_last_game(result, prev_game_stat)
    return Response(result, status=200)


def compare_last_game(cur_stat, prev_stat):
    prev_average = {}
    for i, stat in enumerate(prev_stat):
        for key in stat:
            for sub_key in stat[key]:
                if sub_key not in prev_average:
                    prev_average.update({sub_key: 0})
                prev_average[sub_key] += float(stat[key][sub_key]['average'])
                round_score = float(cur_stat[key][sub_key]['average']) - float(prev_average[sub_key] / (i + 1))
                cur_stat[key][sub_key].update({'compare_last_game_' + str(i + 1): round_float(round_score)})


def calc_game_stat(score):
    item = {
        'no_hole': 0,
        'total': 0,
        'average': 0,
        'at_hole': [],
        'compare_last_game_1': 0,
        'compare_last_game_2': 0,
        'compare_last_game_3': 0,
        'compare_last_game_4': 0,
        'compare_last_game_5': 0,
    }
    scoring = {
        'double_par': deepcopy(item),
        'bogey_2': deepcopy(item),
        'bogey_3': deepcopy(item),
        'bogey_4': deepcopy(item),
        'bogey_5': deepcopy(item),
        'bogey': deepcopy(item),
        'par': deepcopy(item),
        'birdie': deepcopy(item),
        'eagle': deepcopy(item),
    }
    score_average = dict(par_3=deepcopy(item),
                         par_4=deepcopy(item),
                         par_5=deepcopy(item),
                         par_all=deepcopy(item),
                         putt=deepcopy(item)
                         )

    gross = 0
    sum_putt = 0
    for ite in score:
        hdc = int(ite.stroke) - int(ite.hole.par)
        gross += int(ite.stroke)
        if ite.putt and ite.putt > 0:
            score_average['putt']['total'] += ite.putt
            score_average['putt']['no_hole'] += 1
            score_average['putt']['at_hole'].append(ite.hole.holeNumber)
            score_average['putt']['average'] = round_float(
                float(score_average['putt']['total'] / score_average['putt']['no_hole']))
        par_key = 'par_' + str(ite.hole.par)
        if par_key in score_average:
            score_average[par_key]['no_hole'] += 1
            score_average[par_key]['total'] += int(ite.stroke)
            score_average[par_key]['at_hole'].append(ite.hole.holeNumber)
        scoring_key = ''
        if hdc == -2:
            scoring_key = 'eagle'
        elif hdc == -1:
            scoring_key = 'birdie'
        elif hdc == 0:
            scoring_key = 'par'
        elif hdc == 1:
            scoring_key = 'bogey'
        elif hdc == 2:
            scoring_key = 'bogey_2'
        elif hdc == 3:
            scoring_key = 'bogey_3'
        elif hdc == 4:
            scoring_key = 'bogey_4'
        else:
            scoring_key = 'bogey_5'

        if hdc == int(ite.hole.par):
            scoring_key = 'double_par'

        if scoring_key:
            scoring[scoring_key]['total'] += int(ite.stroke)
            scoring[scoring_key]['no_hole'] += 1
            scoring[scoring_key]['at_hole'].append(ite.hole.holeNumber)
    for key in score_average:
        if score_average[key]['no_hole'] > 0:
            score_average[key]['average'] = round_float(
                float(score_average[key]['total'] / score_average[key]['no_hole']))

    score_average['par_all']['average'] = score_average['par_all']['total'] = gross
    score_average['par_all']['no_hole'] = len(score)

    for key in scoring:
        if len(score) > 0:
            scoring[key]['average'] = round_float(float(scoring[key]['no_hole'] / len(score)))
    return {'scoring': scoring, 'score_average': score_average}


def round_float(x):
    round_score = "%.2f" % round(x, 2)
    return float(round_score)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def confirm_game(request, game_id):
    game = Game.objects.filter(id=game_id).first()
    if not game:
        return Response({'status': '404', 'detail': 'Not found'}, status=404)
    if game.event_member.user and game.event_member.user == request.user:
        game.active = True
        game.save()
        game.update_hdcp_index()
        ctype = ContentType.objects.get_for_model(Game)
        Notice.objects.filter(content_type=ctype,
                              object_id=game.id,
                              notice_type='G',
                              to_user=request.user).delete()

        # log to activity when user confirm game
        UserActivity.objects.filter(user=request.user,
                                    verb='create_game',
                                    object_id=game.id,
                                    public=False).update(public=True)

        return Response({'status': 1}, status=200)
    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                     'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def quit_game(request, game_id):
    game = Game.objects.filter(Q(event_member__user=request.user) | Q(recorder=request.user))\
            .filter(id=game_id).first()
    if not game:
        return Response({'status': '404', 'detail': 'Not found'}, status=404)
    game.is_quit = True
    game.save(update_fields=['is_quit'])
    return Response({'status': 1}, status=200)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def resume_game(request, game_id):
    game = Game.objects.filter(Q(event_member__user=request.user) | Q(recorder=request.user))\
            .filter(id=game_id).first()
    if not game:
        return Response({'status': '404', 'detail': 'Not found'}, status=404)
    game.is_quit = False
    game.save(update_fields=['is_quit'])
    return Response({'status': 1}, status=200)
