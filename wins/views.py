import os
from dateutil.parser import parse as date_parser
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from .forms import WinForm, ConfirmationForm
from alice.braces import LoginRequiredMixin
from alice.helpers import rabbit


class MyWinsView(TemplateView, LoginRequiredMixin):
    """ View a list of all Wins of logged in User """

    template_name = 'wins/my-wins.html'

    def get_context_data(self, **kwargs):
        context = TemplateView.get_context_data(self, **kwargs)

        url = settings.WINS_AP + '?user__id=' + str(self.request.user.id)
        wins = rabbit.get(url, request=self.request).json()
        context['wins'] = wins
        return context


def get_win(win_id, request):
    url = settings.WINS_AP + '?id=' + win_id
    resp = rabbit.get(url, request=request)
    if resp.status_code != 200:
        raise Http404
    else:
        return resp.json()['results'][0]


def get_win_advisors(win_id, request):
    url = settings.ADVISORS_AP + '?win__id=' + win_id
    resp = rabbit.get(url, request=request)
    if resp.status_code != 200:
        raise Http404
    else:
        return resp.json()['results']


class WinView(TemplateView, LoginRequiredMixin):
    """ View details of a Win of logged in User """

    template_name = 'wins/win-details.html'

    def get_context_data(self, **kwargs):
        context = TemplateView.get_context_data(self, **kwargs)
        context['win'] = get_win(kwargs['pk'], self.request)
        return context


class WinCompleteView(TemplateView, LoginRequiredMixin):
    """ Mark win complete """

    template_name = 'wins/win-complete.html'

    def get_context_data(self, **kwargs):
        context = TemplateView.get_context_data(self, **kwargs)
        context['win'] = get_win(kwargs['pk'], self.request)
        return context

    def post(self, *args, **kwargs):
        """ POST means user has confirmed they want to submit """

        rabbit.push(
            settings.WINS_AP + kwargs['pk'] + '/',
            {'complete': True},
            self.request,
            'patch',
        )
        return redirect('complete-win-success')


class BaseWinFormView(FormView, LoginRequiredMixin):
    """ Base class for adding and editing Wins """

    template_name = "wins/win-form.html"
    form_class = WinForm

    def get_form_kwargs(self):
        kwargs = FormView.get_form_kwargs(self)
        kwargs["request"] = self.request
        return kwargs


class NewWinView(BaseWinFormView):
    """ Create a new Win """

    def form_valid(self, form):
        """ If form is valid, create on data server """
        form.create()
        return FormView.form_valid(self, form)

    def get_success_url(self):
        "New Export Win saved"
        "Thank you for submitting a new Export Win"
        "The details of this win will be forwarded to the customer for"
        # if you don't want that to happen, click here.

        return reverse("new-win-success")


class EditWinView(BaseWinFormView):
    """ Edit a Win of logged in User """

    def get_initial(self):
        # save here for context data, can't get in init because self.kwargs
        # gets set in `view`, create by `as_view`
        self.win = get_win(self.kwargs['pk'], self.request)

        initial = self.win
        initial['date'] = date_parser(initial['date']).strftime('%m/%Y')

        # add advisor data somehow...
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['win'] = self.win
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['exclude_non_editable'] = True
        kwargs['advisors'] = get_win_advisors(self.kwargs['pk'], self.request)
        return kwargs

    def form_valid(self, form):
        """ If form is valid, update on data server """

        form.update(self.kwargs['pk'])
        return FormView.form_valid(self, form)

    def get_success_url(self):
        if self.request.POST.get('send'):
            return reverse("win-complete", kwargs={'pk': self.kwargs['pk']})
        else:
            return reverse("edit-win-success")


class ConfirmationView(FormView):
    """ Create a new Customer Response """

    template_name = "wins/confirmation-form.html"
    form_class = ConfirmationForm

    # limit the number of days form may be accessed after win submission for
    # security purposes
    ACCEPTANCE_WINDOW = 30

    sample = False  # is this a sample win, which will not be saved?

    class SecurityException(Exception):
        pass

    def dispatch(self, request, *args, **kwargs):
        """ Override dispatch to do some checks before displaying form """

        # quick hack to show sample customer response form with a known test win
        if request.path.endswith('sample/'):
            kwargs['pk'] = os.getenv('SAMPLE_WIN', 'notconfigured')
            self.kwargs['pk'] = kwargs['pk']
            self.sample = True

        try:
            self.win_dict = self._get_valid_win(kwargs["pk"], request)
        except self.SecurityException as e:
            return self._deny_access(request, message=str(e))

        return FormView.dispatch(self, request, *args, **kwargs)

    def get_form_kwargs(self):
        """ Setup additional kwargs for the form """

        kwargs = FormView.get_form_kwargs(self)
        kwargs["request"] = self.request
        kwargs["initial"]["win"] = self.kwargs["pk"]
        return kwargs

    def get_context_data(self, **kwargs):
        """ Get Win data for use in the template

        Not sure why this gets the schema, doesn't seem necessary

        """
        schema_url = "{}schema/".format(settings.WINS_AP)
        win_schema = rabbit.get(schema_url).json()

        for key, value in self.win_dict.items():
            if key == "date":
                value = date_parser(value)
            win_schema[key]["value"] = value

        context = FormView.get_context_data(self, **kwargs)
        context.update({"win": win_schema})
        return context

    def get_success_url(self):
        return reverse("confirmation-thanks")

    def form_valid(self, form):
        if not self.sample:
            form.save()
        return FormView.form_valid(self, form)

    def _deny_access(self, request, message):
        """ Show an error message instead of the form """

        return self.response_class(
            request=request,
            template="wins/confirmation-denied.html",
            context={"message": message},
            using=self.template_engine
        )

    def _get_valid_win(self, pk, request):
        """ Raise SecurityException if Win not valid, else return Win dict """

        win_url = "{}{}/".format(settings.LIMITED_WINS_AP, pk)
        win_resp = rabbit.get(win_url, request=request)
        # likely because already submitted
        if not win_resp.status_code == 200:
            raise self.SecurityException(
                "Sorry, this record is not available or does not exist."
            )

        win_dict = win_resp.json()

        # is it within security window?
        created = date_parser(win_dict["created"])
        window_extent = created + relativedelta(days=self.ACCEPTANCE_WINDOW)
        now = timezone.now()
        if now > window_extent:
            raise self.SecurityException(
                "Sorry, this record is no longer available for review."
            )

        # is the confirmation already completed?
        confirmation_url = "{}?win={}".format(
            settings.CONFIRMATIONS_AP,
            win_dict['id'],
        )
        confirmation_dict = rabbit.get(confirmation_url).json()
        if confirmation_dict["count"]:
            print('butbutbut', confirmation_dict)

            raise self.SecurityException(
                "Sorry, this confirmation was already completed."
            )

        return win_dict
