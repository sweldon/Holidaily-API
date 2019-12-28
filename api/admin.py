from django.contrib import admin
from .models import (
    UserProfile,
    Holiday,
    Comment,
    UserHolidayVotes,
    UserNotifications,
    UserCommentVotes,
)


class HolidayAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "votes",
        "blurb",
        "image",
        "date",
        "num_comments",
        "time_since",
        "creator",
    )
    search_fields = (
        "name",
        "description",
        "votes",
        "blurb",
        "image",
        "date",
        "creator",
    )


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
        "time_since",
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
