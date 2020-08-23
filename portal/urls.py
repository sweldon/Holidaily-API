from __future__ import unicode_literals
from django.urls import path
from portal.views import (
    activate,
    recover,
    password_reset_complete,
    password_reset_page,
    unsubscribe,
)

urlpatterns = [
    path(r"activate/<slug:uidb64>/<slug:token>/", activate, name="activate",),
    path(r"recover/", recover, name="recover"),
    path(
        r"reset/<slug:uidb64>/<slug:token>/",
        password_reset_page,
        name="password_reset_page",
    ),
    path(
        r"accounts/password/done/",
        password_reset_complete,
        name="password_reset_complete",
    ),
    path(r"unsubscribe/", unsubscribe, name="unsubscribe",),
]
