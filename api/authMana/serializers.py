from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import serializers

from core.user.models import UserDevice
from utils.django.models import get_or_none
from utils.rest.code import code


PASSWORD_MAX_LENGTH = User._meta.get_field('password').max_length
EMAIL_MAX_LENGTH = User._meta.get_field('email').max_length
USERNAME_MAX_LENGTH = User._meta.get_field('username').max_length
PASSWORD_MIN_LENGTH = 8


class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password',)

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if len(password) < PASSWORD_MIN_LENGTH:
            raise serializers.ValidationError(code['E_INVALID_PASSWORD'])
        return attrs


class RegisterSerializer(serializers.ModelSerializer):

    email = serializers.CharField(required=True, max_length=EMAIL_MAX_LENGTH)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    password_confirmation = serializers.CharField(required=True, max_length=PASSWORD_MAX_LENGTH)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name', 'password_confirmation')

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if len(password) < PASSWORD_MIN_LENGTH:
            raise serializers.ValidationError(code['E_INVALID_PASSWORD'])
        return attrs

    @staticmethod
    def validate_username(attrs, source):
        """ Check duplicated username
        """
        username = attrs[source].lower()
        if User.objects.filter(username=username).count() > 0:
            raise serializers.ValidationError(code['E_DUPLICATE_USERNAME'])

        return attrs


    @staticmethod
    def validate_password_confirmation(attrs, source):
        """ Password confirmation check
        """
        password_confirmation = attrs[source]
        password = attrs['password']
        if password_confirmation != password:
            raise serializers.ValidationError(code['E_PASSWORD_MISMATCH'])
        return attrs

    def to_native(self, obj):
        """ Remove password and confirmation password field when serializing an object
        """
        ret = super(RegisterSerializer, self).to_native(obj)
        del ret['password_confirmation']
        del ret['password']
        return ret


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, max_length=PASSWORD_MAX_LENGTH)

    @staticmethod
    def validate_email(attrs, source):
        """ ensure email is in the database
        """
        email = attrs[source]
        user = get_or_none(User, username=email)
        if not user:
            raise serializers.ValidationError(code['E_EMAIL_NOT_FOUND'])
        return attrs


class ResetPasswordKeySerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=PASSWORD_MAX_LENGTH
    )
    password_confirmation = serializers.CharField(
        max_length=PASSWORD_MAX_LENGTH
    )

    @staticmethod
    def validate_password(attrs, source):
        """ Check valid password
        """
        password = attrs[source]
        if len(password) < PASSWORD_MIN_LENGTH:
            raise serializers.ValidationError(code['E_INVALID_PASSWORD'])
        return attrs

    @staticmethod
    def validate_password_confirmation(attrs, source):
        """ Password2 check
        """
        password_confirmation = attrs[source]
        password = attrs['password']

        if password_confirmation != password:
            raise serializers.ValidationError(code['E_PASSWORD_MISMATCH'])

        return attrs

    def restore_object(self, attrs, instance):
        """ Change password
        """
        user = instance.user
        user.set_password(attrs["password"])
        user.save()
        # mark password reset object as reset
        instance.reset = True
        instance.save()

        return instance

    def to_native(self, obj):
        """ Remove password and confirmation password field when serializing an object
        """
        ret = super(RegisterSerializer, self).to_native(obj)
        del ret['password_confirmation']
        del ret['password']
        return ret


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        exclude = ('user',)