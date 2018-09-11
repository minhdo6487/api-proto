import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.conf import settings


class PasswordReset(models.Model):
    """ Password reset Key
    """
    user = models.ForeignKey(User)

    activation_key = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=now)
    reset = models.BooleanField(default=False)

    def _activation_key_expired(self):
        """ Determine whether activation key has expired,
        return True if the key has expired.
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.timestamp + expiration_date <= now()

    has_expired = property(_activation_key_expired)


class RegistrationInfo(models.Model):
    """ Stores an activation key for using during user account registration.
    """
    ACTIVATED = 'ALREADY_ACTIVATED'
    user = models.ForeignKey(User)
    activation_key = models.CharField(max_length=40)

    def activation_key_expired(self):
        """
        Determine whether activation key has expired,
        return True if the key has expired.

        1. If the user has already activated, the key will have been
        reset to ALREADY_ACTIVATED. Re-activating is not permitted,
        and so this method returns True in this case.

        2.if date is less than or equal to the current date,
        the key has expired and this method returns True.
        """

        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.activation_key == self.ACTIVATED or \
               (self.user.date_joined + expiration_date <= now())