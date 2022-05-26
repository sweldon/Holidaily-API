from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("config/", views.stripe_config),
    path("checkout/", views.checkout),
    path("success/", views.SuccessView.as_view()),
    path("cancelled/", views.CancelledView.as_view()),
    path("item/", views.product),
    path("webhook/", views.stripe_webhook),
]
