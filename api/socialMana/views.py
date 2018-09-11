import base64
import hmac
import hashlib
import json
import datetime

from django.contrib.contenttypes.models import ContentType
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from rest_framework.pagination import PaginationSerializer
from rest_framework.views import APIView

from core.game.models import Game
from core.post.models import Post
from api.forumMana.serializers import MultiCommentSeri
from api.gameMana.serializers import GameSerializer, BoardGameSerializer
from utils.rest.viewsets import OnlyGetViewSet
from GolfConnect.settings import S3_AWSKEY, S3_SECRET, S3_BUCKET


class leaderboardVs(OnlyGetViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    parser_classes = (JSONParser, FormParser,)
    paginate_by = 10

    def list(self, request):
        invite_ctt = ContentType.objects.get_by_natural_key(
            'invitation', 'invitation')
        checkin_ctt = ContentType.objects.get_by_natural_key(
            'checkin', 'checkin')
        # bat dau get list game dung 1 minh
        game_alone_list = Game.objects.filter(
            content_type_id=None)
        game_invite_list = Game.objects.filter(
            content_type_id=invite_ctt.id).distinct('object_id')
        game_check_list = Game.objects.filter(
            content_type_id=checkin_ctt.id).distinct('object_id')
        count = 0
        return_data = []
        for game_alone in game_alone_list:
            game_alone_seri = BoardGameSerializer(game_alone)
            return_data.append(
                {'game': [game_alone_seri.data], 'date_create': game_alone.date_create, 'type': 'G'})
        # xong list game dung 1 minh
        # group nhung thang nhom invitation
        for game_alone in game_invite_list:
            game = Game.objects.filter(
                content_type_id=invite_ctt.id, object_id=game_alone.object_id)
            game_alone_seri = BoardGameSerializer(game, many=True)
            return_data.append(
                {'game': game_alone_seri.data, 'date_create': game_alone.date_create, 'type': 'G'})
        # ket thuc group invite
        # group nhung thang nhom checkin
        for game_alone in game_check_list:
            game = Game.objects.filter(
                content_type_id=checkin_ctt.id, object_id=game_alone.object_id)
            game_alone_seri = BoardGameSerializer(game, many=True)

            return_data.append(
                {'game': game_alone_seri.data, 'date_create': game_alone.date_create, 'type': 'G'})
        # ket thuc checkin
        # get danh sach post
        post_list = Post.objects.filter(content_type_id=None)
        for post in post_list:
            post_seri = MultiCommentSeri(post)
            if post.date_modified == None:
                date = post.date_creation
            else:
                date = post.date_modified
            game = []
            game.append({'post': post_seri.data})
            return_data.append(
                {'game': game, 'date_create': date, 'type': 'P'})
        # ket thuc post
        # sap xep theo thu tu thoi gian dc tao ra
        return_data = list(
            sorted(return_data, key=lambda x: x['date_create'], reverse=True))
        # ket thuc sap xep

        # Cho Nay la phan trang thoi
        items = request.QUERY_PARAMS.get('item', 50)
        paginator = Paginator(return_data, items)

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
        return Response(serializer.data, status=200)


class S3Policy(APIView):
    permission_classes = (IsAuthenticated, )

    @staticmethod
    def get(request):
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(minutes=now.minute % 5 + 5, seconds=now.second,
                                              microseconds=now.microsecond)
        policy = {
            'expiration': expiration.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'conditions': [
                ['starts-with', '$key', ""],
                {'bucket': S3_BUCKET},
                {'acl': 'public-read'},
                ['starts-with', '$Content-Type', ""],
                ["content-length-range", 0, 52428800],
                {'success_action_status': '201'}
            ]}
        policy_encoded = base64.b64encode(json.dumps(policy).encode())
        signature = base64.b64encode(
            hmac.new(key=S3_SECRET.encode(), msg=policy_encoded, digestmod=hashlib.sha1).digest())
        return Response({'policy': policy_encoded.decode(), 'signature': signature.decode(), 'bucket': S3_BUCKET,
                         'awsKey': S3_AWSKEY})
