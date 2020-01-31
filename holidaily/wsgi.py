"""
WSGI config for holidaily project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

sys.path.append('/home/ubuntu/Holidaily-API')
sys.path.append('/home/ubuntu/Holidaily-API/holidaily')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "holidaily.settings")

application = get_wsgi_application()

