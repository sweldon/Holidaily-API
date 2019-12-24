from django.contrib import admin
from .models import UserProfile, Holiday, Comment

admin.site.register(UserProfile)
admin.site.register(Holiday)
admin.site.register(Comment)
