from django.conf.urls import url

from ui.views import IndexView
from users.views import LoginView, LogoutView
from wins.views import NewWinView, ThanksView, ConfirmationView

urlpatterns = [

    url(r"^wins/new/", NewWinView.as_view(), name="new"),
    url(r"^wins/thanks/", ThanksView.as_view(), name="thanks"),
    url(
        r"^wins/review/(?P<pk>[a-z0-9\-]+)/",
        ConfirmationView.as_view(),
        name="responses"
    ),

    url(r'^accounts/login/', LoginView.as_view(), name="login"),
    url(r"^accounts/logout/", LogoutView.as_view(), name="logout"),

    url(r"^$", IndexView.as_view(), name="index"),

]
