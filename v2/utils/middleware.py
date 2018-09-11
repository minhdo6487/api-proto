# -*- coding: utf-8 -*-
import json
from django.shortcuts import redirect
from django.core.urlresolvers import resolve, Resolver404
from django.http import HttpResponse

from v2.core.trackrequest.models import TrackingRequest
from v2.utils.config import IGNORE_PATHS
from core.user.models import UserProfile
#from functools import map
try:
    # needed to support Django >= 1.10 MIDDLEWARE
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # needed to keep Django <= 1.9 MIDDLEWARE_CLASSES
    MiddlewareMixin = object


class Apiv2Middleware(MiddlewareMixin):
    def process_request(self, request):
        #check_in_list = sum(map(lambda x: (request.path.count(x) or 0), IGNORE_PATHS))
        #if '/api/v2/' in request.path and not check_in_list and getattr(request, 'user', False):
            # Tuan Ly: Put condition to check if this user has profile or not
            # from rest_framework.response import Response
            # return Response({'status': '200', 'code': 'OK'}, status=200)
        #    user = UserProfile.objects.filter(user_id=request.user.id).first()
        #    version = 0 if not user else user.version
        #    if version == 1:
        #        content = {'status': '400', 'code': 'USER_NONE_PROFILE', 'detail':'Please fill to continue'}
        #        data = json.dumps(content)
        #        return HttpResponse(content=data,content_type='application/json',status=400,reason='USER_NONE_PROFILE')
        try:
            resolve(request.path)
        except Resolver404:
            request.path = request.path.replace('/api/v2/','/api/')
            request.path_info = request.path_info.replace('/api/v2/','/api/')
    def process_response(self, request, response):
        r = TrackingRequest()
        if 'gc24/assmin' in request.path:
            return response
        r.from_http_request(request, response)
        return response
