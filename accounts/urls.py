from __future__ import unicode_literals
from django.urls import re_path
from accounts import views as account_views
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    re_path(_(r"^login/$"), account_views.UserLoginView.as_view(), name="login"),
    re_path(_(r"^register/$"), account_views.UserRegisterView.as_view(), name="register"),
]
