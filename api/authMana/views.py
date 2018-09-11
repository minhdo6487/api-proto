import datetime

import math

import hashlib
import random
import re

import boto3
from api.noticeMana.tasks import set_endpoint_enabled, get_endpoint_arn
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg
from django.utils.http import int_to_base36, base36_to_int
from rest_framework.authtoken.models import Token
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from social.apps.django_app.utils import psa

from GolfConnect.settings import S3_AWSKEY, ANDROID_SNS_ARN_DEV, ANDROID_SNS_ARN_PROD, IOS_SNS_ARN_DEV, IOS_SNS_ARN_PROD
from GolfConnect.settings import SNS_REGION, S3_SECRET
from api.authMana.serializers import RegisterSerializer, ResetPasswordSerializer, ResetPasswordKeySerializer, \
    LoginSerializer, UserDeviceSerializer
from core.booking.models import BookedPartner, BookedTeeTime
from core.customer.models import Customer
from core.game.models import Game, EventMember
from core.gcauth.models import PasswordReset, RegistrationInfo
from core.golfcourse.models import GolfCourseEvent
from core.notice.models import Notice
from core.user.models import UserDevice, ANOTHER, UserProfile
from utils.django.models import get_or_none
from utils.rest.code import code
from utils.rest.permissions import IsNotAuthenticated
from utils.rest.sendemail import send_email
from api.noticeMana.tasks import send_register_email
# from core.invitation.models import InvitedPeople, Invitation
from v2.api.gc_eventMana.tasks import send_email_welcome


# from utils.rest.permissions import decrypt_val
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import requests

GENDER = {'male': 'M', 'female': 'F'}


class LoginView(APIView):
    """ Viewset handle for login
    """
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsNotAuthenticated,)

    @staticmethod
    def post(request):
        """ Use for login method
            Parameters:
                * username
                * password
            Returns:
                200 - Login successfully.
                400 - Have to active your account first.
                400 - You login already.
                400 - User is not in database
                :param request:
        """
        username = request.DATA.get('username', '')
        device_token = request.DATA.get('deviceToken', '')
        if not username:
            return Response({'status': '400', 'code': 'E_IS_LOGIN',
                             'detail': {'username': 'This field is required'}}, status=400)
        username = username.lower()

        # check user login or not
        if request.user.is_authenticated():
            return Response({'status': '400', 'code': 'E_IS_LOGIN',
                             'detail': code['E_IS_LOGIN']}, status=400)

        user = authenticate(username=username, password=request.DATA.get('password'))
        if user is None:
            return Response({'status': '400', 'code': 'E_LOGIN_INCORRECT',
                             'detail': code['E_LOGIN_INCORRECT']}, status=400)

        # check user have active yet
        if not user.is_active:
            return Response({'status': '400', 'code': 'E_NOT_ACTIVE',
                             'detail': code['E_NOT_ACTIVE']}, status=400)

        profile, _ = UserProfile.objects.get_or_create(user=user)

        # login user
        login(request, user)
        if device_token:
            profile.deviceToken = device_token
            try:
                profile.save(update_fields=['deviceToken'])
            except Exception as ex:
                print(ex)
                return Response({'status': 500, 'detail': 'Update token failed'}, status=500)

        # return login success with session id
        token = Token.objects.get_or_create(user=user)
        member_golfcourse = user.member_golfcourse.all().values_list('golfcourse', flat=True)
        game = Game.objects.filter(event_member__user_id=user.id, golfcourse__number_of_hole__gte=18,
                                   is_finish=True, active=True).aggregate(Avg('gross_score'))
        avg_stroke = 0
        if game['gross_score__avg']:
            avg_stroke = math.ceil(game['gross_score__avg'])

        resp = {
            'id'                : user.id,
            'status'            : '200',
            'code'              : 'OK_LOGIN',
            'detail'            : code['OK_LOGIN'],
            'token'             : token[0].key,
            'display_name'      : profile.display_name,
            'picture'           : profile.profile_picture,
            'gender'            : profile.gender,
            'handicap_us'       : profile.handicap_us,
            'email'             : user.email,
            'business_area'     : profile.business_area,
            'member_golfcourse' : member_golfcourse,
            'avg_stroke'        : avg_stroke,
            'dob'               : profile.dob,
        }

        return Response(resp,status=200)


class LogoutView(APIView):
    """ Viewset handle for login
    """
    parser_classes = (JSONParser, FormParser,)

    @staticmethod
    def get(request):
        """ Use for logout method
            Returns:
                200 - Logout successfully.
                400 - Not Login Yet.
        """
        # check user login or not
        if not request.user.is_authenticated():
            return Response({'status': '401', 'code': 'E_IS_NOT_LOGIN',
                             'detail ': code['E_IS_NOT_LOGIN']}, status=401)
        try:
            token = Token.objects.get(user=request.user)
        except Exception:
            return Response({'status': '400', 'code': 'E_NOT_DELETE',
                             'detail ': 'Cannot delete token'}, status=400)
        device_id = request.QUERY_PARAMS.get('device_id')
        if device_id:
            device = UserDevice.objects.filter(user_id=request.user.id, device_id=device_id).first()

            if device:

                sns = boto3.client('sns',
                                   region_name=SNS_REGION,
                                   aws_access_key_id=S3_AWSKEY,
                                   aws_secret_access_key=S3_SECRET)

                sns.delete_endpoint(EndpointArn=device.push_token)
                device.delete()

        logout(request)
        return Response({'status': '200', 'code': 'OK_LOGOUT',
                         'detail ': code['OK_LOGOUT']}, status=200)


class RegisterView(APIView):
    """ Viewset handle for registration
    """
    serializer_class = RegisterSerializer
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsNotAuthenticated,)

    def post(self, request):
        """ Use for registration method
        Parameters:
            * username
            * email
            * password
        Returns:
            201 - Return registration data.
            400 - User has login before register.
            :param request:
        """
        # knock it out if logged in
        if request.user.is_authenticated():
            # user has login before register
            return Response({'status': '400', 'code': 'E_IS_LOGIN',
                             'detail ': code['E_IS_LOGIN']},
                            status=400)

        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        username = request.DATA['username'].lower()
        email = request.DATA['email'].lower()
        first_name = request.DATA['first_name']
        last_name = request.DATA['last_name']

        user, created = User.objects.get_or_create(username=username)
        if not created:
            return Response({'status': '500', 'detail': 'Register error.'}, status=500)

        if created:
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(request.DATA['password'])
            user.is_active = True

            user.user_profile.display_name = str(user.last_name) + ' ' + str(user.first_name)
            user.user_profile.gender = request.DATA.get('gender', ANOTHER)
            user.user_profile.is_member = True
            user.user_profile.deviceToken = request.DATA.get('deviceToken', '')

            user.user_profile.save()
            user.save()

            if user.email:
                send_email_welcome.delay(user.id)

        token, _ = Token.objects.get_or_create(user=user)
        resp = {
            'id'          : user.id,
            'status'      : '200',
            'code'        : 'OK',
            'detail'      : 'Register successfully',
            'token'       : token.key,
            'display_name': user.user_profile.display_name,
            'picture'     : user.user_profile.profile_picture,
            'gender'      : user.user_profile.gender,
            'handicap_us' : user.user_profile.handicap_us,
            'email'       : user.email,
        }

        return Response(resp, status=200)


class RegisterConfirmView(APIView):
    """ Viewset handle for registration confirm
    """
    serialize_class = RegistrationInfo

    @staticmethod
    def post(request, uidb36, activation_key):
        """ Activate user
        Parameters:
            * uidb36
            * activation_key
        """
        if request.user.is_authenticated():
            return Response({'status': '400', 'code': 'E_IS_LOGIN',
                             'detail': code['E_IS_LOGIN']},
                            status=400)

        # Activate user
        return UserActivator.activate_user(uidb36=uidb36, activation_key=activation_key)


SHA1_RE = re.compile('^[a-f0-9]{40}$')


class UserActivator:
    @staticmethod
    def create_activation_key(user):
        """ Create an activation key by using salt and SHA1.
        """
        username = user.username
        salt_bytes = str(random.random()).encode('utf-8')
        salt = hashlib.sha1(salt_bytes).hexdigest()[:5]
        hash_input = (salt + username).encode('utf-8')
        activation_key = hashlib.sha1(hash_input).hexdigest()
        return activation_key

    @staticmethod
    def activate_user(uidb36, activation_key):
        """ Validate an activation key and activate the corresponding user if valid.
        Parameters:
            * uidb36
            * activation key
        Returns
            * 404 - E_USER_NOT_FOUND.
            * 400 - Key has expired or invalid - E_INVALID_ACTIVATE_KEY.
            * 200 - OK_REGISTRATION.
        """
        # Check the key is a pattern of SHA1 hash;
        if not SHA1_RE.search(activation_key):
            return Response({'status': '400', 'code': 'E_INVALID_ACTIVATE_KEY',
                             'detail': code['E_INVALID_ACTIVATE_KEY']}, status=404)
            # If the key is not valid
        try:
            uid_int = base36_to_int(uidb36)
            info = RegistrationInfo.objects.get(user_id=uid_int, activation_key=activation_key)
        except RegistrationInfo.DoesNotExist:
            return Response({'status': '400', 'code': 'E_NOT_FOUND',
                             'detail': 'Cannot find user'}, status=404)
        user = info.user
        '''
            If the key is valid and has not expired, we activate user.
            To prevent reactivation of an account which has been
            deactivated by site administrators or click on activate link many times,
            the activation key is reset to the string constant
            RegistrationProfile.ACTIVATED after successful activation.
        '''
        if info.activation_key_expired():
            # If the key is has expired, we delete user account and registration info
            # Can make other options here
            user.delete()
            info.delete()
            return Response({'status': '400', 'code': 'E_INVALID_ACTIVATE_KEY',
                             'detail': code['E_INVALID_ACTIVATE_KEY']}, status=400)
        # If its ok
        user.is_active = True
        user.save()
        info.activation_key = RegistrationInfo.ACTIVATED
        info.save()
        token = Token.objects.get_or_create(user=user)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'Registration successfully', 'token': token[0].key, 'username': user.username,
                         'display_name': user.user_profile.display_name},
                        status=200)


class IsAuth(APIView):
    """ Viewset handle for checking authentication
    """

    @staticmethod
    def get(request):
        """ Check use whether is authenticated
        Returns:
            202 - User is authenticated.
            203 - User is not authenticated.
        """
        if request.user.is_authenticated():
            return Response({'status': '202', 'code': 'OK_LOGIN',
                             'detail': code['OK_LOGIN']}, status=202)

        return Response({'status': '203', 'code': 'E_IS_NOT_LOGIN',
                         'detail': code['E_IS_NOT_LOGIN']}, status=203)


class PasswordResetRequest(APIView):
    serializer_class = ResetPasswordSerializer
    parser_classes = (JSONParser, FormParser,)

    def post(self, request):
        """ Sends an email to the user email address with a link to reset his password.
        Parameters:
            * email
        Return:
            * 200 - Send email to reset password successfully - OK_SEND_EMAIL
            * 400 - E_SEND_EMAIL_FAIL.
                  - E_INVALID_PARAMETER_VALUES.
                  - User already log in cannot reset password - E_IS_LOGIN.

        """
        #if request.user.is_authenticated():
        #    return Response({'status': '400', 'code': 'E_IS_LOGIN',
        #                     'detail': code['E_IS_LOGIN']}, status=400)
        # init form with POST data
        serializer = self.serializer_class(data=request.DATA)
        # validate
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        # Get user by email
        user = get_or_none(User, username=request.DATA['email'])
        if not user:
            return Response({'status': '404', 'code': 'E_USER_NOT_FOUND',
                             'detail': code['E_USER_NOT_FOUND']}, status=404)

        # Generate token
        activation_key = default_token_generator.make_token(user)

        # Information for email, include: subject, link, from email and to email
        subject = "Reset Password"
        # Encode user id
        uidb36 = int_to_base36(user.id)
        # Url will be send to user, this will be replaced by real link
        detail_html = '<b>Hi,</b><br><br>Golfconnect24 was received your reset password request.'
        html_content = detail_html + '<br> <a href="' + 'https://' + request.META[
            'HTTP_HOST'] + '/#/resetpassword/' + uidb36 + '/' + activation_key + '">Click here to reset your password</a>'
        # Message will be send to user
        detail_html = '<br><br><br><b>Chào quý khách,</b><br><br>Golfconnect24 đã nhận được yêu cầu thay đổi mật khẩu của quý khách.'
        html_content += detail_html + '<br> <a href="' + 'https://' + request.META[
            'HTTP_HOST'] + '/#/resetpassword/' + uidb36 + '/' + activation_key + '">Nhấp vào đây để thay đổi mật khẩu</a>'
        # Send email
        send_ok = send_email(subject, html_content, [user.email])

        # Check ok
        if send_ok:
            # Save to the password reset model
            PasswordReset.objects.get_or_create(user=user, activation_key=activation_key)
            return Response({'status': '200', 'code': 'OK_SEND_EMAIL',
                             'detail': code['OK_SEND_EMAIL']},
                            status=200)

        return Response({'status': '400', 'code': 'E_SEND_EMAIL_FAIL',
                         'detail': code['E_SEND_EMAIL_FAIL']}, status=400)


class PasswordResetFromKey(APIView):
    serializer_class = ResetPasswordKeySerializer
    parser_classes = (JSONParser, FormParser,)

    @staticmethod
    def post(request, uidb36, activation_key):
        """ Reset password from key.
            Parameters:
                * new password
                * password_confirmation

            Return:
                * 404 - E_USER_NOT_FOUND
                * 400 - E_INVALID_PARAMETER_VALUES.
                      - User already log in cannot reset password - E_IS_LOGIN.
                * 200 - Reset password successfully - OK_RESET_PASSWORD.
        """
        if request.user.is_authenticated():
            return Response({'status': '400', 'code': 'E_IS_LOGIN',
                             'detail': code['E_IS_LOGIN']}, status=400)

        try:
            # Decode user id
            uid_int = base36_to_int(uidb36)
            # Get PassWordReset instance by checking id, token and reset
            password_reset_key = PasswordReset.objects.get(user_id=uid_int, activation_key=activation_key, reset=False)
            if password_reset_key.has_expired:
                return Response({'status': '400', 'code': 'E_INVALID_ACTIVATE_KEY',
                                 'detail': code['E_INVALID_ACTIVATE_KEY']}, status=400)
        except (ValueError, PasswordReset.DoesNotExist, AttributeError):
            return Response({'status': '404', 'code': 'E_USER_NOT_FOUND',
                             'detail': code['E_USER_NOT_FOUND']}, status=404)

        serializer = ResetPasswordKeySerializer(data=request.DATA, instance=password_reset_key)

        # validate
        if serializer.is_valid():
            instance = serializer.save()
            token = Token.objects.get_or_create(user=instance.user)
            return Response({'status': '200', 'code': 'OK_RESET_PASSWORD',
                             'detail': code['OK_RESET_PASSWORD'], 'token': token[0].key,
                             'username': instance.user.username,
                             'display_name': instance.user.user_profile.display_name}, status=200)
            # in case of errors
        return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                         'detail': serializer.errors}, status=400)

    @staticmethod
    def get(request, uidb36, activation_key):

        if request.user.is_authenticated():
            return Response({'status': '400', 'code': 'E_IS_LOGIN',
                             'detail': code['E_IS_LOGIN']}, status=400)
        try:
            # Decode user id
            uid_int = base36_to_int(uidb36)
            # Get PassWordReset instance by checking id, token and reset
            password_reset_key = PasswordReset.objects.get(user_id=uid_int, activation_key=activation_key, reset=False)
            if password_reset_key.has_expired:
                return Response({'status': '400', 'code': 'E_INVALID_ACTIVATE_KEY',
                                 'detail': code['E_INVALID_ACTIVATE_KEY']}, status=400)
        except (ValueError, PasswordReset.DoesNotExist, AttributeError):
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Cannot find user'}, status=404)

        return Response({'status': '200', 'code': 'OK', 'detail': 'Activation key is OK'}, status=200)


class SocialAuth(APIView):
    permission_classes = (AllowAny,)

    @staticmethod
    @psa()
    def auth_by_token(request, backend):
        backend = request.backend
        user = request.user
        user = backend.do_auth(
            access_token=request.DATA.get('access_token')
        )
        if user and user.is_active:
            return user  # Return anything that makes sense here
        else:
            return None

    def post(self, request, backend):
        auth_token = request.DATA.get('access_token', None)
        if auth_token and backend:
            try:
                user = self.auth_by_token(request, backend)
            except Exception as err:
                return Response(str(err), status=400)
            if user:
                login(request, user)
                expiration = user.social_user.expiration_datetime()
                if expiration:
                    try:
                        request.session.set_expiry(
                            expiration.seconds + expiration.days * 86400
                        )
                    except OverflowError:
                        # Handle django time zone overflow
                        request.session.set_expiry(None)
                token = Token.objects.get_or_create(user=user)
                if backend == 'google-oauth2':
                    user.user_profile.profile_picture = user.user_profile.profile_picture or request.DATA.get('picture', None)
                elif backend == 'facebook':
                    response = requests.get(
                        'https://graph.facebook.com/me',
                        params={'access_token': auth_token,
                                'fields': 'location,hometown,picture,email,gender,birthday,name'}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        img_response = requests.get(
                            'https://graph.facebook.com/v2.3/{}/picture'.format(data['id']),
                            params={'access_token': auth_token,
                                    'type': 'large'}
                        )
                        if img_response.status_code == 200:
                            user.user_profile.profile_picture = user.user_profile.profile_picture or img_response.url
                        else:
                            user.user_profile.profile_picture = user.user_profile.profile_picture or data['picture']['data']['url']
                        user.user_profile.gender = GENDER[data.get('gender','male')]
                        user.email = user.email or data.get('email','')
                user.user_profile.display_name = user.user_profile.display_name or (str(user.first_name) + ' ' + str(user.last_name))
                user.user_profile.save()
                if token[1] and user.email:
                    # send_register_email(user.user_profile.display_name, user.email)
                    send_email_welcome(user.id)
                return Response({'id': user.id,
                                 'status': '200', 'code': 'OK_LOGIN',
                                 'detail': code['OK_LOGIN'],
                                 'token': token[0].key,
                                 'display_name': user.user_profile.display_name,
                                 'picture': user.user_profile.profile_picture,
                                 'gender': user.user_profile.gender,
                                 'handicap_us': user.user_profile.handicap_us,
                                 'email': user.email},
                                status=200)
            else:
                return Response("Bad Credentials", status=403)
        else:
            return Response("Bad request", status=400)


class RegisterMember(APIView):
    @staticmethod
    def post(request):
        serializer = LoginSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)

        user = request.user
        user.username = request.DATA['username'].lower()
        user.set_password(request.DATA['password'])
        user.user_profile.is_member = True
        user.user_profile.date_pass_change = datetime.date.today()
        user.user_profile.save()
        user.save()
        return Response({'status': '200', 'code': 'OK', 'detail': 'Register member successfully'}, status=200)


class RegisterInvite(APIView):
    """ Viewset handle for registration invitation
    """

    @staticmethod
    def post(request):
        key = request.DATA.get('key', '')
        # if not key:
        # return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
        # 'detail': 'Key must be required'}, status=400)
        # inviteID = int(decrypt_val(key))
        try:
            invited_person = EventMember.objects.select_related('event').get(id=int(key))
        except Exception:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Not found'}, status=404)
        request.DATA['username'] = request.DATA['email'] = invited_person.customer.email.lower()
        serializer = RegisterSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        user = User.objects.create(username=request.DATA['username'], email=request.DATA['email'],
                                   first_name=request.DATA['first_name'], last_name=request.DATA['last_name'])
        user.is_active = True
        user.set_password(request.DATA['password'])
        user.user_profile.display_name = str(user.last_name) + ' ' + str(user.first_name)
        user.user_profile.gender = request.DATA['gender']
        user.user_profile.is_member = True
        user.user_profile.save(update_fields=['gender', 'is_member', 'display_name'])
        user.save()

        user_ctype = ContentType.objects.get_for_model(User)
        # invited_person.content_type = user_ctype
        # invited_person.object_id = user.id
        invited_person.user = user
        invited_person.customer = None
        invitation_ctype = ContentType.objects.get_for_model(GolfCourseEvent)
        event = invited_person.event
        detail = str(event.user.user_profile.display_name) + ' mời bạn tham gia sự kiện tại ' + str(
            event.golfcourse.name) + ' vào ngày ' + str(
            event.date_start.strftime('%d-%m-%Y'))
        if event.time:
            detail += ' lúc ' + str(event.time.strftime('%H:%M'))

        detail_en = str(
            event.user.user_profile.display_name) + ' invited you to join the event at ' + str(
            event.golfcourse.name) + ' on ' + str(
            event.date_start.strftime('%d-%m-%Y'))
        if event.time:
            detail += ' at ' + str(event.time.strftime('%H:%M'))

        Notice.objects.create(content_type=invitation_ctype,
                              object_id=event.id,
                              to_user=user,
                              detail=detail,
                              detail_en=detail_en,
                              notice_type='I',
                              from_user=event.user,
                              send_email=False)
        invited_person.save()
        token = Token.objects.get_or_create(user=user)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'Registration successfully', 'token': token[0].key, 'username': user.username,
                         'display_name': user.user_profile.display_name,
                         'gender': user.user_profile.gender,
                         'handicap_us': user.user_profile.handicap_us,
                         'email': user.email},
                        status=200)


class RegisterGame(APIView):
    """ Viewset handle for registration invitation
    """

    @staticmethod
    def post(request):
        key = request.DATA.get('key', '')
        try:
            invited_person = Customer.objects.get(id=int(key))
        except Exception:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Not found'}, status=404)
        request.DATA['username'] = request.DATA['email'] = invited_person.email.lower()
        serializer = RegisterSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        user = User.objects.create(username=request.DATA['username'], email=request.DATA['email'],
                                   first_name=request.DATA['first_name'], last_name=request.DATA['last_name'])
        user.is_active = True
        user.set_password(request.DATA['password'])
        user.user_profile.display_name = str(user.last_name) + ' ' + str(user.first_name)
        user.user_profile.gender = request.DATA['gender']
        user.user_profile.is_member = True
        user.user_profile.profile_picture = invited_person.avatar
        user.user_profile.save(update_fields=['gender', 'is_member', 'display_name', 'profile_picture'])
        user.save()

        game_ctype = ContentType.objects.get_for_model(Game)
        games = Game.objects.only('recorder_id', 'id').filter(event_member__customer=invited_person.id)
        for game in games:
            detail_en = '<a href=/#/profile/' + str(game.recorder_id) + '/>' + str(
                game.recorder.user_profile.display_name) + '</a>' + ' has recorded your game at <b> ' + str(
                game.golfcourse.name) + '</b> on <b> ' + str(game.date_play.strftime('%d-%m-%Y')) + '</b>'
            detail = '<a href=/#/profile/' + str(game.recorder_id) + '/>' + str(
                game.recorder.user_profile.display_name) + '</a>' + ' đã ghi điểm cho bạn ở sân <b> ' + str(
                game.golfcourse) + '</b> vào ngày <b> ' + str(game.date_play.strftime('%d-%m-%Y')) + '</b>'
            Notice.objects.create(content_type=game_ctype,
                                  object_id=game.id,
                                  to_user=user,
                                  detail=detail,
                                  detail_en=detail_en,
                                  notice_type='IN',
                                  from_user_id=game.recorder_id,
                                  send_email=False)
            game.event_member.user = user
            game.event_member.customer = None
            game.event_member.save(update_fields=['user', 'customer'])
        token = Token.objects.get_or_create(user=user)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'Registration successfully', 'token': token[0].key, 'username': user.username,
                         'display_name': user.user_profile.display_name, },
                        status=200)


class RegisterBooking(APIView):
    """ Viewset handle for registration invitation
    """

    @staticmethod
    def post(request):
        key = request.DATA.get('key', '')
        try:
            invited_person = BookedPartner.objects.get(id=int(key))
        except Exception:
            return Response({'status': '404', 'code': 'E_NOT_FOUND',
                             'detail': 'Not found'}, status=404)
        request.DATA['username'] = request.DATA['email'] = invited_person.email.lower()
        serializer = RegisterSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        user = User.objects.create(username=request.DATA['username'], email=request.DATA['email'],
                                   first_name=request.DATA['first_name'], last_name=request.DATA['last_name'])
        user.is_active = True
        user.set_password(request.DATA['password'])
        user.user_profile.display_name = str(user.last_name) + ' ' + str(user.first_name)
        user.user_profile.gender = request.DATA['gender']
        user.user_profile.is_member = True
        user.user_profile.save(update_fields=['gender', 'is_member', 'display_name'])
        user.save()

        game_ctype = ContentType.objects.get_for_model(BookedTeeTime)
        teetime = BookedTeeTime.objects.get(teetime=invited_person.teetime)
        detail_en = '<a href=/#/profile/' + str(teetime.user_id) + '/>' + str(
            teetime.user.user_profile.display_name) + '</a>' + ' has recorded your game at <b> ' + str(
            teetime.golfcourse.name) + '</b> on <b> ' + str(
            teetime.date_to_play.strftime('%d-%m-%Y')) + '</b> on <b> ' + str(
            teetime.date_to_play.strftime('%d-%m-%Y')) + '</b>'
        detail = '<a href=/#/profile/' + str(teetime.user_id) + '/>' + str(
            teetime.user.user_profile.display_name) + '</a>' + ' đã ghi điểm cho bạn ở sân <b> ' + str(
            teetime.golfcourse.name) + '</b> lúc <b>' + str(
            teetime.time_to_play.strftime('%H:%M')) + '</b> vào ngày <b> ' + str(
            teetime.date_to_play.strftime('%d-%m-%Y')) + '</b>'
        Notice.objects.create(content_type=game_ctype,
                              object_id=teetime.id,
                              to_user=user,
                              detail=detail,
                              detail_en=detail_en,
                              notice_type='IN',
                              from_user=teetime.user,
                              send_email=False)
        invited_person.user = user
        invited_person.save(update_fields=['user'])
        token = Token.objects.get_or_create(user=user)
        return Response({'status': '200', 'code': 'OK',
                         'detail': 'Registration successfully', 'token': token[0].key, 'username': user.username,
                         'display_name': user.user_profile.display_name,
                         'email': user.email},
                        status=200)


class DeviceViewSet(APIView):
    parser_classes = (JSONParser, FormParser,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = UserDeviceSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response({'status': '400', 'code': 'E_INVALID_PARAMETER_VALUES',
                             'detail': serializer.errors}, status=400)
        device = configure_device(user_id=request.user.id,
                                  device_id=request.DATA['device_id'],
                                  device_type=request.DATA['device_type'],
                                  api_version=request.DATA.get('version',1))
        if not device:
            return Response({'status': 404, 'detail': 'Device not found.'}, status=404)

        return Response(device, status=200)


def configure_device(user_id, device_id, device_type, api_version):
    device = UserDevice.objects.filter(device_id=device_id).first()
    if not device:
        return None

    user_endpoint_arn = get_endpoint_arn(device_id, device_type)
    set_endpoint_enabled(user_endpoint_arn)

    if device:
        device.user_id = user_id
        device.device_type = device_type
        device.push_token = user_endpoint_arn
        device.api_version = api_version
        device.save()
    else:
        device = UserDevice.objects.create(user_id=user_id,
                                           device_id=device_id,
                                           push_token=user_endpoint_arn,
                                           device_type=device_type,
                                           api_version=api_version)

    serializer = UserDeviceSerializer(device)
    return serializer.data



