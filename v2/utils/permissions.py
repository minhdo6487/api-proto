import re

from rest_framework import permissions

from core.golfcourse.models import GolfCourse, GolfCourseStaff
from utils.django.models import get_or_none
# from Crypto.Cipher import AES
# import base64
# from GolfConnect.settings import SECRET_KEY
PATTERN = r'(.*)-(.*)'

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the user.
        return obj.owner == request.user


class UserIsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the user.
        return obj.user == request.user


class RequestUserIsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to check for friend request owner
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the user.
        return obj.fromuser == request.user


class UserIsOwnerOrDenie(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsNotAuthenticated(permissions.IsAuthenticated):
    """
    Restrict access only to unauthenticated users.
    """
    def has_permission(self, request, view, obj=None):
        if request.user and request.user.is_authenticated():
            return False
        else:
            return True

class IsGolfStaff(permissions.BasePermission):
    """
    Restrict access only to unauthenticated users.
    """
    def has_permission(self, request, view, obj=None):
        if request.user and GolfCourseStaff.objects.filter(user=request.user).exists():
            return True
        else:
            return False

def IsPassword(request):
    if not request.user.check_password(request.DATA['password']):
            return False
    return True


class IsGolfAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        golfcourse_id = request.DATA.get('golfcourse', '')
        if golfcourse_id:
            golfcourse = get_or_none(GolfCourse, id=golfcourse_id)
            if golfcourse:
                groups = request.user.groups.all()
                for group in groups:
                    match = re.match(PATTERN, group.name, re.I | re.M)
                    if match:
                        if match.group(1) == golfcourse.name:
                            if match.group(2) == 'Admin':
                                return True
        return False

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        gc_name = obj.golfcourse.name
        groups = request.user.groups.all()
        for group in groups:
            match = re.match(PATTERN, group.name, re.I | re.M)
            if match:
                if match.group(1) == gc_name:
                    if match.group(2) == 'Admin':
                        return True
        return False

