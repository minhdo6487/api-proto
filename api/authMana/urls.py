from django.conf.urls import patterns, url
from django.contrib import admin

from api.authMana.views import LoginView, LogoutView, RegisterView, PasswordResetRequest, \
    PasswordResetFromKey, RegisterConfirmView, SocialAuth, RegisterMember, RegisterInvite, RegisterGame, DeviceViewSet

admin.autodiscover()

forgot_password_urls = patterns('',
                                url(r'^password/reset/$', PasswordResetRequest.as_view()),
                                url(r'^password/reset/(?P<uidb36>[0-9A-Za-z]+)/(?P<activation_key>.+)/$',
                                    PasswordResetFromKey.as_view()), )

register_urls = patterns('', url(r'^register/$', RegisterView.as_view()),
                         url(r'^register/(?P<uidb36>[0-9A-Za-z]+)/(?P<activation_key>.+)/$',
                             RegisterConfirmView.as_view()))
register_invite_urls = patterns('', url(r'^register-invite/', RegisterInvite.as_view()))
register_game_urls = patterns('', url(r'^register-game/', RegisterGame.as_view()))
social_urls = patterns('', url(r'^auth/(?P<backend>[^/]+)/', SocialAuth.as_view()))

member_urls = patterns('', url(r'^auth-member/', RegisterMember.as_view()))

user_device = patterns('', url(r'^user-device/$', DeviceViewSet.as_view()))

urlpatterns = user_device + register_game_urls + register_invite_urls + social_urls + forgot_password_urls + register_urls + member_urls + \
              patterns('', url(r'^login/', LoginView.as_view()),
                       url(r'^logout/', LogoutView.as_view()),
                       url(r'^api-token-auth/', 'rest_framework.authtoken.views.obtain_auth_token'),)