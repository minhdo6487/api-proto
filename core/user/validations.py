from django.contrib.auth.models import User
from django.db.models import Q

from utils.django.models import get_or_none


def email_exist(current_user, email):
    """
        Validate email if an email already exist or not
        This is mainly used in serializer
        Parameter:
            - currentUser: User object of current user
            - email: email to check
        return:
            - True: if email already exists
            - False: if email does not eixist
    """
    # This is the case in registration, when there's no current user
    if current_user is None:
        user = get_or_none(User, email=email)
    else:
        user = get_or_none(User, ~Q(id=current_user.id), email=email)

    if user is None:
        return False
    else:
        return True