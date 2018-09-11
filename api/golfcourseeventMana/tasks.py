import datetime
import json

from rest_framework.utils import encoders
import redis
from celery import shared_task

from api.gameMana.serializers import EventMemberSerializer, GameSerializer
from api.golfcourseeventMana.serializers import GolfCourseEventSerializer
from core.game.models import EventMember
from core.golfcourse.models import TeeType, Hole, GolfCourseEvent
from core.realtime.models import TimeStamp
from GolfConnect.settings import REDIS_HOST, REDIS_PORT, REDIS_DB


redis_server = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
__author__ = 'toantran'
HDCP_SYSTEM = {'net': 'hdc_net',
               'system36': 'hdc_36', 'hdcus': 'hdc_us', 'callaway': 'hdc_callaway', 'stable_ford': 'hdc_stable_ford',
               'peoria': 'hdc_peoria', 'db_peoria': 'hdc_peoria'}
SCRAMBLE = 'scramble'


@shared_task
def async_ranking(event_id, date, group_by=None):
    try:
        results = {}
        event = GolfCourseEvent.objects.get(id=event_id)
        serializers = GolfCourseEventSerializer(event)
        results.update(serializers.data)
        # results['group'] = list(sorted(results['group'], key=lambda x: x.from_index))
        channel = 'event-' + str(serializers.data['id']) + '-' + str(date)
        ts, created = TimeStamp.objects.get_or_create(channel=channel)
        results.update({'ts': ts.time.timestamp()})
        members = EventMember.objects.filter(event=event)
        serializers = EventMemberSerializer(members)
        register_members = list(filter(lambda x: x['is_active'] is True, serializers.data))
        results.update({'members': serializers.data,
                        'register_members':register_members})
        i = 0
        cal = HDCP_SYSTEM[event.calculation]
        tee_type_checker = {}
        hole_checker = {}
        subgolcourse_id = None
        pars = []
        for member in members:
            games = member.game.filter(date_play=datetime.datetime.strptime(date, '%Y-%m-%d').date())[:1]
            if games:
                serializers = GameSerializer(games[0])
                if serializers.data['score']:
                    if serializers.data['score'][0]['tee_type'] not in tee_type_checker:
                        tt = TeeType.objects.only('id', 'subgolfcourse_id', 'color').get(
                            id=serializers.data['score'][0]['tee_type'])
                        tee_type = {
                            'color': tt.color,
                            'id': tt.id,
                            'subgolfcourse': tt.subgolfcourse_id
                        }
                        if not subgolcourse_id:
                            subgolcourse_id = tt.subgolfcourse_id
                            results.update({'subgolfcourse': subgolcourse_id})
                        if tt.subgolfcourse_id not in hole_checker:
                            hole_ids = Hole.objects.filter(subgolfcourse_id=tt.subgolfcourse_id).values_list(
                                'id', 'par', 'holeNumber').order_by(
                                'holeNumber')
                            hole_checker.update({tt.subgolfcourse_id: hole_ids})
                        tee_type_checker.update({serializers.data['score'][0]['tee_type']: tee_type})
                    j = 0
                    temp_score = serializers.data['score'].copy()
                    maxj = len(temp_score)
                    for k, h in enumerate(hole_checker[subgolcourse_id]):
                        if h[0] != temp_score[j]['hole']:
                            serializers.data['score'].insert(k, {
                                'hole': h[0],
                                'tee_type': tt.id,
                                'stroke': 0,
                                'game': serializers.data['id'],
                                'par': h[1],
                                'holeNumber': h[2],
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
                # else:
                #     results['members'][i]['handicap'] = serializers.data['handicap']
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

        for m in results['members']:
            front_nine = 0
            back_nine = 0
            m.update({'thru': 0, 'gross': 0, 'net': '', 'front_nine': 0, 'back_nine': 0,
                      'hole_18': 0, 'rank_change': 0})
            if 'game' in m and m['game']['score']:
                for j in range(0, len(m['game']['score'])):
                    try:
                        if j < 9:
                            front_nine += m['game']['score'][j]['stroke']
                        else:
                            back_nine += m['game']['score'][j]['stroke']
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
                          'net': m['game'][cal], 'front_nine': front_nine, 'back_nine': back_nine}
                )

        member_has_game = list(
            filter(lambda x: 'game' in x and x['game'] and x['game']['score'], results['members']))
        member_no_game = list(
            filter(lambda x: not ('game' in x and x['game'] and x['game']['score']), results['members']))
        if event.event_type == 'GE':
            if event.calculation == 'system36':
                sort_member = sorted(member_has_game,
                                     key=lambda m: (m['net'], m['left_thru'],
                                          m['handicap'], m['back_nine'], m['front_nine'], tuple(x['stroke'] for x in reversed(m['game']['score']))))
            else:
                sort_member = sorted(member_has_game,
                                     key=lambda m: (m['net'], m['left_thru'], m['back_nine'], m['front_nine'],
                                                    tuple(x['stroke'] for x in reversed(m['game']['score']))))
        else:
            sort_member = sorted(member_has_game, key=lambda m: (m['net'], m['left_thru']))
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
                if sort_member[i]['net'] > sort_member[i - 1]['net']:
                    rank = rank_temp
                else:
                    if event.event_type == 'GE':
                        if sort_member[i]['handicap'] and sort_member[i - 1]['handicap'] and sort_member[i]['handicap'] > sort_member[i - 1]['handicap']:
                            rank = rank_temp
                        elif sort_member[i]['back_nine'] > sort_member[i - 1]['back_nine']:
                            rank = rank_temp
                            sort_member[i].update({'count_back': 'Back-9: ' + str(sort_member[i]['back_nine']) })
                            sort_member[i - 1].update({'count_back': 'Back-9: ' + str(sort_member[i-1]['back_nine'])})
                        elif sort_member[i]['front_nine'] > sort_member[i - 1]['front_nine']:
                            rank = rank_temp
                            sort_member[i].update({'count_back': 'Front-9: ' + str(sort_member[i]['front_nine']) })
                            sort_member[i - 1].update({'count_back': 'Front-9: ' + str(sort_member[i-1]['front_nine'])})
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
        channel = 'event-' + str(event.id) + '-' + str(date)
        redis_server.publish(channel, results)
        redis_server.set(channel, results)
        return True
    except Exception as e:
        print(e)
        return False