from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.encoding import force_text

from django.http import HttpResponseRedirect, QueryDict
from django.shortcuts import resolve_url
from django.utils.six.moves.urllib.parse import urlparse, urlunparse


class LoginRequiredMixin(object):
    """
    Just like django.contrib.auth.mixins.LoginRequiredMixin, but with the
    majority of the overridable stuff in that class stripped out.

    This is only here because attempting to import that class causes an
    explosion since the file it lives in imports things that are
    database-dependent.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.alice_session_id:
            return self.redirect_to_login(
                self.request.get_full_path(),
                force_text(settings.LOGIN_URL)
            )
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)

    def redirect_to_login(self, next, login_url=None):
        """
        Redirects the user to the login page, passing the given 'next' page
        """
        resolved_url = resolve_url(login_url or settings.LOGIN_URL)

        login_url_parts = list(urlparse(resolved_url))
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[REDIRECT_FIELD_NAME] = next
        login_url_parts[4] = querystring.urlencode(safe='/')

        return HttpResponseRedirect(urlunparse(login_url_parts))
