from dateutil.parser import parse as date_parser
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from alice.helpers import rabbit

from .forms import WinForm, ConfirmationForm


class NewWinView(LoginRequiredMixin, FormView):

    template_name = "wins/new.html"
    form_class = WinForm

    def form_valid(self, form):
        form.save()
        return FormView.form_valid(self, form)

    def get_success_url(self):
        return reverse("thanks")

    def get_form_kwargs(self):
        r = FormView.get_form_kwargs(self)
        r["request"] = self.request
        return r


class ConfirmationView(FormView):

    template_name = "wins/confirmation.html"
    form_class = ConfirmationForm

    ACCEPTANCE_WINDOW = 7  # Days

    class SecurityException(Exception):
        pass

    def dispatch(self, request, *args, **kwargs):

        try:
            win = self._check_outside_window(kwargs["pk"], request)
            self._check_already_submitted(win["id"], request)
        except self.SecurityException as e:
            return self.denied(request, message=str(e), *args, **kwargs)

        return FormView.dispatch(self, request, *args, **kwargs)

    def get_success_url(self):
        return reverse("thanks")

    def denied(self, request, *args, **kwargs):
        return self.response_class(
            request=request,
            template="wins/confirmation-denied.html",
            context={"message": kwargs["message"]},
            using=self.template_engine
        )

    def _check_outside_window(self, pk, request):

        now = timezone.now()

        win_url = "{}{}/".format(settings.WINS_AP, pk)
        win = rabbit.get(win_url, request=request)

        if not win.status_code == 200:
            raise self.SecurityException("That key appears to be invalid")

        win = win.json()

        created = date_parser(win["created"])
        window_extent = created + relativedelta(days=self.ACCEPTANCE_WINDOW)

        if now > window_extent:
            raise self.SecurityException(
                "This record is no longer available for review.")

        return win

    @staticmethod
    def _check_already_submitted(pk, request):
        ap = settings.CONFIRMATIONS_AP
        confirmation_url = "{}?win__id={}".format(ap, pk)
        confirmation = rabbit.get(confirmation_url, request=request).json()

        if bool(confirmation["count"]):
            raise self.SecurityException("This confirmation was already completed.")


class ThanksView(TemplateView):
    """
    Doubles as the thank-you page for both the win creation and customer
    responses.
    """

    template_name = "wins/thanks.html"
