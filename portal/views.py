from django.shortcuts import render
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_text
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_active)
        )


def activate(request, uidb64, token):
    account_activation_token = TokenGenerator()
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid)[0]
    except IndexError:
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, "portal/activation_result.html", {"status": 200})
    else:
        return render(request, "portal/activation_result.html", {"status": 500})
