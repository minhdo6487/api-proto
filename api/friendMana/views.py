from datetime import datetime

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from haystack.query import SearchQuerySet
from rest_framework import mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.views import APIView

from api.friendMana.serializers import FriendRequestSerializer, FriendConnectSerializer, FriendSerializer, \
    PaginatedFriendSerializer
from api.noticeMana.tasks import send_notification
from api.userMana.serializers import UserSerializer, UserDisplaySerializer
from core.friend.models import FriendRequest, FriendConnect, Friend, FriendPostTrack
from core.golfcourse.models import GolfCourseStaff
from core.notice.models import Notice
from core.user.models import UserProfile, UserLocation
from utils.django.models import get_or_none
from utils.rest import viewsets as addedviewsets
from utils.rest.code import code
from utils.rest.sendemail import send_email


class FriendRequestViewSet(addedviewsets.ListOnlyViewSet):
    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def get_queryset(self):
        """ Get all friend request to current use
        """
        return FriendRequest.objects.filter(touser=self.request.user)

    @staticmethod
    def connect(request, pk=None):
        """ Sent request connect to new friend.
            Returns:
                400 -- If user sent request to themselves - E_SAME_USER .
                    -- User is not valid - E_USER_NOT_FOUND.
                    -- User has already sent request before - E_ALREADY_SEND_REQUEST.
                    -- Both user are friend before - E_ALREADY_CONNECT.
                500 -- Friend request sent fail - E_NOT_SAVE.
                201 -- Friend request sent successfully - OK_SEND_FRIEND_REQUEST.
        """
        # check if user sent request to them self
        if int(request.user.id) == int(pk):
            return Response({'status': '400', 'code': 'E_SAME_USER',
                             'detail': code['E_SAME_USER']}, status=400)

        # Check both Users are valid
        from_user = get_or_none(User, pk=request.user.id)
        to_user = get_or_none(User, pk=pk)
        # Return Error Message User is not valid
        if from_user is None or to_user is None:
            return Response({'status': '400', 'code': 'E_USER_NOT_FOUND',
                             'detail': code['E_USER_NOT_FOUND']}, status=400)

        # check user have sent request before or not
        current_request = get_or_none(FriendRequest, from_user=from_user, to_user=to_user)
        # search current request in reverse way
        if current_request is None:
            current_request = get_or_none(FriendRequest, from_user=to_user, to_user=from_user)
            # Return Error Message request have sent before
        if current_request is not None:
            return Response({'status': '400', 'code': 'E_ALREADY_SEND_REQUEST',
                             'detail': code['E_ALREADY_SEND_REQUEST']}, status=400)
            # Check both users are connect or not
        current_connection = get_or_none(FriendConnect, user=from_user, friend=to_user)
        # Return Error Message both user are friend before
        if current_connection is not None:
            return Response({'status': '400', 'code': 'E_ALREADY_CONNECT',
                             'detail': code['E_ALREADY_CONNECT']}, status=400)
            # Save new request
        new_request = FriendRequest(from_user=from_user, to_user=to_user)
        new_request.save()
        # Check request is save success
        is_created = get_or_none(FriendRequest, from_user=from_user, to_user=to_user)
        # Return Error Message Request is not save
        if is_created is None:
            return Response({'status': '500', 'code': 'E_NOT_SAVE',
                             'detail': code['E_NOT_SAVE']}, status=500)
            # Return Message sent request success
        return Response({'status': '200', 'code': 'OK_SEND_FRIEND_REQUEST',
                         'detail': code['OK_SEND_FRIEND_REQUEST']}, status=201)

    @staticmethod
    def accept(request, pk=None):
        """ Accept a friend request.
            Returns:
                400 -- Request is none - E_REQUEST_NOT_FOUND.
                    -- E_INVALID_PARAMETER_VALUES.
                500 -- Cannot save friend connect to database - E_NOT_SAVE.
                201 -- Friend request has been accepted successfully - OK_SEND_FRIEND_REQUEST.
        """
        # check request is valid or not
        friend_request = get_or_none(FriendRequest, pk=pk)
        if friend_request is None:
            return Response({'status': '400', 'code': 'E_REQUEST_NOT_FOUND',
                             'detail': code['E_REQUEST_NOT_FOUND']}, status=400)
            # Create friend for login user -> request user
        new_friend1 = FriendConnectSerializer(
            data={'user': friend_request.from_user.id, 'friend': friend_request.to_user.id})
        if not new_friend1.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': new_friend1.errors}, status=400)
            # Create friend for request user -> login user
        new_friend2 = FriendConnectSerializer(
            data={'friend': friend_request.from_user.id, 'user': friend_request.to_user.id})
        if not new_friend2.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': new_friend2.errors}, status=400)
            # Save record 1
        new_friend1.save()
        # Check save or fail
        is_save1 = get_or_none(FriendConnect, user=friend_request.from_user, friend=friend_request.to_user)
        if is_save1 is not None:
            return Response({'status': '500', 'code': 'E_NOT_SAVE',
                             'detail': code['E_NOT_SAVE']}, status=500)
            # Save record 2
        new_friend2.save()
        # Check save or fail
        is_save2 = get_or_none(FriendConnect, user=friend_request.to_user, friend=friend_request.from_user)
        # if fail delete record 1
        if is_save2 is not None:
            is_save1.delete()
            return Response({'status': '500', 'code': 'E_NOT_SAVE',
                             'detail': code['E_NOT_SAVE']}, status=500)
            # if every things ok delete request
        friend_request.delete()
        return Response({'status': '200', 'code': 'OK_SEND_FRIEND_REQUEST',
                         'detail': code['OK_ACCEPT_FRIEND_REQUEST']}, status=201)

    @staticmethod
    def reject(request, pk=None):
        """ Reject a friend request.
            Returns:
              400 -- Request is none - E_REQUEST_NOT_FOUND.
              201 -- Friend request rejected successfully - OK_REJECT_FRIEND_REQUEST.
        """
        # Check request is still valid or not
        friend_request = get_or_none(FriendRequest, pk=pk)
        # if request is not valid
        if friend_request is None:
            return Response({'status': '400', 'code': 'E_REQUEST_NOT_FOUND',
                             'detail': code['E_REQUEST_NOT_FOUND']}, status=400)
        # Delete request
        friend_request.delete()
        return Response({'status': '201', 'code': 'OK_REJECT_FRIEND_REQUEST',
                         'detail': code['OK_REJECT_FRIEND_REQUEST']}, status=201)

    @staticmethod
    def cancel(request, pk=None):
        """ Cancel a friend request.
            Returns:
                400 -- Request is none - E_REQUEST_NOT_FOUND.
                201 -- Friend request cancelled successfully - OK_CANCEL_FRIEND_REQUEST.
        """
        # Check request is still valid or not
        friend_request = get_or_none(FriendRequest, pk=pk)
        # if request is not valid
        if friend_request is None:
            return Response({'status': '400', 'code': 'E_REQUEST_NOT_FOUND',
                             'detail': code['E_REQUEST_NOT_FOUND']}, status=400)
        # Delete request
        friend_request.delete()
        return Response({'status': '200', 'code': 'OK_CANCEL_FRIEND_REQUEST',
                         'detail': code['OK_CANCEL_FRIEND_REQUEST']}, status=200)


class FriendViewSet(mixins.CreateModelMixin,
                    mixins.ListModelMixin,
                    GenericViewSet):
    """ Viewset handle for friend relation.
    """
    queryset = Friend.objects.all()
    serializer_class = FriendSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)

    def list(self, request, *args, **kwargs):
        """ Get all friend connections of current user
        """
        from_user = request.QUERY_PARAMS.get('user', None)
        if from_user:
            from_user_id = from_user
        else:
            from_user_id = request.user.id

        query = Friend.objects.filter(from_user_id=from_user_id)
        # items = request.QUERY_PARAMS.get('item', 50)
        items = 200
        paginator = Paginator(query, items)

        page = request.QUERY_PARAMS.get('page')

        try:
            friends = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            friends = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999),
            # deliver last page of results.
            friends = paginator.page(paginator.num_pages)
        user_location = UserLocation.objects.filter(user=request.user).order_by('-modified_at').first()
        context = dict(user_id=request.user.id)
        if user_location:
            context['lat'] = user_location.lat
            context['lon'] = user_location.lon
        serializer = PaginatedFriendSerializer(friends, context=context)
        return Response(serializer.data, status=200)

    def create(self, request, *args, **kwargs):
        data = request.DATA
        to_request = []
        for d in data.get('to_user', []):
            to_request.append({'from_user': request.user.id, 'to_user': d})
        serializer = self.serializer_class(data=to_request, many=True)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        friends = serializer.save()
        message_notify_en = str(
            request.user.user_profile.display_name) + ' added friend with you. Would you like to add him?'
        message_notify_vi = str(
            request.user.user_profile.display_name) + ' đã kết bạn với bạn. Bạn có muốn thêm golfer này tới danh sách bạn bè của bạn?'
        translate_message_notify = {
            'alert_vi': message_notify_vi,
            'alert_en': message_notify_en
        }
        ctype = ContentType.objects.get_for_model(Friend)
        for friend in friends:
            if not Friend.objects.filter(from_user=friend.to_user, to_user=request.user).exists():
                Notice.objects.create(content_type=ctype,
                                      object_id=friend.id,
                                      to_user=friend.to_user,
                                      detail=message_notify_vi,
                                      detail_en=message_notify_en,
                                      notice_type='FR',
                                      from_user=request.user,
                                      send_email=False)
                send_notification.delay([friend.to_user_id], message_notify_en, translate_message_notify)
            Notice.objects.filter(content_type=ctype, to_user=request.user, from_user=friend.to_user,
                                  notice_type='FR').delete()
        return Response(serializer.data, status=200)

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def unfriend(request, pk=None):
    """ Delete friend relation between 2 users.
        Returns:
            400 -- Send unfriend request to current user - E_SAME_USER.
                -- Any user is not valid - E_USER_NOT_FOUND.
                -- Has no friend connections - E_REQUEST_NOT_FOUND.
            204 -- Friend connection has been removed successfully - OK_UNFRIEND.
    """
    # Check user id and friend id
    if int(request.user.id) == int(pk):
        return Response({'status': '400', 'code': 'E_SAME_USER',
                         'detail': code['E_SAME_USER']}, status=400)
    # Check 2 user is valid
    current_user = get_or_none(User, pk=request.user.id)
    friend = get_or_none(User, pk=pk)
    # if 1 or 2 user is not valid
    if current_user is None or friend is None:
        return Response({'status': '400', 'code': 'E_USER_NOT_FOUND',
                         'detail': code['E_USER_NOT_FOUND']}, status=400)
    # get connect of request user -> friend
    # from_user=friend.to_user, to_user=request.user
    current_connection = get_or_none(Friend, from_user=current_user, to_user=friend)
    if current_connection is None:
        return Response({'status': '400', 'code': 'E_REQUEST_NOT_FOUND',
                         'detail': code['E_REQUEST_NOT_FOUND']}, status=400)
    # get connect of friend to request user
    # reverse_connection = get_or_none(FriendConnect, user=friend, friend=current_user)
    #if reverse_connection is None:
    #    return Response({'status': '400', 'code': 'E_REQUEST_NOT_FOUND',
    #                     'detail': code['E_REQUEST_NOT_FOUND']}, status=400)
    # Delete
    current_connection.delete()
    #reverse_connection.delete()
    # if every thing ok
    return Response({'status': '200', 'code': 'OK_UNFRIEND',
                     'detail': code['OK_UNFRIEND']}, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def invitation(request):
    """ Send an email to invitation non-member to event
        Parameters:
            * email
            * content
        Returns:
            400 -- Email is not valid - E_INVALID_EMAIL.
                -- Send email fail - E_SEND_EMAIL_FAIL.
            200 -- Send mail successfully - OK_SEND_EMAIL.
    """
    # Check Email is valid
    email = request.DATA['email']
    try:
        validate_email(email)
    except ValidationError:
        return Response({'status': '400', 'code': 'E_INVALID_EMAIL',
                         'detail': code['E_INVALID_EMAIL']}, status=400)
    # Email Info
    subject = 'Golfconnect Invitation Email'
    email = [request.DATA['email']]
    message = '<p>' + request.DATA['content'] + '</p>'
    # Create Email
    send_ok = send_email(subject, message, email)
    if send_ok:
        return Response({'status': '200', 'code': 'OK_SEND_EMAIL',
                         'detail': code['OK_SEND_EMAIL']}, status=200)
    else:
        return Response({'status': '400', 'code': 'E_SEND_EMAIL_FAIL',
                         'detail': code['E_SEND_EMAIL_FAIL']}, status=400)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def search(request):
    """ Search a new friend by parameters
        Returns:
            400 -- Return errors - E_INVALID_PARAMETER_VALUES.
            200 -- Return friend data successfully - OK_SEARCH.
    """
    # Get data form request
    name = request.DATA.get('first_name', "''")
    if name == "":

        first_names = request.DATA.get('first_name', "''")
        last_names = request.DATA.get('last_name', "''")
        display_names = request.DATA.get('display_name', "''")
    else:
        first_names = name
        last_names = name
        display_names = name
    genders = request.DATA.get('gender', "''")

    handicaps = request.DATA.get('handicap', "''")
    business_area = request.DATA.get('business_area', "''")
    city = request.DATA.get('city', "''")
    district = request.DATA.get('district', "''")
    age = request.POST.get('age', 0)
    dob_year = int(datetime.now().year) - int(age)
    min_dob = datetime.strptime(str(dob_year) + '-01-1', '%Y-%m-%d')
    max_dob = datetime.strptime(str(dob_year) + '-12-30', '%Y-%m-%d')

    # Search by single properties
    results = SearchQuerySet().filter(first_name=first_names).filter(last_name=last_names
                                                                     ).filter(gender=genders).filter(
        display_name=display_names).filter(handicap_us=handicaps
                                           ).filter(handicap_36=handicaps
                                                    ).filter(business_area=business_area).filter(city=city
                                                                                                 ).filter(
        district=district)

    if age is not 0:
        results.filter(dob__gte=min_dob, dob__lte=max_dob)
    # Get List user
    queryset = User.objects.all()
    # Create result list
    results_list = []
    # Get User to list by id
    max_loop = results.count()
    for x in range(0, max_loop):
        user = get_object_or_404(queryset, pk=results[x].object.id)
        results_list.append(user)
    # Convert to serializer
    serializer = UserSerializer(results_list, many=True)
    if serializer.is_valid:
        return Response({'status': '200', 'code': 'OK_SEARCH',
                         'detail': serializer.data}, status=200)
    else:
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def suggestions(request):
    """ Suggest new friends by the same properties
        Returns:
            400 -- Return errors - E_INVALID_PARAMETER_VALUES.
            200 -- Return friend data successfully - OK_SUGGESTION.
    """
    # Get login user profile
    u_profile = UserProfile.objects.get(user=request.user)
    # Search by user profile
    sqs = SearchQuerySet().filter(business_area=u_profile.business_area, city=u_profile.city,
                                  handicap_36__lte=int(u_profile.handicap_36) + 1,
                                  handicap_36__gte=int(u_profile.handicap_36) - 1,
                                  handicap_us__lte=int(u_profile.handicap_us) + 1,
                                  handicap_us__gte=int(u_profile.handicap_us) - 1)
    # Get user list
    queryset = User.objects.all()
    # Create result list
    results_list = []
    # Get User to list by id
    max_loop = sqs.count()
    for x in range(0, max_loop):
        user = get_object_or_404(queryset, pk=sqs[x].object.id)
        results_list.append(user)
    # Convert to serializer
    serializer = UserSerializer(results_list, many=True)
    if serializer.is_valid:
        return Response({'status': '200', 'code': 'OK_SUGGESTION',
                         'detail': serializer.data}, status=200)
    else:
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_friend(request):
    golfstaff = GolfCourseStaff.objects.all().values_list('user_id', flat=True)
    profiles = User.objects.filter(id__gte=0).exclude(id__in=golfstaff).exclude(
        user_profile__display_name__isnull=True).exclude(user_profile__display_name__exact='').exclude(
        id=request.user.id)
    lat = request.QUERY_PARAMS.get('lat')
    lng = request.QUERY_PARAMS.get('lon')
    context = dict(user_id=request.user.id)
    if lat and lng:
        lat = float(lat)
        lng = float(lng)
        min_lat = lat - 1  # You have to calculate this offsets based on the user location.
        max_lat = lat + 1  # Because the distance of one degree varies over the planet.
        min_lng = lng - 1
        max_lng = lng + 1
        nearby_user = UserLocation.objects.filter(lat__gt=min_lat, lat__lt=max_lat, lon__gt=min_lng,
                                                  lon__lt=max_lng).values_list('user_id', flat=True)
        u = UserLocation.objects.filter(user=request.user).first()
        if u:
            u.lat = lat
            u.lon = lng
            u.save()
        else:
            u = UserLocation.objects.create(user=request.user, lat=lat, lon=lng)
        profiles = profiles.filter(id__in=nearby_user)
        context['lat'] = lat
        context['lon'] = lng
    serializers = UserDisplaySerializer(profiles, many=True, context=context)
    results = sorted(serializers.data, key=lambda k: k['friend_distance'])
    return Response({'data': results}, status=200)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def track_post_friend(request):
    data = request.DATA
    FriendPostTrack.objects.update_or_create(user=request.user, to_user_id=data['to_user'])
    return Response({'status': 1}, status=200)


class FriendViewV2(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        Get all friends of user
        :param request:
        :return:
        """
        from_user_id = request.QUERY_PARAMS.get('user', None)
        if from_user_id is None:
            from_user_id = request.user.id
        query = Friend.objects.filter(from_user_id=from_user_id)
        items = request.QUERY_PARAMS.get('page_size', 10)
        paginator = Paginator(query, items)
        page = request.QUERY_PARAMS.get('page')
        try:
            friends = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            friends = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            friends = paginator.page(paginator.num_pages)
        user_location = UserLocation.objects.filter(user=request.user)\
            .order_by('-modified_at')\
            .first()
        context = {'user_id': request.user.id}
        if user_location:
            context['lat'] = user_location.lat
            context['lon'] = user_location.lon
        serializer = PaginatedFriendSerializer(friends, context=context)
        return Response(serializer.data, status=200)
