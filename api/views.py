from django.db.models import Q
from django.forms import model_to_dict

from holidaily.utils import send_slack, sync_devices, send_push_to_user
from .models import (
    Holiday,
    UserHolidayVotes,
    Comment,
    UserNotifications,
    UserCommentVotes,
    UserProfile,
    S3_CLIENT,
)
from .serializers import (
    UserSerializer,
    HolidaySerializer,
    CommentSerializer,
    UserNotificationsSerializer,
    UserProfileSerializer,
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
    ANDROID_VERSION,
    ANDROID,
    IOS_VERSION,
    IOS,
    S3_BUCKET_NAME,
    CLOUDFRONT_DOMAIN,
)
from api.exceptions import RequestError, DeniedError
import re
from holidaily.settings import COMMENT_PAGE_SIZE


def add_notification(n_id, n_type, user, content, title):
    """
    Add a new notification for users
    :param n_id: notification id, pk
    :param n_type: notification type
    :param user: user to receive notification
    :param content: body of notification
    :param title: title of notification
    :return: the new notification
    """
    new_notification = UserNotifications.objects.create(
        notification_id=n_id,
        notification_type=n_type,
        user=user,
        content=content,
        title=title,
    )
    return new_notification


class UserList(APIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def post(self, request):
        username = request.POST.get("username", None)
        device_id = request.POST.get("device_id", None)
        platform = request.POST.get("platform", None)
        version = request.POST.get("version", None)
        requesting_user = request.POST.get("requesting_user", None)
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
                if device_id and platform:
                    sync_devices(device_id, platform, user)
        elif device_id and platform:
            sync_devices(device_id, platform)
            results = {"status": HTTP_200_OK, "message": "OK"}
            return Response(results)
        elif requesting_user:
            user_list = UserProfile.objects.filter(confetti__gt=0).order_by("confetti")[
                :50
            ]
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
        profile = UserProfile.objects.filter(user__username=username).first()
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
            results = {"message": "User was made premium!", "status": HTTP_200_OK}
            return Response(results)

        elif reward:
            # User earned confetti
            reward_amount = request.POST.get("reward", None)
            profile.confetti += int(reward_amount)
            profile.save()
            results = {
                "message": f"{reward_amount} confetti awarded to {username}",
                "status": HTTP_200_OK,
            }
            return Response(results)
        elif check_update:
            version = request.POST.get("version", None)
            platform = request.POST.get("platform", None)
            requires_update = False
            if platform == ANDROID and version != ANDROID_VERSION:
                requires_update = True
            elif platform == IOS and version != IOS_VERSION:
                requires_update = True
            results = {"needs_update": requires_update, "status": HTTP_200_OK}
            return Response(results)
        elif avatar:
            file_name = f"{username}_{avatar}"
            S3_CLIENT.Bucket(S3_BUCKET_NAME).put_object(Key=file_name, Body=avatar)
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
            results = {"results": serializer.data}
            return Response(results)
        else:
            serializer = UserProfileSerializer(profile)
            results = {"results": serializer.data}
            return Response(results)


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class HolidayList(generics.GenericAPIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        top_holidays = request.GET.get("top", None)
        by_name = request.GET.get("name", None)
        if top_holidays:
            # Top Holidays
            holidays = Holiday.objects.filter(active=True).order_by("-votes")[:10]
        elif by_name:
            holidays = Holiday.objects.filter(name=by_name, active=True)
        else:
            # Default list of today's holidays
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
        else:
            # Most recent holidays
            today = timezone.now()
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
                description = request.POST.get("description", None)
                date = request.POST.get("date", None)
                date_formatted = datetime.strptime(date.split(" ")[0], "%m/%d/%Y")
                Holiday.objects.create(
                    name=submission,
                    description=description,
                    date=date_formatted,
                    creator=User.objects.get(username=username),
                    active=False,
                )
                send_slack(
                    f"[*USER HOLIDAY SUBMISSION*] _{username}_ has submitted a new holiday: *{submission}*."
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
            holiday.save(from_app=True)
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


class CommentDetail(APIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def get_object(self, pk):
        try:
            return Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            raise HTTP_404_NOT_FOUND

    def get(self, request, pk):
        comment = self.get_object(pk)
        serializer = CommentSerializer(comment)
        results = {"results": serializer.data}
        return Response(results)

    def post(self, request, pk):
        vote = request.POST.get("vote", None)
        username = request.POST.get("username", None)
        report = request.POST.get("report", None)
        block_request = request.POST.get("block", None)
        block = True if block_request in TRUTHY_STRS else False
        comment = self.get_object(pk)

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
                f"[*REPORT RECEIVED*] _{username}_ has submitted a report for a comment by _{comment.user}_,"
                f" on _{comment.holiday.name}_. See comment below.\n"
                f"```{comment.content}```\n"
                f"- Link to comment in Admin: https://holidailyapp.com/admin/api/comment/{comment.id}/"
            )
            results = {"status": HTTP_200_OK, "message": "OK"}
            return Response(results)
        else:
            comment = self.get_object(pk)
            serializer = CommentSerializer(comment, context={"username": username})
            results = {"results": serializer.data}
            return Response(results)


class CommentList(generics.GenericAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        holiday = request.GET.get("holiday", None)
        if holiday:
            comments = Holiday.objects.get(id=holiday).comment_set.order_by("-votes")
        else:
            raise RequestError("Please provide a holiday for comments")
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
                # notifications = UserNotifications.objects.filter(
                #     notification_id=comment.id, notification_type=COMMENT_NOTIFICATION
                # )
                # for n in notifications:
                #     n.delete()
                # comment.delete()
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
            holiday = Holiday.objects.get(id=holiday)
            parent = Comment.objects.get(id=parent_id) if parent_id else None
            user = User.objects.get(username=username)

            if UserProfile.objects.get(user=user).active:
                new_comment = Comment(
                    content=content,
                    holiday=holiday,
                    user=user,
                    timestamp=timezone.now(),
                    parent=parent,
                )
                new_comment.save()
                mentions = list(set(re.findall(r"@([^\s.,\?\"\'\;]+)", content)))
                notifications = []
                for user_mention in mentions:
                    if user_mention == username:
                        continue
                    # Get user profiles, exclude self if user mentions themself for some reason
                    user_to_notify = User.objects.filter(username=user_mention).first()
                    if user_to_notify:
                        try:
                            send_push_to_user(
                                user_to_notify,
                                f"{username} mentioned you!",
                                f"{content[:50]}{'...' if len(content) > 50 else ''}",
                                new_comment,
                            )
                        except:  # noqa
                            print(
                                f"Error sending push, bad device token for {user_to_notify}"
                            )
                        n = UserNotifications(
                            notification_id=new_comment.pk,
                            notification_type=COMMENT_NOTIFICATION,
                            user=user_to_notify,
                            content=content,
                            title=f"{username} on {holiday.name}",
                        )
                        notifications.append(n)
                UserNotifications.objects.bulk_create(notifications)
                results = {"status": HTTP_200_OK, "message": "OK"}
                return Response(results)
            else:
                raise DeniedError(
                    "Sorry! You've been banned and can no longer comment."
                )

        elif holiday:
            page = int(request.POST.get("page", 0))
            chunk = page * COMMENT_PAGE_SIZE
            comment_list = []
            # All the parents with no children
            comments = (
                Holiday.objects.get(id=holiday)
                .comment_set.filter(parent__isnull=True)
                .order_by("-votes", "-id")
            )[chunk : chunk + COMMENT_PAGE_SIZE]
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
        notifications = UserNotifications.objects.filter(
            Q(user__username=username)
            | (Q(notification_type=NEWS_NOTIFICATION) & Q(user__isnull=True))
        ).order_by("-id")[:20]
        serializer = UserNotificationsSerializer(notifications, many=True)
        results = {"results": serializer.data}
        return Response(results)
