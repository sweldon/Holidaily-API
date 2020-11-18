import stripe
from django.conf import settings
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from api.constants import S3_BUCKET_IMAGES
from .models import Product


def home(request):
    featured_products = Product.objects.filter(featured=True, active=True)
    first_product = featured_products.first()
    secondary_products = featured_products[1:6]
    main_products = Product.objects.filter(active=True)[:6]
    return render(
        request,
        "shop/home.html",
        {
            "products": main_products,
            "s3_link": S3_BUCKET_IMAGES,
            "secondary_products": secondary_products,
            "first_product": first_product,
        },
    )


def product(request):
    product_id = request.GET.get("product")
    product = Product.objects.filter(id=product_id).first()
    reviews = product.reviews.all().order_by("-timestamp")
    return render(request, "shop/item.html", {"product": product, "reviews": reviews})


class SuccessView(TemplateView):
    template_name = "shop/success.html"


class CancelledView(TemplateView):
    template_name = "shop/cancelled.html"


@csrf_exempt
def stripe_config(request):
    if request.method == "GET":
        stripe_config = {"publicKey": settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)


# 4242 4242 4242 4242
@csrf_exempt
def checkout(request):
    if request.method == "GET":
        # TODO update this
        domain_url = settings.SITE_DOMAIN
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            # Create new Checkout Session for the order
            # Other optional params include:
            # [billing_address_collection] - to display billing address details on the page
            # [customer] - if you have an existing Stripe Customer ID
            # [payment_intent_data] - capture the payment later
            # [customer_email] - prefill the email input in the form
            # For full details see https://stripe.com/docs/api/checkout/sessions/create

            # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param
            checkout_session = stripe.checkout.Session.create(
                success_url=domain_url
                + "/shop/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/shop/cancelled/",
                payment_method_types=["card"],
                mode="payment",
                # todo add size
                line_items=[
                    {
                        "name": "T-shirt",
                        "quantity": 1,
                        "currency": "usd",
                        "amount": "2000",
                    }
                ],
            )
            return JsonResponse({"sessionId": checkout_session["id"]})
        except Exception as e:
            return JsonResponse({"error": str(e)})


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        print("Payment was successful.")
        # TODO: run some custom code here

    return HttpResponse(status=200)
