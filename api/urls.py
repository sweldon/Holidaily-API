from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from api import views

urlpatterns = [
    path("", views.api_root),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("users/<int:pk>/", views.UserDetail.as_view(), name="user-detail"),
    path("holidays/", views.HolidayList.as_view(), name="holiday-list"),
    path("holidays/<int:pk>/", views.HolidayDetail.as_view(), name="holiday-detail"),
    path("comments/<int:pk>/", views.CommentDetail.as_view(), name="comment-detail"),
    path("comments/", views.CommentList.as_view(), name="comment-list"),
    path("notifications/", views.UserNotificationsView.as_view(), name="notifications"),
    path("news/", views.UserNotificationsView.as_view(), name="news"),
    path("search/", views.HolidayList.as_view(), name="search"),
    path("pending/", views.UserHolidays.as_view(), name="pending"),
    path("submit/", views.UserHolidays.as_view(), name="submit"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
