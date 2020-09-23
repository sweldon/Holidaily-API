import humanize
import pytz
from django.db.models import Q
from django.forms import model_to_dict
from elasticsearch_dsl import Search
from push_notifications.models import APNSDevice, GCMDevice
from rest_framework.decorators import api_view

from holidaily.helpers.notification_helpers import (
    send_slack,
    notify_mentioned_users,
    notify_liked_user,
)
from holidaily.permissions import UpdateObjectPermission
from holidaily.utils import sync_devices, normalize_time
from .models import (
    Holiday,
    UserHolidayVotes,
    Comment,
    UserNotifications,
    UserCommentVotes,
    UserProfile,
    Post,
)
from .serializers import (
    UserSerializer,
    HolidaySerializer,
    CommentSerializer,
    UserNotificationsSerializer,
    UserProfileSerializer,
    PostSerializer,
)
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework.status import (
    HTTP_404_NOT_FOUND,
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
)
from api.constants import (
    UPVOTE_CHOICES,
    DOWNVOTE_CHOICES,
    SINGLE_UP,
    SINGLE_DOWN,
    UP_FROM_DOWN,
    DOWN_FROM_UP,
    DOWNVOTE_ONLY,
    UPVOTE_ONLY,
    NEWS_NOTIFICATION,
    COMMENT_NOTIFICATION,
    MAX_COMMENT_DEPTH,
    TRUTHY_STRS,
    REPLY_DEPTH,
    ANDROID,
    IOS,
    S3_BUCKET_NAME,
    CLOUDFRONT_DOMAIN,
    S3_BUCKET_IMAGES,
    CONFETTI_COOLDOWN_MINUTES,
    POST_NOTIFICATION,
    LIKE_NOTIFICATION,
)
from api.exceptions import RequestError, DeniedError
import re
import html
from django.conf import settings
from api.tasks import confetti_notification
from django.core.cache import cache
import logging

logger = logging.getLogger("holidaily")


class UserList(APIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request):
        search = request.GET.get("search", None)
        if search:
            # User searching for another user to mention
            user_list = (
                UserProfile.objects.filter(user__username=search)
                or UserProfile.objects.filter(user__username__istartswith=search)[:5]
            )
            serializer = UserProfileSerializer(user_list, many=True)
            results = {"results": serializer.data}
            return Response(results)
        else:
            return Response({"message": "Not a valid request"}, status=404,)

    def post(self, request):
        username = request.POST.get("username", None)
        device_id = request.POST.get("device_id", None)
        platform = request.POST.get("platform", None)
        version = request.POST.get("version", None)
        requesting_user = request.POST.get("requesting_user", None)
        device_update = request.POST.get("device_update", None)
        if username:
            user = User.objects.get(username=username)
            # Keep device id up to date
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                update_fields = ["last_launched", "logged_out"]
                if device_id and device_id != profile.device_id:
                    profile.device_id = device_id
                    update_fields.append("device_id")
                if platform and platform != profile.platform:
                    profile.platform = platform
                    update_fields.append("platform")
                if version and version != profile.version:
                    profile.version = version
                    update_fields.append("version")
                profile.last_launched = timezone.now()
                profile.logged_out = False
                profile.save(update_fields=update_fields)
                # Logged out user
                if device_id and platform:
                    # Token Refresh
                    sync_devices(device_id, platform, user)
                else:
                    # Logged-in user duplicate anon device cleanup, NOT via syncUser()
                    device_class = APNSDevice if platform == IOS else GCMDevice
                    existing_unassigned = device_class.objects.filter(
                        registration_id=profile.device_id, user__isnull=True
                    ).last()
                    if existing_unassigned:
                        existing_unassigned.delete()

            # isLoggedIn syncUser()
            if device_update:
                if profile and device_update != profile.device_id:
                    profile.device_id = device_update
                    profile.save()
                sync_devices(device_update, platform, user)

        elif device_id and platform:
            sync_devices(device_id, platform)
            results = {"status": HTTP_200_OK, "message": "OK"}
            return Response(results)
        elif requesting_user:
            # Confetti leaderboard
            user_list = UserProfile.objects.filter(
                confetti__gt=0, user__is_staff=False
            ).order_by("confetti")[:50]
            serializer = UserProfileSerializer(
                user_list, many=True, context={"requesting_user": requesting_user}
            )
            results = {"results": serializer.data}
            return Response(results)
        else:
            raise RequestError("Please provide a username for POST requests")
        serializer = UserSerializer(user)
        results = {"results": serializer.data}
        return Response(results)


class UserProfileDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    def post(self, request):
        username = request.POST.get("username", None)
        requesting_user = request.POST.get("requesting_user", None)
        token = request.POST.get("token", None)
        reward = request.POST.get("reward", None)
        logout = request.POST.get("logout", None)
        check_update = request.POST.get("check_update", None)
        avatar = request.FILES.get("file", None)
        notify_cooldown = request.POST.get("notify_cooldown", False)
        profile = UserProfile.objects.filter(user__username=username).first()

        if check_update:
            version = request.POST.get("version", None)
            platform = request.POST.get("platform", None)
            requires_update = False
            force_update = False

            if settings.UPDATE_ALERT:
                if platform == ANDROID and version != settings.ANDROID_VERSION:
                    requires_update = True
                elif platform == IOS and version != settings.IOS_VERSION:
                    requires_update = True

                if settings.FORCE_UPDATE and requires_update:
                    force_update = True

            results = {
                "needs_update": requires_update,
                "force_update": force_update,
                "status": HTTP_200_OK,
            }
            return Response(results)

        if not profile:
            return Response({"status": 404, "message": "User not found"})

        if logout is not None:
            profile.logged_out = bool(logout)
            profile.save()
            results = {
                "message": f"{username} logout status changed to: {logout}",
                "status": HTTP_200_OK,
            }
            return Response(results)
        elif token:
            # User bought premium
            id = request.POST.get("id", None)
            state = request.POST.get("state", None)
            profile.premium_id = id
            profile.premium_token = token
            profile.premium_state = state
            profile.premium = True
            profile.save()
            send_slack(
                f":moneybag: PREMIUM HYPE :moneybag: _{username}_ bought premium!",
                channel="hype",
            )
            results = {"message": "User was made premium!", "status": HTTP_200_OK}
            return Response(results)

        elif notify_cooldown:
            notify = True if notify_cooldown in TRUTHY_STRS else False
            if notify != profile.requested_confetti_alert:
                profile.requested_confetti_alert = notify
                profile.save()

            if notify:
                user_id = profile.user.id
                cache_key = f"confetti_notify_{user_id}"
                if not cache.get(cache_key):
                    logger.info(
                        f"Queueing up confetti notification from toggle (key: {cache_key})"
                    )
                    countdown = (
                        (
                            profile.ad_last_watched
                            + timedelta(minutes=CONFETTI_COOLDOWN_MINUTES)
                        )
                        - timezone.now()
                    ).total_seconds()
                    cache.set(cache_key, 1, countdown)
                    confetti_notification.apply_async(
                        args=[user_id], countdown=countdown
                    )

            results = {
                "message": f"Notify preference updated to {notify} for {username}",
                "status": HTTP_200_OK,
            }
            return Response(results)

        elif reward:
            # User earned confetti
            reward_amount = request.POST.get("reward", None)
            profile.confetti += int(reward_amount)
            profile.ad_last_watched = timezone.now()
            profile.save()

            if profile.requested_confetti_alert:
                user_id = profile.user.id
                cache_key = f"confetti_notify_{user_id}"
                if not cache.get(cache_key):
                    logger.info(
                        f"Queueing up confetti notification from default (key: {cache_key})"
                    )
                    countdown = (
                        (
                            profile.ad_last_watched
                            + timedelta(minutes=CONFETTI_COOLDOWN_MINUTES)
                        )
                        - timezone.now()
                    ).total_seconds()
                    cache.set(cache_key, 1, countdown)
                    confetti_notification.apply_async(
                        args=[user_id], countdown=countdown
                    )

            results = {
                "message": f"{reward_amount} confetti awarded to {username}",
                "status": HTTP_200_OK,
            }
            return Response(results)

        elif avatar:
            file_name = f"{username}_{avatar}"
            settings.S3_CLIENT.Bucket(S3_BUCKET_NAME).put_object(
                Key=file_name, Body=avatar
            )
            profile.profile_image = file_name
            profile.avatar_approved = False
            profile.save()
            results = {
                "avatar": f"{CLOUDFRONT_DOMAIN}/{file_name}",
                "status": HTTP_200_OK,
            }
            send_slack(
                f"[*PROFILE PICTURE*] _{username}_ has uploaded a new profile picture."
                f" Needs approval: https://holidailyapp.com/admin/api/userprofile/{profile.id}/"
            )
            return Response(results)
        elif requesting_user:
            serializer = UserProfileSerializer(
                profile, context={"requesting_user": requesting_user}
            )
            results = {"results": serializer.data, "status": 200}
            return Response(results)
        else:
            serializer = UserProfileSerializer(profile)
            results = {"results": serializer.data, "status": 200}
            return Response(results)


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class HolidayList(generics.GenericAPIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer

    def get(self, request):
        top_holidays = request.GET.get("top", None)
        by_name = request.GET.get("name", None)
        if top_holidays:
            # Top Holidays
            holidays = Holiday.objects.filter(active=True).order_by("-votes")[:10]
        elif by_name:
            holidays = Holiday.objects.filter(name=by_name, active=True)
        else:
            # Not used in app, just a default
            today = timezone.now()
            holidays = Holiday.objects.filter(
                date__range=[today - timedelta(days=7), today], active=True
            ).order_by("-date")
        serializer = HolidaySerializer(holidays, many=True)
        results = {"results": serializer.data}
        return Response(results)

    def post(self, request):

        username = request.POST.get("username", None)
        search = request.POST.get("search", None)
        holidays_by = request.POST.get("holidays_by", None)
        past = request.POST.get("past", None)
        # 2.0+ will always send page
        page = request.POST.get("page", None)

        if search:
            is_date = False
            try:
                search = re.match(
                    r"\d{1,2}\/\d{1,2}\/\d{4}\s\d{1,2}:\d{1,2}:\d{1,2}\s(AM|PM)", search
                ).group(0)
                is_date = True
            except AttributeError:
                search = (
                    search.lower().replace("national", "").replace("day", "").strip()
                )

            if is_date:
                holidays = Holiday.objects.filter(
                    Q(date=datetime.strptime(search.split(" ")[0], "%m/%d/%Y")),
                    Q(active=True) | (Q(active=False) & Q(creator__isnull=True)),
                )
            else:
                holidays = Holiday.objects.filter(
                    Q(name__icontains=search),
                    Q(active=True) | (Q(active=False) & Q(creator__isnull=True)),
                )

        elif holidays_by:
            holidays = Holiday.objects.filter(
                creator__username=holidays_by, active=True
            ).order_by("-votes")
        elif past:
            today = timezone.now()
            chunk = int(page) * settings.HOLIDAY_PAGE_SIZE
            holidays = Holiday.objects.filter(date__lt=today).order_by("-date")[
                chunk : chunk + settings.HOLIDAY_PAGE_SIZE
            ]
            print(
                f"loading past holidays {chunk} to {chunk + settings.HOLIDAY_PAGE_SIZE}"
            )
        else:
            # Default endpoint for all users
            today = timezone.now()
            if page is not None:
                chunk = int(page) * settings.HOLIDAY_PAGE_SIZE
                holidays = Holiday.objects.filter(date__gte=today).order_by("date")[
                    chunk : chunk + settings.HOLIDAY_PAGE_SIZE
                ]
            else:
                # TODO legacy < 2.0, needs -date because of range & no pagination
                holidays = Holiday.objects.filter(
                    date__range=[today - timedelta(days=7), today], active=True
                ).order_by("-date")

        serializer = HolidaySerializer(
            holidays, many=True, context={"username": username}
        )
        results = {"results": serializer.data}
        return Response(results)


class UserHolidays(HolidayList):
    def post(self, request):
        username = request.POST.get("username", None)
        submission = request.POST.get("submission", None)

        pending_holidays = Holiday.objects.filter(
            creator__username=username, active=False
        ).exists()
        if submission:
            if pending_holidays:
                results = {
                    "status": HTTP_400_BAD_REQUEST,
                    "message": "Submission already pending",
                }
                return Response(results)
            else:
                image = request.FILES.get("file", None)
                image_name = None
                image_link = None
                if image:
                    image_name = f"{submission.strip().replace(' ', '-')}.jpeg"
                    settings.S3_CLIENT.Bucket(S3_BUCKET_NAME).put_object(
                        Key=image_name, Body=image
                    )
                    image_link = f"{S3_BUCKET_IMAGES}/{image_name}"
                description = request.POST.get("description", None)
                date = request.POST.get("date", None)
                date_formatted = datetime.strptime(date.split(" ")[0], "%m/%d/%Y")
                holiday = Holiday.objects.create(
                    name=submission,
                    description=description,
                    date=date_formatted,
                    creator=User.objects.get(username=username),
                    active=False,
                    image_name=image_name,
                    image=image_link,
                )
                send_slack(
                    f"[*USER HOLIDAY SUBMISSION*] *{username}* has submitted *{submission}*\n"
                    f"- Link: https://holidailyapp.com/admin/api/holiday/{holiday.id}/"
                )
                results = {
                    "message": "Holiday submitted for review",
                    "status": HTTP_200_OK,
                }
                return Response(results)
        else:
            results = {"results": pending_holidays}
            return Response(results)


class HolidayDetail(APIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get_object(self, pk):
        try:
            return Holiday.objects.get(pk=pk)
        except Holiday.DoesNotExist:
            raise HTTP_404_NOT_FOUND

    def get(self, request, pk):
        holiday = self.get_object(pk)
        serializer = HolidaySerializer(holiday)
        results = {"results": serializer.data}
        return Response(results)

    def post(self, request, pk):
        vote = request.POST.get("vote", None)
        username = request.POST.get("username", None)
        holiday = self.get_object(pk)

        if vote:
            vote = int(vote)
            if vote in UPVOTE_CHOICES:
                holiday.votes += 1
            elif vote in DOWNVOTE_CHOICES:
                holiday.votes -= 1
            else:
                raise RequestError("Invalid vote type")
            holiday.save()
            user_vote, created = UserHolidayVotes.objects.get_or_create(
                user__username=username,
                holiday=holiday,
                defaults={"choice": vote, "user": User.objects.get(username=username)},
            )
            if not created and user_vote.choice != vote:
                user_vote.choice = vote
                user_vote.save()
            results = {"status": HTTP_200_OK, "message": "OK"}
            return Response(results)
        else:
            holiday = self.get_object(pk)
            serializer = HolidaySerializer(holiday, context={"username": username})
            results = {"results": serializer.data}
            return Response(results)


class CommentDetail(generics.RetrieveUpdateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [UpdateObjectPermission]

    def patch(self, request, *args, **kwargs):

        data = request.data.copy()
        updated_comment = self.get_object()
        if not self.get_queryset().count():
            raise RequestError("No comments available for update")

        profile = UserProfile.objects.get(
            device_id=data["device_id"], user__username=data["username"]
        )
        data["user"] = profile.user.id

        if "report" in data:
            block = True if data["block"] in TRUTHY_STRS else False
            current_reports = updated_comment.reports
            data["reports"] = current_reports + 1
            profile.reported_comments.add(updated_comment)
            if block:
                profile.blocked_users.add(updated_comment.user)

            send_slack(
                f"[*REPORT RECEIVED*] *{data['username']}* has submitted a report for a post by "
                f"*{updated_comment.user}*,"
                f" on *{updated_comment.holiday.name}*. See post below.\n"
                f"```{updated_comment.content}```\n"
                f"- Link to post in Admin: https://holidailyapp.com/admin/api/comment/{updated_comment.id}/"
            )

        if "content" in data and data["content"] != updated_comment.content:
            data["edited"] = timezone.now()

        serializer = self.get_serializer(self.get_object(), data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        results = serializer.data
        # TODO this is for legacy apps before post update, need this response
        results.update({"status": 200, "message": "OK"})
        return Response(results)

    def post(self, request, pk):
        vote = request.POST.get("vote", None)
        username = request.POST.get("username", None)
        report = request.POST.get("report", None)
        block_request = request.POST.get("block", None)
        block = True if block_request in TRUTHY_STRS else False
        comment = self.get_object()

        if vote:
            vote = int(vote)
            profile = UserProfile.objects.filter(user=comment.user).first()
            if vote in SINGLE_UP:
                comment.votes += 1
                profile.confetti += 1
            elif vote in SINGLE_DOWN:
                comment.votes -= 1
                profile.confetti -= 1
            elif vote == UP_FROM_DOWN:
                comment.votes += 2
                profile.confetti += 2
            elif vote == DOWN_FROM_UP:
                comment.votes -= 2
                profile.confetti -= 2
            else:
                raise RequestError("Invalid vote type")
            comment.save()
            profile.save()
            user_vote, created = UserCommentVotes.objects.get_or_create(
                user__username=username,
                comment=comment,
                defaults={"choice": vote, "user": User.objects.get(username=username)},
            )
            if not created and user_vote.choice != vote:
                user_vote.choice = vote
                user_vote.save()
            results = {"status": HTTP_200_OK, "message": "OK"}
            return Response(results)
        elif report:
            comment.reports += 1
            comment.save()
            user_profile = UserProfile.objects.get(user__username=username)
            user_profile.reported_comments.add(comment)
            if block:
                user_profile.blocked_users.add(comment.user)
            send_slack(
                f"[*REPORT RECEIVED*] *{username}* has submitted a report for a comment by *{comment.user}*,"
                f" on *{comment.holiday.name}*. See comment below.\n"
                f"```{comment.content}```\n"
                f"- Link to comment in Admin: https://holidailyapp.com/admin/api/comment/{comment.id}/"
            )
            results = {"status": HTTP_200_OK, "message": "OK"}
            return Response(results)
        else:
            comment = self.get_object()
            serializer = CommentSerializer(comment, context={"username": username})
            results = {"results": serializer.data}
            return Response(results)


class CommentList(generics.GenericAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        holiday_id = request.GET.get("holiday", None)
        post_id = request.GET.get("post", None)
        if holiday_id:
            comments = Holiday.objects.get(id=holiday_id).comment_set.order_by("-votes")
        elif post_id:
            post = Post.objects.get(id=post_id)
            comments = Comment.objects.filter(parent_post=post)
        else:
            raise RequestError("Invalid query")
        serializer = CommentSerializer(comments, many=True)
        results = {"results": serializer.data}
        return Response(results)

    def get_replies(self, comment, username):
        """ Recursively get comment reply chain """
        reply_chain = []
        replies = comment.comment_set.all().order_by("-votes", "-id")

        for c in replies:
            reply_chain.append(c)
            if c.comment_set.all().count() > 0:
                child_replies = self.get_replies(c, username)
                reply_chain.extend(child_replies)

        return reply_chain

    def get_vote_status(self, username, obj):
        if username:
            if UserCommentVotes.objects.filter(
                user__username=username, comment=obj, choice__in=UPVOTE_ONLY
            ).exists():
                return "up"
            elif UserCommentVotes.objects.filter(
                user__username=username, comment=obj, choice__in=DOWNVOTE_ONLY
            ).exists():
                return "down"
            else:
                return None
        else:
            return None

    def post(self, request):
        username = request.POST.get("username", None)
        content = request.POST.get("content", None)
        holiday = request.POST.get("holiday", None)
        delete = request.POST.get("delete", None)
        activity = request.POST.get("activity", None)
        if delete:
            # Mobile, confirm mobile user requesting delete is the author
            device_id = request.POST.get("device_id", None)
            if device_id is not None:
                device_id = device_id.strip()
            else:
                results = {
                    "status": HTTP_400_BAD_REQUEST,
                    "message": "Have you switched accounts recently? We could not identify your device. Please re-log"
                    " and try again!",
                }
                return Response(results)
            comment = Comment.objects.filter(id=delete).first()
            # Mobile, confirm mobile user requesting delete is the author
            if not comment:
                results = {
                    "status": HTTP_404_NOT_FOUND,
                    "message": "Comment no longer exists",
                }
                return Response(results)

            try:
                device_user = UserProfile.objects.get(
                    user__username=username, device_id=device_id
                ).user.id
            except:  # noqa
                results = {
                    "status": HTTP_403_FORBIDDEN,
                    "message": "There was an issue identifying your device. Please re-log in and try to delete "
                    "this comment again.",
                }
                return Response(results)
            comment_user = comment.user.id
            if device_user == comment_user:
                comment.deleted = True
                comment.save()
                results = {
                    "status": HTTP_200_OK,
                    "message": "Comment flagged for deletion",
                }
                return Response(results)
            else:
                results = {
                    "status": HTTP_403_FORBIDDEN,
                    "message": "You aren't allowed to delete this",
                }
                return Response(results)
        elif content:
            parent_id = request.POST.get("parent", None)
            post_id = request.POST.get("post", None)
            holiday = Holiday.objects.get(id=holiday)
            parent = Comment.objects.get(id=parent_id) if parent_id else None
            post = Post.objects.get(id=post_id) if post_id else None
            user = User.objects.get(username=username)

            if UserProfile.objects.get(user=user).active:
                new_comment = Comment(
                    content=content,
                    holiday=holiday,
                    user=user,
                    timestamp=timezone.now(),
                    parent=parent,
                    parent_post=post,
                )
                new_comment.save()
                notify_mentioned_users(new_comment)
                results = CommentSerializer(new_comment).data
                # TODO legacy
                results.update({"status": HTTP_200_OK, "message": "OK"})
                return Response(results)
            else:
                raise DeniedError(
                    "Sorry! You've been banned and can no longer comment."
                )

        elif holiday:
            page = int(request.POST.get("page", 0))
            chunk = page * settings.COMMENT_PAGE_SIZE
            comment_list = []
            # All the parents with no children
            comments = (
                Holiday.objects.get(id=holiday)
                .comment_set.filter(parent__isnull=True)
                .order_by("-votes", "-id")
            )[chunk : chunk + settings.COMMENT_PAGE_SIZE]
            for c in comments:
                comment_group = [c]
                if c.comment_set.all().count() > 0:
                    replies = self.get_replies(c, username)
                    comment_group.extend(replies)
                # Skip deleted top level comments with no replies
                if len(comment_group) == 1 and comment_group[0].deleted:
                    continue
                comment_list.append(comment_group)

            # Custom serializing for padding/vote status, etc.
            results = []
            profile = UserProfile.objects.filter(user__username=username).first()
            blocked_users, reported_comments = [], []
            if profile:
                blocked_users = profile.blocked_users.all()
                reported_comments = profile.reported_comments.all()
            for sub_list in comment_list:
                serialized_sublist = []
                # Entire thread parent, default padding
                depth = 10
                padding_dict = {}
                for c in sub_list:
                    # Replies
                    c_dict = model_to_dict(c)
                    avatar = None
                    comment_profile = UserProfile.objects.filter(user=c.user).first()
                    if comment_profile and comment_profile.profile_image:
                        if (
                            comment_profile.user.username == username
                            or comment_profile.avatar_approved
                        ):
                            avatar = (
                                f"{CLOUDFRONT_DOMAIN}/{comment_profile.profile_image}"
                            )
                    if not c.parent:
                        c_dict["depth"] = depth
                    else:
                        # If parent is in dict, inherit its padding
                        if c.parent in padding_dict:
                            depth = padding_dict[c.parent]
                        else:
                            # Otherwise add new parent to dict
                            if depth <= MAX_COMMENT_DEPTH:
                                depth += REPLY_DEPTH
                            padding_dict[c.parent] = depth
                        c_dict["depth"] = depth
                    c_dict["time_since"] = c.time_since
                    c_dict["user"] = c.user.username
                    c_dict["avatar"] = avatar
                    c_dict["vote_status"] = self.get_vote_status(username, c)
                    c_dict["edited"] = c.time_since_edit
                    c_dict["blocked"] = False
                    c_dict["reported"] = False
                    if c in reported_comments:
                        c_dict["reported"] = True
                    if c.user in blocked_users:
                        c_dict["blocked"] = True

                    serialized_sublist.append(c_dict)
                results.append(serialized_sublist)
            results = {"results": results}
            return Response(results)
        elif activity:
            comments = Comment.objects.filter(
                user__username=activity, deleted=False
            ).order_by("-id")[:50]
            serializer = CommentSerializer(comments, many=True)
            results = {"results": serializer.data}
            return Response(results)

        else:
            raise RequestError("Please provide a holiday for comments")


class UserNotificationsView(generics.GenericAPIView):
    queryset = UserNotifications.objects.all()
    serializer_class = UserNotificationsSerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # News page
        notifications = UserNotifications.objects.filter(
            notification_type=NEWS_NOTIFICATION
        ).order_by("-id")[:20]
        serializer = UserNotificationsSerializer(notifications, many=True)
        results = {"results": serializer.data}
        return Response(results)

    def post(self, request):
        username = request.POST.get("username", None)
        clear_notifications = request.POST.get("clear_notifications", None)
        mark_read_id = request.POST.get("mark_read_id", None)
        if mark_read_id:
            mark_read_type = request.POST.get("mark_read_type", None)
            # n_type used to find unique type/pk combo, can have many in this table
            n_type = None
            if mark_read_type == "comment":
                n_type = COMMENT_NOTIFICATION
            elif mark_read_type == "post":
                n_type = POST_NOTIFICATION
            elif mark_read_type == "like":
                n_type = LIKE_NOTIFICATION
            # Can add more types in the future
            if n_type is not None:
                notification = UserNotifications.objects.filter(
                    notification_type=n_type, notification_id=mark_read_id
                ).first()
                if notification:
                    notification.read = True
                    notification.save()
            else:
                raise RequestError(f"Notification type {mark_read_type} not valid")
            unread = UserNotifications.objects.filter(
                user__username=username, read=False
            ).count()
            results = {"status": HTTP_200_OK, "unread": unread}
            return Response(results)

        notifications = UserNotifications.objects.filter(
            Q(user__username=username)
            | (Q(notification_type=NEWS_NOTIFICATION) & Q(user__isnull=True))
        ).order_by("-id")[:20]
        unread = UserNotifications.objects.filter(user__username=username, read=False)
        serializer = UserNotificationsSerializer(notifications, many=True)
        results = {"results": serializer.data, "unread": unread.count()}
        if clear_notifications:
            unread.update(read=True)
        return Response(results)


@api_view(["GET"])
def tweets_view(request):
    page = int(request.GET.get("page", 0))
    TWEET_PAGE_SIZE = 30
    s = Search(using=settings.ES_CLIENT, index=settings.TWEET_INDEX_NAME).sort(
        "-twitter_id"
    )
    # total = s.count()
    chunk = page * TWEET_PAGE_SIZE
    # s = s[0:total]
    s = s[chunk : chunk + TWEET_PAGE_SIZE]
    hits = s.execute().hits
    results = hits.hits
    response = []
    for hit in results:
        h = hit["_source"].to_dict()
        tweet_timestamp = h["timestamp"]
        dt = datetime.strptime(tweet_timestamp, "%a %b %d %H:%M:%S +0000 %Y")
        utc = dt.replace(tzinfo=pytz.UTC)
        time_ago = humanize.naturaltime(datetime.now(timezone.utc) - utc)
        time_since = normalize_time(time_ago, "precise", short=True)
        h["timestamp"] = time_since
        h["body"] = html.unescape(h["body"])
        response.append(h)

    return Response(response)


class PostDetail(generics.RetrieveUpdateAPIView):
    serializer_class = PostSerializer
    permission_classes = [UpdateObjectPermission]
    queryset = Post.objects.all()

    def patch(self, request, *args, **kwargs):

        data = request.data.copy()
        updated_post = self.get_object()
        if not self.get_queryset().count():
            raise RequestError("No posts available for update")
        profile = UserProfile.objects.get(
            device_id=data["device_id"], user__username=data["username"]
        )
        data["user"] = profile.user.id
        new_image = request.FILES.get("post_image", None)

        if new_image:
            settings.S3_CLIENT.Bucket(S3_BUCKET_NAME).put_object(
                Key=str(new_image), Body=new_image
            )
            data["image"] = f"{S3_BUCKET_IMAGES}/{new_image}"
        else:
            # Cleared image from edit
            remove_image = data.pop("clear_image", None)
            if remove_image is not None:
                data["image"] = None

        if "report" in data:
            block = True if data["block"] in TRUTHY_STRS else False
            current_reports = updated_post.reports
            data["reports"] = current_reports + 1
            profile.reported_posts.add(updated_post)
            if block:
                profile.blocked_users.add(updated_post.user)

            send_slack(
                f"[*REPORT RECEIVED*] *{data['username']}* has submitted a report for a post by *{updated_post.user}*,"
                f" on *{updated_post.holiday.name}*. See post below.\n"
                f"```{updated_post.content}```\n"
                f"- Link to post in Admin: https://holidailyapp.com/admin/api/post/{updated_post.id}/"
            )

        if "content" in data and data["content"] != updated_post.content:
            data["edited"] = timezone.now()

        if "like" in data:
            liked = data["like"] in TRUTHY_STRS
            current_likes = updated_post.likes
            author = UserProfile.objects.get(user=updated_post.user)
            if liked:
                data["likes"] = current_likes + 1
                author.confetti += 1
                updated_post.user_likes.add(profile.user)
                # No need to notify if liking their own post
                if updated_post.user != profile.user:
                    cache_key = (
                        f"post_like_notification_{updated_post.id}_{profile.user.id}"
                    )
                    if not cache.get(cache_key):
                        cache.set(cache_key, 1, 300)
                        notify_liked_user(updated_post, profile.user)
            else:
                data["likes"] = current_likes - 1
                author.confetti -= 1
                updated_post.user_likes.remove(profile.user)
            author.save(update_fields=["confetti"])
        serializer = self.get_serializer(self.get_object(), data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class PostList(APIView):

    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get(self, request):
        holiday_id = request.GET.get("holiday_id")
        username = request.GET.get("username")
        if holiday_id:
            h = Holiday.objects.filter(pk=holiday_id).first()
            if h:
                posts = Post.objects.filter(holiday=h, deleted=False)
                if username:
                    profile = UserProfile.objects.get(user__username=username)
                    blocked_users = profile.blocked_users.all()
                    reported_posts = profile.reported_posts.all().only("id")
                    posts = posts.exclude(user__in=blocked_users).exclude(
                        id__in=reported_posts
                    )
                posts = posts.order_by("-id")
                # TODO pagination
                serializer = PostSerializer(
                    posts, many=True, context={"username": username}
                )
                results = {"results": serializer.data}
                return Response(results)
            else:
                results = {
                    "status": HTTP_200_OK,
                    "message": f"Holiday {holiday_id} does not exist",
                }
                return Response(results)
        raise RequestError("Please pass a holiday id")

    def post(self, request):
        username = request.POST.get("username")
        content = request.POST.get("content")
        holiday_id = request.POST.get("holiday_id")
        post_image = request.FILES.get("post_image", None)
        user = User.objects.filter(username=username).first()
        holiday = Holiday.objects.filter(pk=holiday_id).first()
        if user and holiday:
            image_link = None
            if post_image:
                settings.S3_CLIENT.Bucket(S3_BUCKET_NAME).put_object(
                    Key=str(post_image), Body=post_image
                )

                image_link = f"{S3_BUCKET_IMAGES}/{post_image}"
            new_post = Post.objects.create(
                user=user,
                content=content,
                holiday=holiday,
                timestamp=timezone.now(),
                image=image_link,
            )
            if content:
                notify_mentioned_users(new_post)
            results = {
                "status": HTTP_200_OK,
                "post_id": new_post.id,
                "image": new_post.image,
            }
            return Response(results)
        else:
            raise RequestError("User or holiday does not exist")
