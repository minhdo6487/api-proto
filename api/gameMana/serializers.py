from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from api.forumMana.serializers import MultiCommentSeri
from core.game.models import Game, Score, EventMember, GameFlight
from core.post.models import Post
from utils.django.models import get_or_none


class EventMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMember
        # exclude = ('id',)

    def to_native(self, obj):
        if obj:
            serializers = super(EventMemberSerializer, self).to_native(obj)
            if obj.user:
                serializers.update({'name': obj.user.user_profile.display_name,
                                    'handicap': obj.user.user_profile.handicap_us,
                                    'email': obj.user.email,
                                    'avatar': obj.user.user_profile.profile_picture})
            elif obj.customer:
                serializers.update({'name': obj.customer.name,
                                    'handicap': obj.customer.handicap,
                                    'email': obj.customer.email,
                                    'avatar': obj.customer.avatar})
            if obj.group:
                serializers.update({'group_name': obj.group.name})

            return serializers


class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ('id', 'game', 'hole', 'tee_type', 'stroke',
                  'ob', 'putt', 'chip', 'bunker', 'water', 'fairway', 'on_green')

    def to_native(self, obj):
        if obj:
            serializers = super(ScoreSerializer, self).to_native(obj)
            if int(serializers['stroke']) < 0:
                serializers['stroke'] = 'x'

            return serializers


class GameSerializer(serializers.ModelSerializer):
    score = ScoreSerializer(many=True, required=True, source='score')
    class Meta:
        model = Game
        fields = (
            'id', 'golfcourse', 'date_play', 'time_play', 'bag_number', 'hdc_36', 'handicap', 'handicap_36', 'hdc_net',
            'is_finish','is_quit',
            'hdcp', 'gross_score', 'active', 'adj', 'hdc_us', 'score_card', 'content_type', 'object_id', 'score',
            'recorder', 'group_link', 'event_member')

    def to_native(self, obj):
        if obj:
            serializers = super(GameSerializer, self).to_native(obj)
            if serializers['score']:
                putts = [x['putt'] for x in serializers['score'] if x['putt']]
                sum_putt = sum(putts)
                serializers.update({'sum_putt': sum_putt})
            del serializers['group_link']
            del serializers['recorder']
            del serializers['content_type']
            del serializers['object_id']
            del serializers['event_member']
            return serializers


class MiniGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('id', 'golfcourse', 'date_play', 'time_play', 'hdc_36',
                  'hdcp', 'gross_score', 'hdc_us')


class BoardGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('id', 'user', 'golfcourse', 'date_play', 'gross_score')

    def to_native(self, obj):
        if obj is not None:
            serializers = super(BoardGameSerializer, self).to_native(obj)
            game_ctype = ContentType.objects.get_by_natural_key(
                'game', 'game')
            post = get_or_none(
                Post, content_type_id=game_ctype.id, object_id=obj.id)
            serializers.update({
                'full_name': obj.user.user_profile.display_name
            })
            serializers.update({
                'picture': obj.user.user_profile.profile_picture
            })
            serializers.update({
                'golfcourse_name': obj.golfcourse.name
            })
            if post is not None:
                post_seri = MultiCommentSeri(post)
                serializers.update({
                    'post': post_seri.data
                })
            return serializers


class GameFlightSerializer(serializers.ModelSerializer):
    game = GameSerializer(required=False, source='game')
    member = EventMemberSerializer(required=False, source='member')

    class Meta:
        model = GameFlight
        fields = ('flight', 'game', 'member')