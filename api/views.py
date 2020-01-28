from django.forms import model_to_dict

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
)
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import generics
from rest_framework.views import APIView
from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK
from api.constants import (
    UPVOTE_CHOICES,
    DOWNVOTE_CHOICES,
    SINGLE_UP,
    SINGLE_DOWN,
    UP_FROM_DOWN,
    DOWN_FROM_UP,
    DOWNVOTE_ONLY, UPVOTE_ONLY)
from api.exceptions import RequestError, DeniedError
import re
from holidaily.settings import (
    PUSH_ENDPOINT_ANDROID,
    PUSH_ENDPOINT_IOS,
    APPCENTER_API_KEY,
)
import requests
from django.conf import settings


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "users": reverse("user-list", request=request, format=format),
            "holidays": reverse("holiday-list", request=request, format=format),
        }
    )


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
    # permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        username = request.POST.get("username", None)
        if username:
            user = User.objects.get(username=username)
        else:
            raise RequestError("Please provide a username for POST requests")
        serializer = UserSerializer(user)
        results = {"results": serializer.data}
        return Response(results)


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = (permissions.IsAuthenticated,)


class HolidayList(generics.GenericAPIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        top_holidays = request.GET.get("top", None)
        by_name = request.GET.get("name", None)
        if top_holidays:
            # Top Holidays
            holidays = Holiday.objects.all().order_by("-votes")[:10]
        elif by_name:
            holidays = Holiday.objects.filter(name=by_name)
        else:
            # Default list of today's holidays
            today = timezone.now()
            holidays = Holiday.objects.filter(
                date__range=[today - timedelta(days=7), today]
            )
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
                    date=datetime.strptime(search.split(" ")[0], "%m/%d/%Y")
                )
            else:
                holidays = Holiday.objects.filter(name__icontains=search)
        else:
            # Most recent holidays
            today = timezone.now()
            if settings.TEST_MODE:
                holidays = Holiday.objects.all().order_by('-id')[:5]
            else:
                holidays = Holiday.objects.filter(
                    date__range=[today - timedelta(days=7), today]
                )

        serializer = HolidaySerializer(
            holidays, many=True, context={"username": username}
        )
        results = {"results": serializer.data}
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
    # permission_classes = (permissions.IsAuthenticated,)

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
        replies = comment.comment_set.all().order_by('-votes', '-id')

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

        if content:
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
                    print(user_mention)
                    user_mention_obj = User.objects.filter(
                        username=user_mention
                    ).first()
                    if user_mention_obj:
                        user_mention_device = UserProfile.objects.get(
                            user=user
                        ).device_id
                        if user_mention_device:
                            devices.append(user_mention_device)
                            n = UserNotifications(
                                notification_id=new_comment.pk,
                                notification_type=0,  # Comment
                                user=user_mention_obj,
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
            comment_list = []
            # All the parents with no children
            comments = Holiday.objects.get(id=holiday).comment_set.filter(parent__isnull=True).order_by('-votes', '-id')
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
                    c_dict["vote_status"] = self.get_vote_status(username, c)
                    depth += 20
                    serialized_sublist.append(c_dict)
                results.append(serialized_sublist)
            # TODO works but this is so damn slow
            results = {"results": results}
            return Response(results)
        else:
            raise RequestError("Please provide a holiday for comments")


class UserNotificationsView(generics.GenericAPIView):
    queryset = UserNotifications.objects.all()
    serializer_class = UserNotificationsSerializer
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        username = request.GET.get("username", None)
        news = request.GET.get("news", None)
        update_type = 0 if news else 1
        notifications = (
            UserNotifications.objects.filter(user__username=username)
            .exclude(notification_type=update_type)
            .order_by("-id")[:20]
        )
        serializer = UserNotificationsSerializer(notifications, many=True)
        results = {"results": serializer.data}
        return Response(results)
