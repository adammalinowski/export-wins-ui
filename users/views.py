from django.conf import settings
from django.contrib.auth import login, logout
from django.views.generic import FormView, RedirectView

from alice.helpers import rabbit

from .forms import LoginForm


class LoginView(FormView):

    form_class = LoginForm
    template_name = "users/login.html"

    def form_valid(self, form):
        login(self.request, form.user)
        response = FormView.form_valid(self, form)
        response.set_cookie("alice", form.user.token)
        return response

    def get_success_url(self):
        return self.request.GET.get("next") or "/"


class LogoutView(RedirectView):

    url = "/"

    def get(self, request, *args, **kwargs):
        logout(self.request)  # Local
        rabbit.get(settings.LOGOUT_AP)  # Remote
        response = RedirectView.get(self, request, *args, **kwargs)
        response.delete_cookie("alice")
        return response
