from __future__ import unicode_literals
from django.conf.urls import url
from accounts import views as account_views
from django.utils.translation import ugettext_lazy as _

urlpatterns = [
    url(_(r"^login/$"), account_views.UserLoginView.as_view(), name="login"),
    url(_(r"^register/$"), account_views.UserRegisterView.as_view(), name="register"),
    url(
        r"^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        account_views.UserRegisterView.as_view(),
        name="activate",
    ),
]
