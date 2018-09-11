# -*- coding: utf-8 -*-
import datetime, json, django
from socket import gethostbyaddr
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from v2.utils.code import HTTP_STATUS_CODES, browsers, engines

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

class TrackingRequest(models.Model):
    response = models.SmallIntegerField(choices=HTTP_STATUS_CODES, default=200)
    method = models.CharField(default='GET', max_length=7)
    path = models.CharField(max_length=255)
    time = models.DateTimeField(default=now, db_index=True)

    # User infomation
    ip = models.GenericIPAddressField()
    user = models.ForeignKey(User, blank=True, null=True, related_name='user_request')
    referer = models.URLField(max_length=255, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ('-time',)
        default_permissions = ('add', 'change', 'delete', 'view')

    def __str__(self):
        return '[{0}] {1} {2} {3}'.format(self.time, self.method, self.path, self.response)

    def get_user(self):
        return User.objects.get(pk=self.user_id)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def from_http_request(self, request, response=None, commit=True):
        # Request infomation
        self.method = request.method
        self.path = request.path[:255]

        # User infomation
        self.ip = self.get_client_ip(request)
        self.referer = request.META.get('HTTP_REFERER', '')[:255]
        self.user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        self.language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')[:255]

        if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated'):
            is_authenticated = request.user.is_authenticated
            if django.VERSION < (1, 10):
                is_authenticated = is_authenticated()
            if is_authenticated:
                self.user = request.user

        if response:
            self.response = response.status_code

            if (response.status_code == 301) or (response.status_code == 302):
                self.redirect = response['Location']

        if commit:
            self.save()

    @property
    def browser(self):
        if not self.user_agent:
            return

        if not hasattr(self, '_browser'):
            self._browser = browsers.resolve(self.user_agent)
        return self._browser[0]

    @property
    def keywords(self):
        if not self.referer:
            return

        if not hasattr(self, '_keywords'):
            self._keywords = engines.resolve(self.referer)
        if self._keywords:
            return ' '.join(self._keywords[1]['keywords'].split('+'))

    @property
    def hostname(self):
        try:
            return gethostbyaddr(self.ip)[0]
        except Exception:  # socket.gaierror, socket.herror, etc
            return self.ip