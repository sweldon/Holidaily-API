from __future__ import unicode_literals
from django.conf.urls import url
from portal.views import activate

urlpatterns = [
    url(
        r"^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        activate,
        name="activate",
    ),
]
