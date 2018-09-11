import datetime

from api.noticeMana.serializers import CrawlTeetimeSerializer
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, Q
from haystack.query import SearchQuerySet
from rest_framework import mixins
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.pagination import PaginationSerializer
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from api.noticeMana.views import get_from_xmpp, update_version
from api.userMana.serializers import UserSerializer, UserSettingSerializer, UserDisplaySerializer, \
    ChangePasswordSerializer, UserGameSerializer, UserActivitySerializer, PaginatedActivitySerializer, \
    CommentActivitySerializer, InvoiceSerializer, UserLocationSerializer, PaginatedUserSerializer, UserVersionMessageSerializer, \
    GroupChatSerializer, UserPrivacySerializer
from api.userMana.tasks import log_activity, query_online_user_xmpp, block_user, get_last_modified_room
from core.friend.models import Friend
from core.game.models import EventMember, Game
from core.golfcourse.models import GolfCourseEvent, GolfCourseStaff
from core.like.models import Like
from core.user.models import UserSetting, UserProfile, UserActivity, Invoice, UserLocation, UserVersion, \
    GroupChat, UserGroupChat, UserPrivacy
from utils.django.models import get_or_none
from utils.rest.code import code
from utils.rest.permissions import UserIsOwnerOrRead
from utils.rest.viewsets import GetAndUpdateViewSet, OnlyGetViewSet
from v2.api.chatserviceMana.tasks import get_user_chat_statistic

@api_view(['POST'])
def get_group(request):
    email_list = request.DATA.get('email', "''")
    if email_list == "''":
        return Response({'detail': 'Are You Kidding me???'}, status=404)
    return_data = []
    i = 1
    for item in email_list:
        s = 'p' + str(i)
        user = get_or_none(User, username=item[s])
        if user is not None:
            return_data.append({s: {'name': user.last_name + ' ' + user.first_name, 'id': user.id}})
        else:
            return_data.append({s: {'name': '', 'id': -1}})
        i += 1
    return Response(return_data, status=404)


class UserViewSet(OnlyGetViewSet):
    """ Viewset handle for managing Get Another User profile and friend list
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated,)

    # get user detail by pk

    def list(self, request, *args, **kwargs):
        email = request.QUERY_PARAMS.get('email', '')
        if email:
            user = get_or_none(User, username=email)
            if user:
                serialize = UserDisplaySerializer(user)
                return Response(serialize.data, status=200)
        return Response([], status=200)

    def retrieve(self, request, pk=None, **kwargs):
        user = get_or_none(User, pk=pk)
        if user is None:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Cannot find user'}, status=404)
        privacy = UserPrivacy.objects.filter(user=user, target=request.user, action='D').first()
        context = {
            'is_block': True if privacy else False
        }
        # get usersetting by PK
        setting_queryset = UserSetting.objects.get(user_id=pk)

        # if user not public and not get itself
        if not setting_queryset.public_profile and request.user.id != int(pk):
            return Response({'status': '405', 'code': 'E_GET_NOT_ALLOW',
                             'detail': code['E_GET_NOT_ALLOW']}, status=405)

        serializer = UserSerializer(user, context=context)

        response_data = serializer.data

        # checking friend with current user
        response_data['is_friend'] = Friend.objects.filter(from_user=request.user.id, to_user=user.id).count() > 0
        response_data['current_user_id'] = request.user.id

        return Response(response_data, status=200)


class ProfileView(GetAndUpdateViewSet):
    """ Viewset handle for user profile
        HEADER :
            GET
            PATCH
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # TODO: More rule for action
    permission_classes = (IsAuthenticated, UserIsOwnerOrRead)
    parser_classes = (JSONParser, FormParser,)

    def initial(self, request, *args, **kwargs):
        """ Override init function of django to add pk to the request, before calling any other actions
        """
        super().initial(request, *args, **kwargs)
        self.kwargs['pk'] = request.user.pk

    def partial_update(self, request, *args, **kwargs):
        # add encode password to request
        return super(ProfileView, self).partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super(ProfileView, self).update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        device = request.QUERY_PARAMS.get('device', '')
        if device == 'mobile':
            user_profile = UserProfile.objects.only('display_name', 'gender', 'handicap_us', 'profile_picture').get(
                user=request.user)
            return Response({
                "display_name": user_profile.display_name,
                "gender": user_profile.gender,
                "handicap_us": user_profile.handicap_us,
                "profile_picture": user_profile.profile_picture
            })
        return super(ProfileView, self).retrieve(request, *args, **kwargs)


class ChangePassView(APIView):
    """ Viewset handle for changing password
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrRead)
    parser_classes = (JSONParser, FormParser,)

    def post(self, request):
        """ Changing password in database.
            Returns:
                200 -- Change successfully - OK_CHANGE_PASSWORD.
                404 -- Can't find this user - E_USER_NOT_FOUND.
                411 -- Password is required - E_INVALID_PARAMETER_VALUES.
        """

        serializer = self.serializer_class(data=request.DATA)
        # validate
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        # check user is not null
        user = get_or_none(User, pk=int(request.user.id))
        if user is None:
            # return fail
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Cannot find user'}, status=404)
        # edit password
        if user.check_password(request.DATA['password']):
            user.set_password(request.DATA['new_password'])
            # save password
            user.save()
            user.user_profile.date_pass_change = datetime.date.today()
            user.user_profile.save()
            return Response({'status': '200', 'code': 'OK_CHANGE_PASSWORD',
                             'detail': code['OK_CHANGE_PASSWORD']}, status=200)
        else:
            return Response({'status': '400', 'code': 'E_INVALID_PASSWORD',
                             'detail': 'invalid password'}, status=400)


class UserSettingView(GetAndUpdateViewSet):
    """ Viewset handle for getting and updating user setting
    """
    queryset = User.objects.all()
    serializer_class = UserSettingSerializer
    permission_classes = (IsAuthenticated, UserIsOwnerOrRead)
    parser_classes = (JSONParser, FormParser,)

    def initial(self, request, *args, **kwargs):
        """ Override init function of django to add pk to the request, before calling any other actions
        """
        super().initial(request, *args, **kwargs)
        self.kwargs['pk'] = request.user.pk


class FindEmailViewSet(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        username = request.QUERY_PARAMS.get('name', '')
        resutls = []
        if username:
            temp = SearchQuerySet().autocomplete(username=username)[0:5]
            for t in temp:
                if not t.pic:
                    t.pic = '/assets/images/icon_name/' + t.username[0].upper() + '_icons/1_Desktop_Icons/icon_512.png'
                resutls.append({'username': t.username,
                                'display_name': t.display_name,
                                'phone': t.mobile,
                                'pic': t.pic})
        else:
            golfcourse_staff = GolfCourseStaff.objects.all().values_list('user_id', flat=True)

            temp = UserProfile.objects.only('display_name', 'description','profile_picture', 'user_id', 'handicap_us',
                                            'user__email').filter(user_id__gte=0, display_name__isnull=False).exclude(
                display_name__exact='').exclude(user_id__in=golfcourse_staff).order_by('-user__date_joined')
            for t in temp:
                if not t.user.email:
                    email = t.user.username
                else:
                    email = t.user.email
                resutls.append({'description': t.description,
                                'display_name': t.display_name,
                                'id': t.user_id,
                                'pic': t.profile_picture,
                                'handicap': t.handicap_us,
                                'handicap_us': t.handicap_us,
                                'email': email})
        return Response(resutls, status=200)

class NewFindEmailViewSet(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        name = request.QUERY_PARAMS.get('name')
        filter_params = {'id__gte':0}

        golfcourse_staff = GolfCourseStaff.objects.all().values_list('user_id', flat=True)
        query = User.objects.filter(**filter_params)\
            .order_by('-date_joined')\
            .exclude(id__in=golfcourse_staff)\
            .exclude(user_profile__display_name__isnull=True)\
            .exclude(user_profile__display_name__exact='')\
            .exclude(id=request.user.id)
        if name:
            query = query.filter(Q(user_profile__display_name__unaccent__icontains=name)
                                 | Q(user_profile__display_name__icontains=name))

        items = request.QUERY_PARAMS.get('item', 10)
        paginator = Paginator(query, items)

        page = request.QUERY_PARAMS.get('page')

        try:
            activities = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            activities = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999),
            # deliver last page of results.
            activities = paginator.page(paginator.num_pages)

        serializer = PaginatedUserSerializer(activities, context={'user_id': request.user.id})
        return Response(serializer.data, status=200)

class UserGameViewSet(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, user_id):
        resutls = {'games': []}
        event_member = EventMember.objects.filter(user=request.user).values_list('id', flat=True)
        games = Game.objects.filter(event_member__in=event_member).order_by('-date_play')
        items = request.QUERY_PARAMS.get('item', 10)
        paginator = Paginator(games, items)

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
        event_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        game_ctype = ContentType.objects.get_for_model(Game)
        for game in games:
            game_data = {'members': []}
            member_games = Game.objects.filter(group_link=game.group_link).order_by('gross_score')
            serializer = UserGameSerializer(member_games, many=True)
            game_data['members'] = serializer.data
            date_play = game.date_play
            golfcourse_name = game.golfcourse.name
            if game.event_member.event:
                like_count = \
                    Like.objects.filter(content_type=event_ctype, object_id=game.event_member.event.id).aggregate(
                        Sum('count'))['count__sum']
            else:
                like_count = Like.objects.filter(content_type=event_ctype, object_id=game.id).aggregate(Sum('count'))[
                    'count__sum']

            game_data.update({
                'like_count': like_count if like_count else 0,
                'golfcourse_name': golfcourse_name,
                'date_play': date_play
            })
            resutls['games'].append(game_data)

        paging = PaginationSerializer(instance=games)
        resutls.update({'count': paging.data['count'],
                        'next': paging.data['next'],
                        'prev': paging.data['previous']})
        return Response(resutls, status=200)


class UserActivityViewset(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.DestroyModelMixin,
                          GenericViewSet):
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        user_id = request.QUERY_PARAMS.get('user', None)
        if not user_id:
            user_id = request.user.id
        getype = ContentType.objects.get_for_model(GolfCourseEvent)
        user_event = GolfCourseEvent.objects.filter(event_member__user_id=request.user.id)
        object_event = GolfCourseEvent.objects.filter(event_member__user_id=user_id, is_publish=True)
        event = user_event | object_event
        event_id = event.values_list('id', flat=True)
        query_game = UserActivity.objects.filter(user_id=user_id, public=True).exclude(content_type=getype)
        query_event = UserActivity.objects.filter(user_id=user_id, public=True, content_type=getype, object_id__in=event_id)
        query = query_game | query_event
        query = query.order_by('-date_creation')
        items = request.QUERY_PARAMS.get('item', 10)
        paginator = Paginator(query, items)

        page = request.QUERY_PARAMS.get('page')

        try:
            activities = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            activities = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999),
            # deliver last page of results.
            activities = paginator.page(paginator.num_pages)

        serializer = PaginatedActivitySerializer(activities)
        for d in serializer.data['results']:
            channel = str(d['id']) + '_activity'
            d.update({'comment_count': get_from_xmpp(request.user.username, channel)[0]})
            if d['verb'] in ['join_event', 'create_event'] and d['related_object'].get('event_id'):
                (count, uread) = get_from_xmpp(request.user.username, d['related_object']['event_id'])
                d['related_object'].update({'comment_count': count})

        return Response(serializer.data, status=200)

    def create(self, request, *args, **kwargs):
        serializer = CommentActivitySerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        ctype = None
        if serializer.data['content_type'] == 'Event':
            ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        if not ctype:
            return Response({}, status=404)
        log_activity(request.user.id, 'comment', serializer.data['object_id'], ctype.id)

        return Response({'detail': 'OK'}, status=200)


class InvoiceViewSet(ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (AllowAny,)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def track_location(request):
    data = request.DATA
    data.update({'user': request.user.id})
    serializer = UserLocationSerializer(data=data)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    u = UserLocation.objects.filter(user=request.user).first()
    if u:
        u.lat = data['lat']
        u.lon = data['lon']
        u.save()
    else:
        u = UserLocation.objects.create(user=request.user, lat=data['lat'], lon=data['lon'])
    serializer = UserLocationSerializer(u)
    return Response({'status': 1, 'data': serializer.data}, status=200)

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def clean_up_activities(request):
    serializer = CrawlTeetimeSerializer(data=request.DATA)
    if not serializer.is_valid():
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)
    activities = UserActivity.objects.filter(verb='create_game')
    for a in activities:
        if not a.related_object or (a.related_object and not a.related_object.is_finish):
            a.delete()
    return Response({'status': 1})

@api_view(['GET','POST'])
@permission_classes((AllowAny,))
def update_user_version(request):
    if request.method == 'POST':
        serializer = UserVersionMessageSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        data = serializer.data
        update_version(data['user'],data['version'],data['source'])
        return Response({'status': 200, 'detail': 'ok'}, status=200)
    if request.method == 'GET':
        userverion = UserVersion.objects.all()
        for uv in userverion:
            data = "{0} - {3} got version {1} from source {2}".format(uv.user.id, uv.version, uv.source, (uv.user.email or uv.user.username))

        return Response({'status': 200, 'detail': 'ok'}, status=200)

class GroupchatViewSet(ModelViewSet):
    queryset = GroupChat.objects.all()
    serializer_class = GroupChatSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        groupchat = GroupChat.objects.filter(group_member__user_id=request.user.id).order_by('-modified_at')
        context = query_online_user_xmpp()
        #context = {}
        friend_list = request.user.friend_fromusers.all().values_list('to_user_id',flat=True)
        privacy_list = request.user.privacy_owner.all().filter(action='D').values_list('target_id',flat=True)
        list_group = groupchat.values_list('group_id',flat=True)
        chat_statistic = get_user_chat_statistic(user=request.user, room_id=list(list_group) or [], is_notify=False)
        context.update({
                'friend_list': list(friend_list),
                'privacy_list': list(privacy_list),
                'last_modified_date': get_last_modified_room(list(list_group)),
                'chat_statistic': chat_statistic,
                'requested_by': request.user.id
            })
        serializer = self.serializer_class(groupchat, context=context)
        serializer.data.sort(key=lambda k: (str(k['last_modified_at']), k['id']), reverse=True)
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer.data}, status=200)

    def create(self, request, *args, **kwargs):
        if 'data' in request.DATA:
            request.DATA['data']['user'] = request.user.id
            data = request.DATA['data']
            players = request.DATA['data']['invite_people']
        else:
            request.DATA['user'] = request.user.id
            data = request.DATA
            players = request.DATA['invite_people']
        userid_list = [request.user.id]
        blocked_by = request.user.privacy_target.all().filter(action='D').values_list('user_id',flat=True)
        flag = False
        for player in players:
            user_id = player.get('user_id')
            if not user_id or not str(user_id).isdigit():
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'You must fill at least email or phone'}, status=400)
            if user_id == request.user.id:
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'Cannot invite myself'}, status=400)
            if user_id in list(blocked_by):
                flag = True
            userid_list.append(user_id)
        userid_list.sort()
        if len(userid_list) == 2 and flag:
            return Response({'status': '400', 'code': 'BLOCKED_BY_PERSON',
                            'detail': 'You blocked by this person'}, status=400)
        if not userid_list:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': 'No user'}, status=400)
        user_string = ' '.join(str(x) for x in userid_list)
        groupchat = GroupChat.objects.filter(member_list=user_string).order_by('-modified_at').first()
        if not groupchat:
            groupchat = GroupChat.objects.create(member_list=user_string)
            groupchat = GroupChat.objects.get(pk=groupchat.id)
        for uid in userid_list:
            uGroup= UserGroupChat.objects.filter(user_id=uid,groupchat=groupchat).first()
            if not uGroup:
                uGroup = UserGroupChat.objects.create(user_id=uid,groupchat=groupchat,invited_by_id=request.user.id)
        context = query_online_user_xmpp()
        friend_list = request.user.friend_fromusers.all().values_list('to_user_id',flat=True)
        privacy_list = request.user.privacy_owner.all().filter(action='D').values_list('target_id',flat=True)
        chat_statistic = get_user_chat_statistic(user=request.user, room_id=[groupchat.group_id], is_notify=False)
        context.update({
                'friend_list': list(friend_list),
                'privacy_list': list(privacy_list),
                'last_modified_date': get_last_modified_room([groupchat.group_id]),
                'requested_by': request.user.id,
                'chat_statistic': chat_statistic
            })
        serializer = self.serializer_class(groupchat, context=context)
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer.data}, status=200)
    def destroy(self, request, pk=None):
        if not pk:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': 'You must field room'}, status=400)
        uGroup = UserGroupChat.objects.filter(user_id=request.user.id,groupchat=pk).first()
        if uGroup:
            userid_list = UserGroupChat.objects.filter(groupchat=pk).exclude(user_id=request.user.id).values_list('user_id', flat=True)
            userid_list = sorted(list(userid_list))
            if not userid_list:
                uGroup.groupchat.delete()
            else:
                user_string = ' '.join(str(x) for x in userid_list)
                uGroup.groupchat.member_list = user_string
                uGroup.groupchat.save()
            uGroup.delete()
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)
    def retrieve(self, request, pk=None):
        if not pk:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': 'You must field room'}, status=400)
        groupchat = GroupChat.objects.filter(pk=pk).order_by('-modified_at')
        list_group = groupchat.values_list('group_id',flat=True)
        context = query_online_user_xmpp()
        friend_list = request.user.friend_fromusers.all().values_list('to_user_id',flat=True)
        privacy_list = request.user.privacy_owner.all().filter(action='D').values_list('target_id',flat=True)
        list_group = groupchat.values_list('group_id',flat=True)
        chat_statistic = get_user_chat_statistic(user=request.user, room_id=list(list_group), is_notify=False)
        context.update({
                'friend_list': list(friend_list),
                'privacy_list': list(privacy_list),
                'last_modified_date': get_last_modified_room(list(list_group)),
                'requested_by': request.user.id,
                'chat_statistic': chat_statistic
            })
        serializer = GroupChatSerializer(groupchat, context=context)
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer.data}, status=200)
    def update(self,request,pk=None):
        type = request.DATA.get('type', 'Invite')
        groupchat = get_or_none(GroupChat,id=pk)
        if not groupchat:
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': 'No such room'}, status=400)
        players = request.DATA['invite_people']
        userid_list = UserGroupChat.objects.filter(groupchat=groupchat).values_list('user_id',flat=True)
        userid_list = list(userid_list)
        blocked_by = request.user.privacy_target.all().filter(action='D').values_list('user_id',flat=True)
        flag = False
        for player in players:
            user_id = player.get('user_id')
            if not user_id or not str(user_id).isdigit():
                return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                 'detail': 'You must fill at least email or phone'}, status=400)
            if user_id == request.user.id:
                    return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                                     'detail': 'Cannot invite myself'}, status=400)
            if user_id not in userid_list:
                userid_list.append(user_id)
            if user_id in list(blocked_by):
                flag = True
        if flag:
            return Response({'status': '400', 'code': 'BLOCKED_BY_PERSON',
                            'detail': 'You blocked by this person'}, status=400)
        userid_list.sort()
        user_string = ' '.join(str(x) for x in userid_list)
        for uid in userid_list:
            uGroup = UserGroupChat.objects.filter(user_id=uid,groupchat=groupchat).first()
            if not uGroup:
                uGroup = UserGroupChat.objects.create(user_id=uid,groupchat=groupchat,invited_by_id=request.user.id)
            uGroup.groupchat.member_list = user_string
            uGroup.groupchat.save()
            user_privacy = uGroup.user.privacy_owner.all().first()
            if user_privacy:
                user_privacy.save()
        context = query_online_user_xmpp()
        friend_list = request.user.friend_fromusers.all().values_list('to_user_id',flat=True)
        privacy_list = request.user.privacy_owner.all().filter(action='D').values_list('target_id',flat=True)
        chat_statistic = get_user_chat_statistic(user=request.user, room_id=[groupchat.group_id], is_notify=False)
        context.update({
                'friend_list': list(friend_list),
                'privacy_list': list(privacy_list),
                'last_modified_date': get_last_modified_room([groupchat.group_id]),
                'requested_by': request.user.id,
                'chat_statistic': chat_statistic
            })
        serializer = GroupChatSerializer(groupchat, context=context)
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer.data}, status=200)

class UserPrivacyViewSet(ModelViewSet):
    queryset = UserPrivacy.objects.all()
    serializer_class = UserPrivacySerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)
    ACTION_CHOICE = {
        'allow': 'A',
        'deny' : 'D'
    }
    def create(self, request, *args, **kwargs):
        user = request.user
        target = request.DATA.get('user_id', None)
        action = request.DATA.get('action', None)
        target_user = get_or_none(User,pk=target)
        query_action = self.ACTION_CHOICE.get(action.lower(), None)
        if target_user and query_action:
            privacy_list, created = UserPrivacy.objects.get_or_create(user=user, target=target_user)
            privacy_list.action = query_action
            privacy_list.save(update_fields=['action'])

        return Response({'status': '200', 'code': 'OK',
                         'detail': 'OK'}, status=200)

    def list(self, request, *args, **kwargs):
        groupchat = UserPrivacy.objects.filter(user=request.user,action=self.ACTION_CHOICE.get('deny', None))
        serializer = self.serializer_class(groupchat)
        return Response({'status': '200', 'code': 'OK',
                         'detail': serializer.data}, status=200)