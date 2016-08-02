import os

from django.conf.urls import url
from django.views.generic import TemplateView

from ui.views import CSVView
from users.views import LoginView, LogoutView
from wins.views import (
    ConfirmationView, EditWinView, MyWinsView, NewWinView, WinCompleteView,
    WinView
)

urlpatterns = [

    url(
        r"^$",
        MyWinsView.as_view(),
        name="index",
    ),

    url(
        r"^wins/new/$",
        NewWinView.as_view(),
        name="new-win",
    ),

    # success pages after creating/editing/completing a win
    url(
        r"^wins/new-success/$",
        TemplateView.as_view(template_name="wins/win-new-success.html"),
        name="new-win-success"
    ),
    url(
        r"^wins/edit-success/$",
        TemplateView.as_view(template_name="wins/win-edit-success.html"),
        name="edit-win-success"
    ),
    url(
        r"^wins/complete-success/$",
        TemplateView.as_view(template_name="wins/win-complete-success.html"),
        name="complete-win-success"
    ),

    # view/edit/complete a win
    url(
        r"^wins/(?P<pk>[a-z0-9\-]{36})/$",
        WinView.as_view(),
        name="win-details"
    ),
    url(
        r"^wins/(?P<pk>[a-z0-9\-]{36})/edit/$",
        EditWinView.as_view(),
        name="win-edit"
    ),
    url(
        r"^wins/(?P<pk>[a-z0-9\-]{36})/complete/$",
        WinCompleteView.as_view(),
        name="win-complete"
    ),

    # review a win
    url(
        r"^wins/review/(?P<pk>[a-z0-9\-]{36})/$",
        ConfirmationView.as_view(),
        name="responses"
    ),
    url(
        r"^wins/review/thanks/$",
        TemplateView.as_view(template_name="wins/confirmation-thanks.html"),
        name="confirmation-thanks"
    ),
    url(
        r"^wins/review/sample/$",
        ConfirmationView.as_view(),
        name="response_sample"
    ),

    url(
        r"^accounts/login/$",
        LoginView.as_view(),
        name="login",
    ),
    url(
        r"^accounts/logout/$",
        LogoutView.as_view(),
        name="logout",
    ),

]

csv_secret = os.getenv("CSV_SECRET")
if csv_secret:
    csv_url = url(r"^{}/".format(csv_secret), CSVView.as_view(), name="csv")
    urlpatterns = [csv_url] + urlpatterns
