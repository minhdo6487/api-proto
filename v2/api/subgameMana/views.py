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
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PaginationSerializer
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.customer.models import Customer
from core.game.models import Game, Score, EventMember, GameFlight
from core.golfcourse.models import GroupOfEvent, GolfCourseEvent, Hole, SubGolfCourse, GolfCourse, HoleTee, Hole, \
    TeeType
from api.gameMana.serializers import GameSerializer, ScoreSerializer, MiniGameSerializer, GameFlightSerializer
from api.golfcourseMana.serializers import GolfCourseListSerializer

from v2.api.subgameMana.serializers import SubGolfCourseSerializer

from utils.rest.permissions import UserIsOwnerOrReadOnly
from utils.django.models import get_or_none
from utils.rest.code import code
from utils.rest.viewsets import CreateOnlyViewSet, ListOnlyViewSet
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB
from api.golfcourseeventMana.tasks import async_ranking
from utils.rest.handicap import handicap_index
from django.db.models import Q

redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


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


"""
1. create: same with 18 hole
    request: "method POST" 
        golfcoures_id
        game_id

        sub_golfcourse (add, can be empty "key: value"): id of sub_golfcourse
        continue_sub_game
            ---
            if (continue_sub_game is exist (true) and sub_golfcourse not same with sub_golfcouse store in db)
                play to finish and calulate handicap_us
            else
                just store 
            ---

        score
        is_finish: True
        active: True
    response
        same as normal
        handicap_us : N/A (b/c still not finish)

        sub_golfcourse (add, can be empty "key: value")
        continue_sub_game
            ---
            if (continue_sub_game is exist (true) and sub_golfcourse not same with sub_golfcouse store in db)
                play to finish and calulate handicap_us
            else
                just store 
            ---

        only finish first sub: True (finish 9 hole and stop)

2. list/<pk>
3. recommnend sub for play (only for subgame finish 9 hole)
    method GET
    user (token) is required
    if has subgame only 9 hole
"""


class GameViewSet_v2(viewsets.ModelViewSet):
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

            """
                Minh add
            """

            d_score = list(filter(lambda x: 'stroke' in x and x['stroke'], d['score']))
            sub_gcid_second = list(Hole.objects.filter(pk__in=[i["hole"] for i in d_score]).values("subgolfcourse"))[0][
                "subgolfcourse"]

            fr_hole = min([item["hole"] for item in d_score])
            to_hole = max([item["hole"] for item in d_score])
            second_fr_to_hole = "{} --- {}".format(fr_hole, to_hole)

            """
                in this case we have:
                    golfcourse id 
                    subgolfcourse_id
                    tee_type do not change
            """
            # game_played = Game.objects.filter(golfcourse=d["golfcourse"]).values("id")

            """get from game id for continue calculate handicap_us_"""
            # first_part_score = Game.objects.get(pk = d["first_part"])
            if d["continue_sub_game"] and d["first_part"]:
                first_part_score = list(
                    Score.objects.filter(game_id=d["first_part"]).values('hole_id', 'stroke', 'tee_type_id'))

                first_tee_type = first_part_score[0]["tee_type_id"]
                first_tt = TeeType.objects.get(pk=first_tee_type)
                first_slope = TeeType.objects.get(pk=first_tee_type).slope
                first_rating = TeeType.objects.get(pk=first_tee_type).rating
                first_name = TeeType.objects.get(pk=first_tee_type).name
                first_subgc = SubGolfCourse.objects.filter(pk=first_tt.subgolfcourse_id).values_list("id",
                                                                                                     flat=True).first()

                first_part_hole = (Score.objects.filter(game_id=d["first_part"]).values('hole_id'))
                fr_hole = min([item["hole_id"] for item in first_part_hole])
                to_hole = max([item["hole_id"] for item in first_part_hole])
                first_fr_to_hole = "{} --- {}".format(fr_hole, to_hole)
                """
                    handle exception for different hole, or tee_type
                """
                second_tee_type = [int(item["tee_type"]) for item in d_score][0]
                second_slope = TeeType.objects.get(pk=second_tee_type).slope
                second_rating = TeeType.objects.get(pk=second_tee_type).rating
                second_name = TeeType.objects.get(pk=second_tee_type).name
                second_subgc = sub_gcid_second

                print ("first color {} --- second color {}".format(first_name, second_name))
                print ("first slope {} --- second slope {}".format(first_slope, second_slope))
                print ("first rating {} --- second rating {}".format(first_rating, second_rating))

                if [int(item["hole"]) for item in d_score] == [item["hole_id"] for item in first_part_hole]:
                    return Response({"status": "not allow choose same hole id"}, status=400)
                elif second_name != first_name or second_slope != first_slope or second_rating != first_rating:
                    return Response({"status": "have to choose same tee_type, same slope, same rating"}, status=400)

                sub_gcid_first = list(Hole.objects.filter(pk__in=first_part_hole).values("subgolfcourse"))[0][
                    "subgolfcourse"]

                for item in first_part_score:
                    item.update({"hole": item["hole_id"]})
                    item.update({"tee_type": item["tee_type_id"]})

                    del item["tee_type_id"]
                    del item["hole_id"]

            else:
                first_part_score = []
                sub_gcid_first = sub_gcid_second
                first_fr_to_hole = second_fr_to_hole

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

        """
        minh add
        """
        d["score"] = list(first_part_score) + d["score"]

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
                            # game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
                            game.calculate_handicap_v2(d["first_part"], normal=True, hdcus=True, system36=True,
                                                       hdc_net=True)
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
                            # game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
                            game.calculate_handicap_v2(d["first_part"], normal=True, hdcus=True, system36=True,
                                                       hdc_net=True)
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

                for s in score:
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
                # game.calculate_handicap(normal=True, hdcus=True, system36=True, hdc_net=True)
                game.calculate_handicap_v2(d["first_part"], normal=True, hdcus=True, system36=True, hdc_net=True)
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
        if first_part_score:
            ### remove first game

            del_game = Game.objects.get(id=d["first_part"])
            del_game.delete()

            return Response(
                {'status': '200',
                 'detail': {'saved_member': saved_member,
                            'saved_game': saved_game,
                            'not_register_member': not_register_member,
                            'event': first_event_id,
                            'first_sub_gc': sub_gcid_first,
                            'first_fr_to_hole': first_fr_to_hole,
                            'second_sub_gc': sub_gcid_second,
                            'second_fr_to_hole': second_fr_to_hole,
                            'is_calculate': True},
                 'code': 'OK'},
                status=200)
        else:
            return Response(
                {'status': '200',
                 'detail': {'saved_member': saved_member,
                            'saved_game': saved_game,
                            'not_register_member': not_register_member,
                            'event': first_event_id,
                            'first_sub_gc': sub_gcid_first,
                            'first_fr_to_hole': first_fr_to_hole,
                            'is_calculate': False},
                 'code': 'OK'},
                status=200)

    # def partial_update(self, request, pk=None):
    #     temp = super(GameViewSet_v2, self).partial_update(self.request, pk)
    #     if temp.status_code == 200:
    #         game = Game.objects.get(id=pk)
    #         game.calculate_handicap_v2(first_part="",normal=True, hdcus=True, system36=True, hdc_net=True)
    #         game.update_hdcp_index()
    #         serializer = self.serializer_class(game)
    #         return Response(serializer.data, status=200)
    #     return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
    #                      'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)

    def partial_update(self, request, pk=None):
        # temp = super(GameViewSet_v2, self).partial_update(self.request, pk)
        # if temp.status_code == 200:
        req_js = request.DATA
        sub_scores_update = req_js.get('score') if req_js.get('score') else None
        if sub_scores_update:
            for item in sub_scores_update:
                # optional
                # ob = item.get('ob') if item.get('ob') else ""
                # putt = item.get('putt') if item.get('putt') else ""
                # chip = item.get('chip') if item.get('chip') else ""
                # bunker = item.get('bunker') if item.get('bunker') else ""
                # water = item.get('water') if item.get('water') else ""
                # fairway = item.get('fairway') if item.get('fairway') else False
                # on_green = item.get('on_green') if item.get('on_green') else False

                game = Game.objects.get(id=pk)
                score = game.score

                results = score.filter(hole_id=int(item.get('hole')))
                if not results:
                    return Response({'note': 'missing hole can\'t not update'}, status=400)
                else:
                    results.update(
                        stroke=item.get('stroke'),
                        # optional
                        # ob=ob,
                        # putt=putt,
                        # chip=chip,
                        # bunker=bunker,
                        # water=water,
                        # fairway=fairway,
                        # on_green=on_green
                    )

            game.calculate_handicap_v2(first_part=req_js.get('first_part'), normal=True, hdcus=True, system36=True,
                                       hdc_net=True)
            game.update_hdcp_index()
            serializer = self.serializer_class(game)
            return Response(serializer.data, status=200)
        else:
            return Response({"note": "miss score for update"}, status=400)
        # return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
        #                  'detail': code['E_INVALID_PARAMETER_VALUES']}, status=400)

    def list(self, request):
        """ Use this api like this: api/game/?user=3&from_date=2014-09-20&to_date=2014-09-21"""
        if request.user.is_anonymous():
            return Response({"status": 400, "detail": "User is anonumous, don not have user_profile infomation"}, status=400)

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
        # hdcp_avg = games.filter(is_finish=True, golfcourse__number_of_hole__gte=18).aggregate(Avg('hdcp'))
        hdcp_avg = {'hdcp__avg': 0}
        # hdus_avg = games.filter(is_finish=True, golfcourse__number_of_hole__gte=18).aggregate(Avg('hdc_36'))
        hdus_avg = {'hdc_36__avg': 0}
        # handicap_us
        handicap_us = {'handicap_us': request.user.user_profile.handicap_us or 'N/A'}
        avg_score = {'average-score': request.user.user_profile.avg_score}
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
                    try:
                        s.update({'par': temp_hole[subgolfcourse.id][i]['par'],
                                  'hdcp_index': temp_hole[subgolfcourse.id][i]['hdcp_index'],
                                  'yard': temp_holetee[teetype.id][i]})
                    except Exception as e:
                        pass
                    i += 1
                game_serializer.data.update({'sum_putt': sum_putt})

                """
                Minh add round analisis
                """
                strokes = list(Score.objects.filter(game_id=game.id).values_list('stroke', flat=True))
                valid = True
                count = 1
                for stroke in strokes:
                    # print ("here", stroke)
                    count += 1
                    if stroke == 0:
                        valid = False
                        break
                if not valid:
                    continue
                # if game.score.count() != 18:
                #     continue
                if game.hdc_us and game.score.count() == 18 and game.is_finish:
                    game_serializer.data.update(
                        {
                            # 'handicap_cal': True,
                            'handicap_flag': True,
                            'game_id': game.id,
                            'handicap_diff': game.hdc_us
                        }
                    )
                    data_cal_sorted = sorted(game_serializer.data['score'], key=lambda k: k['hole'])
                    game_serializer.data.update({'score': data_cal_sorted})
                else:
                    game_serializer.data.update(
                        {
                            'handicap_flag': False,
                            'handicap_cal': False
                        }
                    )
                    data_cal_sorted = sorted(game_serializer.data['score'], key=lambda k: k['hole'])
                    game_serializer.data.update({'score': data_cal_sorted})

            # list_result.append(game_serializer.data)
            list_result.append(game_serializer.data)

        list_handicap = [item for item in list_result if item['handicap_flag'] == True]
        data_sorted = sorted(list_handicap, key=lambda k: k['handicap_diff'])
        nums = len(data_sorted)

        if 5 <= nums <= 6:
            change_status = data_sorted[0]
        elif 7 <= nums <= 8:
            change_status = data_sorted[0:2]
        elif 9 <= nums <= 10:
            change_status = data_sorted[0:3]
        elif 11 <= nums <= 12:
            change_status = data_sorted[0:4]
        elif 13 <= nums <= 14:
            change_status = data_sorted[0:5]
        elif 15 <= nums <= 16:
            change_status = data_sorted[0:6]
        elif nums == 17:
            change_status = data_sorted[0:7]
        elif nums == 18:
            change_status = data_sorted[0:8]
        elif nums == 19:
            change_status = data_sorted[0:9]
        else:
            change_status = data_sorted[0:10]

        if len(list_handicap) >= 5 and not request.QUERY_PARAMS.get('is_finish'):
            for j in list_result:
                try:
                    if change_status['id'] == j['id'] and j['is_finish'] == True:
                        j.update({'handicap_cal': True})
                except:
                    for i in change_status:
                        if i['id'] == j['id'] and j['is_finish'] == True:
                            j.update({'handicap_call': True})

        elif request.QUERY_PARAMS.get('is_finish'):
            for j in list_result:
                # for i in change_status:
                try:
                    if j['id'] == change_status['id']:
                        j.update({'handicap_cal': True})
                except:
                    for i in change_status:
                        if i['id'] == j['id'] and j['is_finish'] == True:
                            j.update({'handicap_call': True})

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
        serializer.data.update(avg_score)
        """
            try get game calculate hdcp
        """

        games = Game.objects.filter(event_member__user=request.user, is_finish=True, active=True).order_by(
            '-date_play')[:20]

        # if len(games) >= 5:
        #     handicap_differentials = []
        #     gameIds_4_hdcpus = []
        #     json_data = []
        #     for game in games:
        #
        #         strokes = list(Score.objects.filter(game_id=game.id).values_list('stroke', flat=True))
        #         valid = True
        #         count = 1
        #         for stroke in strokes:
        #             count += 1
        #             if stroke == 0:
        #                 valid = False
        #                 break
        #         if not valid:
        #             continue
        #         if game.score.count() != 18:
        #             continue
        #         if game.hdc_us and game.score.count() == 18:
        #             handicap_differentials.append(game.hdc_us)
        #             gameIds_4_hdcpus.append(game.id)
        #
        #             json_data.append(
        #                 {"handicap_diff": game.hdc_us, "game_id": game.id}
        #             )
        #
        #     data_sorted = sorted(json_data, key=lambda k: k['handicap_diff'])
        #
        #     # handicap_differentials.sort()
        #     # print ("hdcp_us: {} gameIDs: {}".format(handicap_differentials, gameIds_4_hdcpus))
        #     serializer.data.update({"handicap_cal": data_sorted})
        ##########################################

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


@api_view(["GET"])
@permission_classes((AllowAny,))
def find_next_subgame(request, golfcourse_id):
    queryset = SubGolfCourse.objects.all()
    serializer_class = SubGolfCourseSerializer
    parser_classes = (JSONParser, FormParser,)

    games = Game.objects.filter(event_member__user=request.user)

    result = []
    gc_id = []
    list_result = []
    temp_hole = {}
    temp_holetee = {}

    gc = get_or_none(GolfCourse, pk=golfcourse_id)
    if not gc:
        return Response({'detail': 'This golfcourse doesn\'t exist'}, status=400)

    sub_gc = SubGolfCourse.objects.filter(golfcourse=golfcourse_id).values("id", "teetype", "name")

    new_sub_gc = []
    for i in list(sub_gc):
        list_hole = [i["id"] for i in Hole.objects.filter(subgolfcourse=i["id"]).values("id")]
        if len(list_hole) == 9:
            new_sub_gc.append({
                "sub_id": i['id'],
                "sub_gc_name": i['name'],
                "teetype": i['teetype'],
                "list_hole": list_hole
            })

    if not Game.objects.filter(event_member__user=request.user, golfcourse=gc):
        return Response({'note': 'User doesn\'t play any game of this golfcourse', 'subgolfcourse_set': new_sub_gc},
                        status=200)

    for i in list(sub_gc):
        list_hole = [i["id"] for i in Hole.objects.filter(subgolfcourse=i["id"]).values("id")]
        if len(list_hole) == 9:
            i.update({
                "sub_id": i['id'],
                "sub_gc_name": i['name'],
                "teetype": i['teetype'],
                "list_hole": list_hole
            })
        # i.update({"list_hole": list_hole})

    for game in games:
        game_serializer = GameSerializer(game)
        scores = game.score.all().order_by('hole_id')
        if len(scores) == 9 and str(game.golfcourse_id) == str(golfcourse_id):
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
                                      'color': teetype.color, 'subgolfcourse': subgolfcourse.id,
                                      'sub_reccomend': sub_gc}
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

    gc = SubGolfCourse.objects.filter(golfcourse=golfcourse_id)
    ser = SubGolfCourseSerializer(gc)

    tmp_ser = []
    for i in ser.data:
        if i['number_of_hole'] == 9:
            tmp_ser.append(i)

    list_result.append({'advance_info': tmp_ser})

    if not list_result:
        return Response({"note": "don\'t have any first part sub with 9 hole or not same goflcourse",
                         'subgolfcourse_set': new_sub_gc}, status=400)

    # return Response(list_result, status=200)
    return Response(tmp_ser, status=200)


'''

    queryset = SubGolfCourse.objects.all()
    serializer_class = SubGolfCourseSerializer
    parser_classes = (JSONParser, FormParser,)

'''


# class SubGolfCourseUnderCourseViewSet(viewsets.ModelViewSet):
@api_view(["GET"])
@permission_classes((AllowAny,))
def find_new_sub(request, golfcourse_id=None):
    """ Viewset handle for requesting sub course of specific golfcourse information
    """
    queryset = SubGolfCourse.objects.all()
    serializer_class = SubGolfCourseSerializer
    parser_classes = (JSONParser, FormParser,)

    gc = SubGolfCourse.objects.filter(golfcourse=golfcourse_id)
    ser = SubGolfCourseSerializer(gc)

    tmp_ser = []
    for i in list(ser.data):

        if i['number_of_hole'] == 9:
            tmp_ser.append(i)
    data_sorted = sorted(tmp_ser, key=lambda k: k['name'])
    return Response(data_sorted, status=200)

    # permission_classes = (IsAuthenticated, UserIsOwnerOrReadOnly,)

    def get_queryset(self):
        # return SubGolfCourse.objects.filter(golfcourse=self.kwargs['golfcourse_pk'])
        return SubGolfCourse.objects.filter(golfcourse=golfcourse_id)

    def initial(self, request, *args, **kwargs):
        # logging.debug(request.TYPE)
        if request.method == 'POST':
            request.DATA['golfcourse'] = kwargs['golfcourse_pk']
        super().initial(request, *args, **kwargs)


@api_view(["POST", "GET"])
@permission_classes((IsAuthenticated,))
def split_sub(request, golfcourse_id=None):
    if request.method == "POST":
        req_type = request.DATA
        """
            should handle exception
        """
        gc = GolfCourse.objects.get(pk=req_type.get('gc'))

        sub_gc = SubGolfCourse.objects.get(pk=req_type.get('sub_gc'))
        hole_list = Hole.objects.filter(subgolfcourse=sub_gc).values_list('id', flat=True)

        teetype_list = list(
            TeeType.objects.filter(subgolfcourse=sub_gc).values('id', 'name', 'color', 'slope', 'rating'))

        for item in range(int(len(hole_list) / 9)):
            st = item * 9 + 1
            en = item * 9 + 9
            ### int to character ###
            new_sub_name = sub_gc.name + "_" + str(st) + '-' + str(en)
            ########################

            s = SubGolfCourse.objects.create(name=new_sub_name, golfcourse=gc,
                                             number_of_hole=9)

            split_hole_list = [hole_list[i] for i in range(st - 1, en, 1)]

            count_index = 0
            for hole_index in split_hole_list:
                h = Hole.objects.get(pk=hole_index)
                Hole.objects.create(subgolfcourse=s, holeNumber=int(count_index + 1),
                                    par=h.par,
                                    hdcp_index=h.hdcp_index,
                                    lat=h.lat,
                                    lng=h.lng)

                count_index += 1

            for teetype in teetype_list:
                t = TeeType.objects.create(subgolfcourse=s, name=teetype['name'], color=teetype['color'],
                                           slope=teetype['slope'], rating=teetype['rating'])

                for i in range(0, s.number_of_hole):
                    h = Hole.objects.get(subgolfcourse=s, holeNumber=int(i + 1))
                    yard = HoleTee.objects.filter(hole_id=split_hole_list[i], tee_type_id=teetype['id']).values_list(
                        'yard', flat=True).first()
                    HoleTee.objects.create(tee_type=t, yard=yard, hole=h)
        return Response({"split_sub": "done", "body": req_type}, status=200)


class GameViewSetCal_v2(viewsets.ModelViewSet):
    """ Handle for games
    """
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request):
        """ Use this api like this: api/game/?user=3&from_date=2014-09-20&to_date=2014-09-21"""
        recent = request.QUERY_PARAMS.get('recent', '')

        hdcp_cal = request.QUERY_PARAMS.get('handicap_cal', '')
        is_finish = request.QUERY_PARAMS.get('is_finish', '')
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
        # hdcp_avg = games.filter(is_finish=True, golfcourse__number_of_hole__gte=18).aggregate(Avg('hdcp'))
        hdcp_avg = {'hdcp__avg': 0}
        # hdus_avg = games.filter(is_finish=True, golfcourse__number_of_hole__gte=18).aggregate(Avg('hdc_36'))
        hdus_avg = {'hdc_36__avg': 0}
        # handicap_us
        handicap_us = {'handicap_us': request.user.user_profile.handicap_us or 'N/A'}
        avg_score = {'average-score': request.user.user_profile.avg_score}
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
                    try:
                        s.update({'par': temp_hole[subgolfcourse.id][i]['par'],
                                  'hdcp_index': temp_hole[subgolfcourse.id][i]['hdcp_index'],
                                  'yard': temp_holetee[teetype.id][i]})
                    except Exception as e:
                        pass
                    i += 1
                game_serializer.data.update({'sum_putt': sum_putt})

                """
                Minh add round analisis
                """
                strokes = list(Score.objects.filter(game_id=game.id).values_list('stroke', flat=True))
                valid = True
                count = 1
                for stroke in strokes:
                    # print ("here", stroke)
                    count += 1
                    if stroke == 0:
                        valid = False
                        break
                if not valid:
                    continue
                # if game.score.count() != 18:
                #     continue
                if game.hdc_us and game.score.count() == 18 and game.is_finish:
                    game_serializer.data.update(
                        {
                            'handicap_cal': False,
                            'game_id': game.id,
                            'handicap_diff': game.hdc_us,
                            'handicap_flag': True,
                        }
                    )
                    data_cal_sorted = sorted(game_serializer.data['score'], key=lambda k: k['hole'])
                    game_serializer.data.update({'score': data_cal_sorted})
                    list_result.append(game_serializer.data)
                else:
                    game_serializer.data.update(
                        {
                            'handicap_cal': False,
                            'handicap_flag': False,
                        }
                    )

        list_handicap = [item for item in list_result if item['handicap_flag'] == True]
        data_sorted = sorted(list_handicap, key=lambda k: k['handicap_diff'])
        nums = len(data_sorted)

        if 5 <= nums <= 6:
            change_status = data_sorted[0]
        elif 7 <= nums <= 8:
            change_status = data_sorted[0:2]
        elif 9 <= nums <= 10:
            change_status = data_sorted[0:3]
        elif 11 <= nums <= 12:
            change_status = data_sorted[0:4]
        elif 13 <= nums <= 14:
            change_status = data_sorted[0:5]
        elif 15 <= nums <= 16:
            change_status = data_sorted[0:6]
        elif nums == 17:
            change_status = data_sorted[0:7]
        elif nums == 18:
            change_status = data_sorted[0:8]
        elif nums == 19:
            change_status = data_sorted[0:9]
        else:
            change_status = data_sorted[0:10]

        if len(list_handicap) >= 5:
            for j in list_result:
                # for i in change_status:
                try:
                    if change_status['id'] == j['id'] and j['is_finish'] == True:
                        j.update({'handicap_cal': True})
                    else:
                        j.update({'handicap_cal': False})
                except Exception as e:
                    # print (e)
                    for i in change_status:
                        if i['id'] == j['id']:
                            j.update({'handicap_cal': True})


        data_sorted = sorted(list_result, key=lambda k: k['handicap_diff'])
        if hdcp_cal:
            try:
                return Response(data_sorted[int(hdcp_cal)], status=200)
            except IndexError:
                return Response({'note': 'out of index'}, status=400)

        return Response(data_sorted[:10], status=200)
        # paginator = Paginator(list_result, items)
        #
        # page = request.QUERY_PARAMS.get('page')
        #
        # try:
        #     games = paginator.page(page)
        # except PageNotAnInteger:
        #     # If page is not an integer, deliver first page.
        #     games = paginator.page(1)
        # except EmptyPage:
        #     # If page is out of range (e.g. 9999),
        #     # deliver last page of results.
        #     games = paginator.page(paginator.num_pages)
        # serializer = PaginationSerializer(instance=games)
        # serializer.data.update(hdcp_avg)
        # serializer.data.update(hdus_avg)
        # serializer.data.update(handicap_us)
        # serializer.data.update(avg_score)
        #
        # return Response(serializer.data, status=200)