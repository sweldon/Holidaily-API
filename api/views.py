from .models import Holiday, UserHolidayVotes
from .serializers import UserSerializer, HolidaySerializer
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import generics, permissions
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "users": reverse("user-list", request=request, format=format),
            "holidays": reverse("holiday-list", request=request, format=format),
        }
    )


class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class HolidayList(generics.GenericAPIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = (permissions.IsAuthenticated,)

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
        holiday_id = request.POST.get("id", None)

        if holiday_id:
            # Single holiday
            holidays = Holiday.objects.filter(id=holiday_id)
        else:
            # List of holidays
            today = timezone.now()
            holidays = Holiday.objects.filter(
                date__range=[today - timedelta(days=7), today]
            )

        serializer = HolidaySerializer(holidays, many=True)
        if username:
            user = User.objects.get(username=username)
            for h in serializer.data:
                celebrating = UserHolidayVotes.objects.filter(
                    (Q(user=user) & Q(holiday__id=h["id"]))
                    & (Q(choice=1) | Q(choice=4))
                ).exists()
                h["celebrating"] = celebrating

        results = {"results": serializer.data}
        return Response(results)


class HolidayDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = (permissions.IsAuthenticated,)
