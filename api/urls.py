from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from api import views

urlpatterns = [
    path("", views.api_root),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("users/<int:pk>/", views.UserDetail.as_view(), name="user-detail"),
    path("holidays/", views.HolidayList.as_view(), name="holiday-list"),
    path("holidays/<int:pk>/", views.HolidayDetail.as_view(), name="holiday-detail"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
