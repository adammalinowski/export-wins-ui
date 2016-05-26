import re

from datetime import datetime
from dateutil.relativedelta import relativedelta

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse

from alice.helpers import rabbit, get_form_field
from alice.metaclasses import ReflectiveFormMetaclass
from ui.forms import BootstrappedForm


class WinReflectiveFormMetaclass(ReflectiveFormMetaclass):

    reflection_url = settings.WINS_AP

    def __new__(mcs, name, bases, attrs):
        new_class = ReflectiveFormMetaclass.__new__(mcs, name, bases, attrs)

        make_typed_choice = (
            "is_prosperity_fund_related",
            "is_e_exported",
            "has_hvo_specialist_involvement",
        )
        for name in make_typed_choice:
            form_field = forms.TypedChoiceField(
                coerce=lambda x: x == "True",
                choices=((True, 'Yes'), (False, 'No')),
                widget=forms.RadioSelect,
                label=new_class._schema[name]["label"]
            )
            new_class.base_fields[name] = form_field
            new_class.declared_fields[name] = form_field

        return new_class


class ConfirmationFormMetaclass(ReflectiveFormMetaclass):

    reflection_url = settings.CONFIRMATIONS_AP

    def __new__(mcs, name, bases, attrs):

        new_class = ReflectiveFormMetaclass.__new__(mcs, name, bases, attrs)

        make_typed_choice = (
            "involved_state_enterprise",
            "interventions_were_prerequisite",
            "support_improved_speed",
            "company_was_at_risk_of_not_exporting",
            "has_explicit_export_plans",
            "has_enabled_expansion_into_new_market",
            "has_increased_exports_as_percent_of_turnover",
            "has_enabled_expansion_into_existing_market"
        )
        for name in make_typed_choice:
            form_field = forms.TypedChoiceField(
                coerce=lambda x: x == "True",
                choices=((True, 'Yes'), (False, 'No')),
                widget=forms.RadioSelect,
                label=new_class._schema[name]["label"]
            )
            new_class.base_fields[name] = form_field
            new_class.declared_fields[name] = form_field

        return new_class


class WinForm(BootstrappedForm, metaclass=WinReflectiveFormMetaclass):

    # We're only caring about yyyy-mm formatted dates
    date = forms.fields.CharField(max_length=7, label="Date business won")

    class Meta(object):
        exclude = ("id", "user")

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop("request")

        BootstrappedForm.__init__(self, *args, **kwargs)

        self.fields["date"].widget.attrs.update({"placeholder": "YYYY-MM"})

        self.fields["is_personally_confirmed"].required = True
        self.fields["is_personally_confirmed"].label_suffix = ""

        self.fields["is_line_manager_confirmed"].required = True
        self.fields["is_line_manager_confirmed"].label_suffix = ""

        self.fields["total_expected_export_value"].widget.attrs.update(
            {"placeholder": "£GBP"})
        self.fields["total_expected_non_export_value"].widget.attrs.update(
            {"placeholder": "£GBP"})

        self._add_breakdown_fields()
        self._add_advisor_fields()

        self._advisors = []

    def clean_date(self):
        date = self.cleaned_data.get("date")
        m = re.match(r"^(\d\d\d\d)-(\d\d)$", date)
        if not m:
            raise forms.ValidationError('Invalid format. Please use "YYYY-MM"')
        return "{}-01".format(date)

    def clean_is_personally_confirmed(self):
        r = self.cleaned_data.get("is_personally_confirmed")
        if not r:
            raise forms.ValidationError("This is a required field")
        return r

    def clean_is_line_manager_confirmed(self):
        r = self.cleaned_data.get("is_line_manager_confirmed")
        if not r:
            raise forms.ValidationError("This is a required field")
        return r

    def save(self):

        # This is overwritten by the data server to be request.user, but since
        # it's entirely possible that the local user id and the data server's
        # user id are different, we can't use request.user.pk here.
        # Ideally this should be rewritten to have a local user.data_server_id
        # or something, but that's not here yet because deadlines.
        self.cleaned_data["user"] = 1

        win = self.push(settings.WINS_AP, self.cleaned_data)

        for data in self._get_breakdown_data(win["id"]):
            self.push(settings.BREAKDOWNS_AP, data)

        for data in self._get_advisor_data(win["id"]):
            self.push(settings.ADVISORS_AP, data)

        self.send_notifications(win["id"])

    def send_notifications(self, win_id):
        """
        Tell the data server to send mail. Failures will not blow up at the
        client, but will blow up the server, so we'll be notified if something
        goes wrong.
        """

        rabbit.post(settings.NOTIFICATIONS_AP, data={
            "win": win_id,
            "type": "o",
            "user": self.request.user.pk,
        })

        # Disabled until we get the go-ahead
        # rabbit.post(settings.NOTIFICATIONS_AP, data={
        #     "win": win_id,
        #     "type": "c",
        #     "recipient": self.cleaned_data["customer_email_address"],
        #     "url": self.request.build_absolute_uri(
        #         reverse("responses", kwargs={"pk": win_id})
        #     )
        # })

    def push(self, ap, data):

        # The POST request is http-url-encoded rather than json-encoded for now
        # since I don't know how to set it that way and don't have the time to
        # find out.
        response = rabbit.post(ap, data=data, request=self.request)

        if not response.status_code == 201:
            raise forms.ValidationError(
                "Something has gone terribly wrong.  Please contact support.")

        return response.json()

    def _add_breakdown_fields(self):

        breakdown_values = ("breakdown_exports_{}", "breakdown_non_exports_{}")

        now = datetime.utcnow()

        for i in range(0, 5):

            d = now + relativedelta(years=i)

            for field in breakdown_values:
                self.fields[field.format(i)] = forms.fields.IntegerField(
                    label="{}/{}".format(d.year, str(d.year + 1)[-2:]),
                    widget=forms.fields.NumberInput(
                        attrs={
                            "class": "form-control",
                            "placeholder": "£GBP"
                        }
                    ),
                )

    def _get_breakdown_data(self, win_id):

        r = []
        now = datetime.utcnow()

        for i in range(0, 5):
            d = now + relativedelta(years=i)
            for t in ("exports", "non_exports"):
                value = self.cleaned_data.get("breakdown_{}_{}".format(t, i))
                if value:
                    r.append({
                        "type": "1" if t == "exports" else "2",
                        "year": d.year,
                        "value": value,
                        "win": win_id
                    })
        return r

    def _add_advisor_fields(self):

        schema = rabbit.get(settings.ADVISORS_AP + "schema/").json()

        for i in range(0, 5):
            for name, spec in schema.items():
                field_name = "advisor_{}_{}".format(i, name)
                self.fields[field_name] = get_form_field(spec)
                self.fields[field_name].required = False
                self.fields[field_name].widget.attrs.update({
                    "class": "form-control"
                })

    def _get_advisor_data(self, win_id):
        for advisor in self._advisors:
            advisor["win"] = win_id
        return self._advisors


class ConfirmationForm(BootstrappedForm, metaclass=ConfirmationFormMetaclass):

    def __init__(self, *args, **kwargs):

        BootstrappedForm.__init__(self, *args, **kwargs)

        self.fields["win_id"].widget = forms.widgets.HiddenInput()

