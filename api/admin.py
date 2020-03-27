from django.contrib import admin
from django.forms import Textarea
from .models import (
    UserProfile,
    Holiday,
    Comment,
    UserHolidayVotes,
    UserNotifications,
    UserCommentVotes,
)
from django.db import models


class HolidayAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active",
        "get_image_small",
        "description",
        "blurb",
        "votes",
        "push",
        "date",
        "num_comments",
        "creator",
    )
    search_fields = (
        "name",
        "description",
        "votes",
        "push",
        "blurb",
        "image",
        "date",
        "creator__username",
    )
    readonly_fields = ("get_image",)
    fields = (
        "name",
        "date",
        "active",
        "get_image",
        "image_format",
        "image",
        "description",
        "push",
        "blurb",
        "votes",
        "creator",
    )
    formfield_overrides = {
        models.CharField: {"widget": Textarea(attrs={"rows": 4, "cols": 99})},
    }


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "active",
        "device_id",
        "rewards",
        "profile_image",
        "premium",
        "premium_id",
        "premium_token",
        "premium_state",
        "logged_out",
    )
    search_fields = (
        "user",
        "device_id",
        "profile_image",
        "premium_id",
        "premium_token",
        "premium_state",
    )


class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "content",
        "holiday",
        "user",
        "timestamp",
        "votes",
        "parent",
    )
    search_fields = ("content", "holiday", "user")


class HolidayVotesAdmin(admin.ModelAdmin):
    list_display = ("user", "holiday", "choice")
    search_fields = ("user", "holiday")


class NotificationsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_id",
        "notification_type",
        "read",
        "content",
        "timestamp",
        "title",
    )
    search_fields = ("user", "notification_type", "content", "title")


class CommentVotesAdmin(admin.ModelAdmin):
    list_display = ("user", "comment", "choice")
    search_fields = ("user", "comment")


admin.site.register(Holiday, HolidayAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(UserHolidayVotes, HolidayVotesAdmin)
admin.site.register(UserNotifications, NotificationsAdmin)
admin.site.register(UserCommentVotes, CommentVotesAdmin)
