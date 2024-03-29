import hashlib
import requests
from PIL import Image
from django.contrib import admin
from django.forms import Textarea
from io import BytesIO

from api.constants import S3_BUCKET_NAME, S3_BUCKET_IMAGES
from holidaily.helpers.notification_helpers import award_and_notify_user_for_holiday
from django.conf import settings
from .models import (
    UserProfile,
    Holiday,
    Comment,
    UserHolidayVotes,
    UserNotifications,
    UserCommentVotes,
    Post,
)
from django.db import models
import logging
from django.contrib import messages

logger = logging.getLogger("holidaily")


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
        "created",
        "notes",
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
        "notes",
    )
    ordering = ("-created",)
    readonly_fields = ("get_image", "created", "votes", "creator_awarded", "creator")
    raw_id_fields = ("photo_credit_user",)
    fields = (
        "name",
        "date",
        "active",
        "get_image",
        "image_format",
        "image",
        "uploaded_image",
        "photo_credit_user",
        "description",
        "push",
        "blurb",
        "votes",
        "creator",
        "created",
        "creator_awarded",
        "notes",
    )
    formfield_overrides = {
        models.CharField: {"widget": Textarea(attrs={"rows": 1, "cols": 40})},
        models.TextField: {"widget": Textarea(attrs={"rows": 3, "cols": 60})},
    }

    def get_form(self, request, obj=None, **kwargs):
        form = super(HolidayAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["image"].widget.attrs["style"] = "height: 1.25em;"
        form.base_fields["push"].widget.attrs["style"] = "height: 1.25em;"
        form.base_fields["blurb"].widget.attrs["style"] = "height: 2.5em;"
        return form

    def save_model(self, request, obj, form, change):
        if "uploaded_image" in form.changed_data and obj.uploaded_image:
            obj.image_name = obj.uploaded_image
            obj.image = f"{S3_BUCKET_IMAGES}/{obj.uploaded_image}"

        if (
            "active" in form.changed_data
            and obj.active
            and obj.creator
            and not obj.creator_awarded
        ):

            push_sent = award_and_notify_user_for_holiday(obj)
            if push_sent:
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"{obj.creator.username} was notified of holiday approval!",
                )
            else:
                messages.add_message(
                    request,
                    messages.WARNING,
                    f"Holiday approved, but {obj.creator.username} could not be reached for notification",
                )

        if "image" in form.changed_data and "uploaded_image" not in form.changed_data:
            try:
                image_data = requests.get(obj.image).content
                image_object = Image.open(BytesIO(image_data))
                byte_arr = BytesIO()
                image_object.save(byte_arr, format=obj.image_format)
                image_data = byte_arr.getvalue()
                image_hash = hashlib.md5(image_data).hexdigest()
                image_suffix = f"-{image_hash}.{obj.image_format}"
                if not obj.image_name or not obj.image_name.endswith(image_suffix):
                    new_image_name = f"{obj.name.strip().replace(' ', '-')}-{image_hash}.{obj.image_format}"
                    settings.S3_CLIENT.Bucket(S3_BUCKET_NAME).put_object(
                        Key=new_image_name, Body=image_data
                    )
                    obj.image_name = new_image_name
            except Exception as e:  # noqa
                messages.add_message(
                    request,
                    messages.ERROR,
                    "The holiday was saved, but we couldn't save the image. Please try another one.",
                )
                logger.error(f"Could not save image: {e}")

        super(HolidayAdmin, self).save_model(request, obj, form, change)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "active",
        "platform",
        "version",
        "last_launched",
        "confetti",
        "premium",
        "logged_out",
        "avatar_preview",
        "referrer",
    )
    search_fields = (
        "user__username",
        "device_id",
        "platform",
        "version",
        "last_launched",
    )
    fields = (
        "user",
        "active",
        "platform",
        "version",
        "last_launched",
        "device_id",
        "confetti",
        "premium",
        "logged_out",
        "avatar_full",
        "avatar_approved",
        "referrer",
        "emails_enabled",
        "device_active",
        "ad_last_watched",
        "requested_confetti_alert",
    )
    readonly_fields = ("avatar_full", "referrer")
    raw_id_fields = ("user",)


class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "content",
        "holiday",
        "user",
        "timestamp",
        "votes",
        "reports",
        "parent",
    )
    fields = (
        "holiday",
        "user",
        "parent",
        "deleted",
        "parent_post",
        "likes",
        "votes",
        "reports",
        "edited",
        "timestamp",
        "content",
    )
    search_fields = ("content", "holiday__name", "user__username")
    raw_id_fields = ("user", "holiday", "parent", "parent_post")
    readonly_fields = ("votes", "reports", "edited", "timestamp", "content")


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


class PostAdmin(admin.ModelAdmin):
    list_display = (
        "get_image_small",
        "user",
        "content",
        "holiday",
        "timestamp",
        "likes",
        "deleted",
        "reports",
        "edited",
    )
    fields = (
        "get_image",
        "user",
        "content",
        "holiday",
        "timestamp",
        "likes",
        "deleted",
        "reports",
        "edited",
    )
    search_fields = ("content",)
    raw_id_fields = ("holiday",)
    readonly_fields = ("get_image",)


admin.site.register(Holiday, HolidayAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(UserHolidayVotes, HolidayVotesAdmin)
admin.site.register(UserNotifications, NotificationsAdmin)
admin.site.register(UserCommentVotes, CommentVotesAdmin)
admin.site.register(Post, PostAdmin)
