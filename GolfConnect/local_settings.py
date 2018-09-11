"""
Django settings for GolfConnect project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import raven
from datetime import timedelta
from celery.schedules import crontab

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '40-a1-p=134*l#%*_q%2u-y!2qw8z#^3qr8f&d9u_q$e0t*bdr')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'no').lower() in ['yes', 'true', '1']

TEMPLATE_DEBUG = DEBUG
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,golfconnect24.com').split(',')]

SITE_ID = 1
ANONYMOUS_USER_ID = -1
# Application definition
USE_L10N = True
MEDIA_ROOT = 'media/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
# MEDIA_URL = 'http://127.0.0.1:8000/media/qr_codes/'
# ADMIN_MEDIA_PREFIX = '/admin-media/'
# Configure for sign with third party
SOCIAL_AUTH_RAISE_EXCEPTIONS = True
RAISE_EXCEPTIONS = True
# Configure for sign with facebook
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('SOCIAL_AUTH_FACEBOOK_KEY', '338827976289197')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('SOCIAL_AUTH_FACEBOOK_SECRET', 'your app secret here')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email',  'user_friends', 'friends_location']

NOTIFY_JOIN_LEFT_EVENT = os.environ.get('NOTIFY_JOIN_LEFT_EVENT', 1)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '544423833090-qmra9t5h1lvc4a1fbvvve9eu2bbti9of.apps.googleusercontent.com')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', 'a99BkdzzPDAjpddS8rrWQ_0t')

S3_BUCKET = os.environ.get('S3_BUCKET', 'media.golfconnect24.com')
S3_AWSKEY = os.environ.get('S3_AWSKEY', 'AKIAIPBAQUYRY6VWIA2Q')
S3_SECRET = os.environ.get('S3_SECRET', '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')
SNS_REGION = os.environ.get('SNS_REGION', 'ap-southeast-1')

ANDROID_SNS_ARN_PROD = os.environ.get('ANDROID_SNS_ARN_PROD',
                                      'arn:aws:sns:ap-southeast-1:500556504508:app/GCM/prod-gc24-android')
ANDROID_SNS_ARN_DEV = os.environ.get('ANDROID_SNS_ARN_DEV',
                                     'arn:aws:sns:ap-southeast-1:500556504508:app/GCM/dev-gc24-android')
IOS_SNS_ARN_DEV = os.environ.get('ANDROID_SNS_ARN_DEV',
                                 'arn:aws:sns:ap-southeast-1:500556504508:app/APNS/dev-gc24-ios')
IOS_SNS_ARN_PROD = os.environ.get('ANDROID_SNS_ARN_DEV',
                                  'arn:aws:sns:ap-southeast-1:500556504508:app/APNS/prod-gc24-ios')


GG_SERVER_KEY = 'AIzaSyBOMWldmaAfoQgj2A_4p4ITeA0xKIOUWI4'
GOOGLE_MAP_API_KEY = os.environ.get('GOOGLE_MAP_API_KEY', 'AIzaSyBrbiRR1EM2y1qdjeBM8PjSwBA7BXsR2ZA')

CURRENT_ENV = os.environ.get('CURRENT_ENV', 'dev')

INSTALLED_APPS = (
    'core.fixapp',
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'haystack',
    'rest_framework',
    'rest_framework.authtoken',
    'django_extensions',
    'corsheaders',
    'psycopg2',
    'guardian',
    'django_user_agents',
    'social.apps.django_app.default',
    'reversion',
    'import_export',
    'core.location',
    'core.user',
    'core.gcauth',
    'core.friend',
    'core.golfcourse',
    'core.customer',
    'core.teetime',
    'core.booking',
    'core.game',
    'core.category',
    'core.post',
    'core.like',
    'core.comment',
    'core.checkin',
    'core.gallery',
    'core.advertise',
    'core.messsage',
    'core.notice',
    'core.invitation',
    'core.realtime',
    'core.playstay',
    'v2.core.trackrequest',
    'v2.core.geohash',
    'v2.core.questionair',
    'v2.core.eventqueue',
    'v2.core.localindex',
    'v2.core.chatservice',
    'v2.core.bookinghis',

    'api.businessMana',
    'api.educationMana',
    'api.locationMana',
    'api.buggyMana',
    'api.clubsetMana',
    'api.userMana',
    'api.authMana',
    'api.bookingMana',
    'api.checkinMana',
    'api.friendMana',
    'api.commentMana',
    'api.likeMana',
    'api.postMana',
    'api.golfcourseMana',
    'api.gameMana',
    'api.golfcourseeventMana',
    'api.teetimeMana',
    'api.customerMana',
    'api.galleryMana',
    'api.advertiseMana',
    'api.messageMana',
    'api.noticeMana',
    'api.forumMana',
    'api.realtimeMana',
    'api.playstayMana',
    'v2.api.gc_eventMana',
    'v2.api.subgameMana',
    'v2.api.notify',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social.apps.django_app.middleware.SocialAuthExceptionMiddleware',
    'v2.utils.middleware.Apiv2Middleware',
)

ROOT_URLCONF = 'GolfConnect.urls'

WSGI_APPLICATION = 'GolfConnect.wsgi.application'

SILKY_PYTHON_PROFILER = True
# http://www.stickpeople.com/projects/python/win-psycopg/
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql_psycopg2'),
        'NAME': os.environ.get('DB_NAME', 'test_gc'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '12345678'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'TEST': {
            'NAME': 'test_golfconnect',
        }
    }
}


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Saigon'

USE_I18N = True


USE_TZ = True


"""
    registration setting
    http://www.michelepasin.org/blog/2011/01/14/setting-up-django-registration/
"""

ACCOUNT_ACTIVATION_DAYS = 7
# EMAIL_USE_TLS = os.environ.get('SMTP_STARTTLS', 'true') in ['true', 'yes', '1']
# EMAIL_HOST = os.environ.get('SMTP_HOST', 'box.ludiino.com')
# EMAIL_PORT = os.environ.get('SMTP_PORT', 587)
# EMAIL_HOST_USER = os.environ.get('SMTP_USER', 'no-reply@golfconnect24.com')
# EMAIL_HOST_PASSWORD = os.environ.get('SMTP_PASS', 'LeatherMoleCoronation')
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.mailtrap.io'
EMAIL_HOST_USER = 'b1c68e128e5077'
EMAIL_HOST_PASSWORD = '433f19769f7c73'
EMAIL_PORT = '2525'

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
SETTINGS_PATH = os.path.dirname(os.path.dirname(__file__))
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
    },
}
# HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

REST_FRAMEWORK = {
    # 'PAGINATE_BY': 10,
    # 'PAGINATE_BY_PARAM': 'page_size',

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}


AUTHENTICATION_BACKENDS = (
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GooglePlusAuth',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

CORS_ORIGIN_WHITELIST = (
    # 'localhost:9000'
)

CORS_ORIGIN_REGEX_WHITELIST = ('^(https?://)?(\w+\.)?google\.com$', )

CORS_ALLOW_METHODS = (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
)

CORS_ALLOW_HEADERS = (
    'x-requested-with',
    'content-type',
    'accept',
    'origin',
    'authorization',
    'x-csrftoken'
)
SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'social.pipeline.mail.mail_validation',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details',
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)
TEMPLATE_DIRS = (
    'media/email_template/',
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

# Configure cache servers and binding settings.py
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_DB = os.environ.get('REDIS_DB', 0)

BROKER_URL = os.environ.get('REDIS_URI', 'redis://localhost:6379/0')
# BROKER_URL = "amqp://guest:guest@localhost:5672//"
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URI', 'redis://localhost:6379')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERYBEAT_SCHEDULE = {
    'check-running-discount': {
        'task': 'GolfConnect.celery.restart_deal_real_time',
        'schedule': timedelta(seconds=60),
        'args': {}
    },

    'push_notification_tick': {
        'task': 'GolfConnect.celery.push_notification_tick',
        'schedule': crontab(minute='*/1'),
        'args': {},
    }
}

# Configure xmpp server
XMPP_HOST = os.environ.get('XMPP_HOST', '23.94.37.3')
XMPP_PORT = os.environ.get('XMPP_PORT', 5280)

# PAYMERCHANTCODE = os.environ.get('PAYMERCHANTCODE', "GOLFCONNECT24COM")
# PAYPASSCODE = os.environ.get('PAYPASSCODE', "GOLFCONNECT24COMqHys4Jsa8Z")
# PAYSECRETKEY = os.environ.get('PAYSECRETKEY', "GOLFCONNECT24COMaZdgZ5ZHsZ")
# PAYURL = os.environ.get('PAYURL', "mi.123pay.vn")

PAYURL="sandbox.123pay.vn"
PAYMERCHANTCODE="MICODE"
PAYPASSCODE="MIPASSCODE"
PAYSECRETKEY="MIKEY"

# ./manage.py schemamigration southtut --initial
# ./manage.py schemamigration southtut --auto
#sudo kill `sudo lsof -t -i: 8000`

# config raven
raven_dsn = os.environ.get('RAVEN_DSN', '')
if raven_dsn:
    INSTALLED_APPS += (
        'raven.contrib.django.raven_compat',
    )
    RAVEN_CONFIG = {
        'dsn': raven_dsn,
    }

# config for sending report email
ADMIN_EMAIL_RECIPIENT = [email.strip() for email in
                         os.environ.get('ADMIN_EMAIL_RECIPIENT', 'htphuong290@gmail.com').split(',')]

SYSADMIN_EMAIL = [email.strip() for email in
                  os.environ.get('SYSADMIN_EMAIL', 'htphuong290@gmail.com').split(',')]
