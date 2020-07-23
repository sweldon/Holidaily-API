from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from api import views
from portal.views import index

urlpatterns = [
    path("", index),
    path("holiday/", index),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("user/", views.UserProfileDetail.as_view(), name="user-profile-detail"),
    path("users/top", views.UserList.as_view(), name="top-users"),
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
    path("tweets/", views.tweets_view, name="tweets_view"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
