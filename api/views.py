from django.forms import model_to_dict

from holidaily.utils import send_slack
from .models import (
    Holiday,
    UserHolidayVotes,
    Comment,
    UserNotifications,
    UserCommentVotes,
    UserProfile,
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
)
from api.exceptions import RequestError, DeniedError
import re
from holidaily.settings import (
    PUSH_ENDPOINT_ANDROID,
    PUSH_ENDPOINT_IOS,
    APPCENTER_API_KEY,
    COMMENT_PAGE_SIZE,
)
import requests
from django.conf import settings


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

    def get(self, request):
        top_users = UserProfile.objects.all()[:20]
        user_list = sorted(top_users, key=lambda x: x.confetti)
        serializer = UserProfileSerializer(user_list, many=True)
        results = {"results": serializer.data}
        return Response(results)

    def post(self, request):
        username = request.POST.get("username", None)
        if username:
            user = User.objects.get(username=username)
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
        token = request.POST.get("token", None)
        reward = request.POST.get("reward", None)
        logout = request.POST.get("logout", None)

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
            profile.rewards += int(reward_amount)
            profile.save()
            results = {
                "message": f"{reward_amount} confetti awarded to {username}",
                "status": HTTP_200_OK,
            }
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
                    date=datetime.strptime(search.split(" ")[0], "%m/%d/%Y"),
                    active=True,
                )
            else:
                holidays = Holiday.objects.filter(name__icontains=search, active=True)

        else:
            # Most recent holidays
            today = timezone.now()
            if settings.DEBUG:
                holidays = Holiday.objects.filter(active=True).order_by("-id")[:5]
            else:
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
                print(date, date_formatted)
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
        comment = self.get_object(pk)

        if vote:
            vote = int(vote)
            if vote in SINGLE_UP:
                comment.votes += 1
            elif vote in SINGLE_DOWN:
                comment.votes -= 1
            elif vote == UP_FROM_DOWN:
                comment.votes += 2
            elif vote == DOWN_FROM_UP:
                comment.votes -= 2
            else:
                raise RequestError("Invalid vote type")
            comment.save()

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

    def get_replies(self, comment, depth, username):
        """ Recursively get comment reply chain """
        reply_chain = []
        replies = comment.comment_set.all().order_by("-votes", "-id")

        for c in replies:
            reply_chain.append(c)
            if c.comment_set.all().count() > 0:
                depth += 20
                child_replies = self.get_replies(c, depth, username)
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
                devices = []
                notifications = []
                for user_mention in mentions:
                    user_mention_profile = UserProfile.objects.filter(
                        user__username=user_mention, logged_out=False
                    ).first()
                    if user_mention_profile:
                        user_mention_device = user_mention_profile.device_id
                        if user_mention_device:
                            devices.append(user_mention_device)
                            n = UserNotifications(
                                notification_id=new_comment.pk,
                                notification_type=COMMENT_NOTIFICATION,  # Comment
                                user=user_mention_profile.user,
                                content=f"{username} mentioned you in a comment on {holiday.name}",
                                title="You were mentioned!",
                            )
                            notifications.append(n)
                UserNotifications.objects.bulk_create(notifications)
                new_comment_time_since = new_comment.timestamp.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                comment_content = content.encode("ascii", "ignore").decode("ascii")
                holiday_name = holiday.name.encode("ascii", "ignore").decode("ascii")
                data = {
                    "notification_content": {
                        "name": "Comment Mention",
                        "title": "{} mentioned you in a comment".format(username),
                        "body": str(comment_content),
                        "custom_data": {
                            "comment_id": int(new_comment.id),
                            "holiday_id": holiday.pk,
                            "content": str(comment_content),
                            "comment_user": str(username),
                            "time_since": new_comment_time_since,
                            "holiday_name": holiday_name,
                        },
                    },
                    "notification_target": {
                        "type": "devices_target",
                        "devices": devices,
                    },
                }
                headers = {"X-API-Token": APPCENTER_API_KEY}
                requests.post(PUSH_ENDPOINT_ANDROID, headers=headers, json=data)
                requests.post(PUSH_ENDPOINT_IOS, headers=headers, json=data)
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
                depth = 0
                if c.comment_set.all().count() > 0:
                    replies = self.get_replies(c, depth, username)
                    comment_group.extend(replies)
                comment_list.append(comment_group)

            # TODO: the actual object is good just needs to be serialized'
            results = []
            for sub_list in comment_list:
                serialized_sublist = []
                depth = 10
                for c in sub_list:
                    c_dict = model_to_dict(c)
                    c_dict["depth"] = depth
                    c_dict["time_since"] = c.time_since
                    c_dict["user"] = c.user.username
                    c_dict["vote_status"] = self.get_vote_status(username, c)
                    depth += 20
                    serialized_sublist.append(c_dict)
                results.append(serialized_sublist)
            results = {"results": results}
            return Response(results)
        else:
            raise RequestError("Please provide a holiday for comments")


class UserNotificationsView(generics.GenericAPIView):
    queryset = UserNotifications.objects.all()
    serializer_class = UserNotificationsSerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        notifications = UserNotifications.objects.filter(
            notification_type=NEWS_NOTIFICATION
        ).order_by("-id")[:20]
        serializer = UserNotificationsSerializer(notifications, many=True)
        results = {"results": serializer.data}
        return Response(results)

    def post(self, request):
        username = request.POST.get("username", None)
        notifications = (
            UserNotifications.objects.filter(user__username=username)
            .exclude(notification_type=NEWS_NOTIFICATION)
            .order_by("-id")[:20]
        )
        serializer = UserNotificationsSerializer(notifications, many=True)
        results = {"results": serializer.data}
        return Response(results)
