from django import forms
from django.conf import settings

from ui.forms import BootstrappedForm
from alice.helpers import rabbit


class LoginForm(BootstrappedForm):

    email = forms.EmailField()
    password = forms.CharField(widget=forms.widgets.PasswordInput)

    def __init__(self, *args, **kwargs):
        BootstrappedForm.__init__(self, *args, **kwargs)
        self.session_cookie = None

    def clean_email(self):
        if "email" in self.cleaned_data:
            return self.cleaned_data["email"].lower().strip()

    def clean_password(self):
        if "password" in self.cleaned_data:
            return self.cleaned_data["password"].strip()

    def clean(self):

        cleaned_data = BootstrappedForm.clean(self)

        # Don't bother to continue if we've already got problems
        if self._errors:
            return cleaned_data

        # Try logging in on data server
        self._login()

        return self.cleaned_data

    def _login(self):

        response = rabbit.post(settings.LOGIN_AP, data={
            "username": self.cleaned_data["email"],
            "password": self.cleaned_data["password"]
        })

        # Anything other than 200 means the data server rejected the login
        if not response.status_code == 200:

            error_message = response.json().get("non_field_errors")
            if error_message:
                raise forms.ValidationError(error_message[0])

            forms.ValidationError(
                "There was a problem logging in.  Please try again later.")

        # Data server has logged user in, get user data and session cookie from
        # data server and pass to view for creating the JWT
        self.user = response.json()
        self.session_cookie = self._get_cookie(response.cookies)

    def _get_cookie(self, cookies):
        for cookie in cookies:
            if cookie.name == "sessionid":
                return cookie
        raise Exception("The data server didn't return a session cookie")
