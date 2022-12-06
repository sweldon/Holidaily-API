from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six
from django.core.mail import EmailMessage
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template import loader
from django.utils.encoding import force_str
from django.shortcuts import resolve_url
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

from api.models import UserProfile


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_active)
        )


def index(request):
    return render(request, "portal/applink.html")


def unsubscribe(request):
    username = request.GET.get("user")
    user = User.objects.filter(username=username).first()
    profile = UserProfile.objects.filter(user=user).first()
    if not user:
        status, message = 404, "User does not exist"
    elif not profile:
        status, message = 404, "Profile does not exist"
    else:
        profile.emails_enabled = False
        profile.save()
        status, message = 200, "You have been successfully unsubscribed!"

    return render(
        request, "portal/unsubscribe.html", {"status": status, "message": message}
    )


def activate(request, uidb64, token):
    account_activation_token = TokenGenerator()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid)[0]
    except IndexError:
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(
            request, "portal/activation_result.html", {"status": 200, "token": token}
        )
    else:
        return render(request, "portal/activation_result.html", {"status": 500})


def validate_email_address(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def recover(request):
    if request.POST:
        result = 200
        email = request.POST["email"]
        if validate_email_address(email):
            try:
                associated_user = User.objects.get(email__iexact=email)
                c = {
                    "email": associated_user.email,
                    "domain": request.META["HTTP_HOST"],
                    "site_name": "Holidaily",
                    "uid": urlsafe_base64_encode(force_bytes(associated_user.pk)),
                    "user": associated_user,
                    "token": default_token_generator.make_token(associated_user),
                    "protocol": "http",
                }
                subject = "Holidaily Password Reset"
                email_template_name = "portal/recover_email.html"
                email_message = loader.render_to_string(email_template_name, c)
                activation_email = EmailMessage(subject, email_message, to=[email])
                activation_email.send(fail_silently=False)
                result = 202
            except ObjectDoesNotExist:
                result = 404
        else:
            result = 500
        return render(request, "portal/recover.html", {"result": result})
    else:
        return render(request, "portal/recover.html", status=200)


def password_reset_page(
    request,
    uidb64=None,
    token=None,
    template_name="portal/password_reset_page.html",
    token_generator=default_token_generator,
    set_password_form=SetPasswordForm,
    post_reset_redirect=None,
    extra_context=None,
):
    user_model = get_user_model()
    assert uidb64 is not None and token is not None  # checked by URLconf
    if post_reset_redirect is None:
        post_reset_redirect = reverse("password_reset_complete")
    else:
        post_reset_redirect = resolve_url(post_reset_redirect)
    try:
        # urlsafe_base64_decode() decodes to bytestring
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = user_model._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
        user = None

    valid_form = True
    if user and token_generator.check_token(user, token):
        valid_link = True
        title = "Enter new password"
        if request.method == "POST":
            form = set_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(post_reset_redirect)
            else:
                valid_form = False
        else:
            form = set_password_form(user)
    else:
        valid_link = False
        form = None
        title = "Password reset unsuccessful"

    context = {
        "form": form,
        "valid_form": valid_form,
        "title": title,
        "valid_link": valid_link,
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)


def password_reset_complete(request):
    return render(request, "portal/password_reset_complete.html", status=200)
