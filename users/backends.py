from django.conf import settings
from django.contrib.auth.models import User

from alice.helpers import rabbit


class RelayedBackend(object):

    def authenticate(self, username=None, password=None):

        response = rabbit("post", settings.LOGIN_AP, data={
            "username": username,
            "password": password
        })

        # Anything other than 200 means the data server rejected the login
        if not response.status_code == 200:
            return None

        user, __ = User.objects.get_or_create(
            username=username, defaults={"password": "*"})

        # Attach the data server's token to the user object temporarily so that
        # the LoginView can put it into a cookie.
        user.token = response.json()["token"]

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
