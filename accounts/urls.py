from __future__ import unicode_literals
from django.conf.urls import url
from accounts import views as account_views
from django.utils.translation import ugettext_lazy as _

urlpatterns = [
    url(_(r"^login/$"), account_views.UserLoginView.as_view(), name="login"),
    url(_(r"^register/$"), account_views.UserRegisterView.as_view(), name="register"),
]
