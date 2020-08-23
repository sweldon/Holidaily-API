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
    path(
        r"activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        activate,
        name="activate",
    ),
    path(r"recover/", recover, name="recover"),
    path(
        r"reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
        password_reset_page,
        name="password_reset_page",
    ),
    path(
        r"accounts/password/done/$",
        password_reset_complete,
        name="password_reset_complete",
    ),
    path(r"unsubscribe/$", unsubscribe, name="unsubscribe",),
]
