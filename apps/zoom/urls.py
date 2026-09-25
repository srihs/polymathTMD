"""URLs for Zoom link requests. Referenced only by name (``zoom:…``)."""

from django.urls import path

from . import views

app_name = "zoom"

urlpatterns = [
    path("request/", views.LinkRequestCreateView.as_view(), name="request"),
    path("request/sent/", views.RequestSentView.as_view(), name="request_sent"),
    path("confirm/<str:token>/", views.ConfirmView.as_view(), name="confirm"),
    path("confirmed/<str:token>/", views.ConfirmedView.as_view(), name="confirmed"),
    path("requests/", views.QueueView.as_view(), name="queue"),
    path("requests/<int:pk>/", views.LinkRequestDetailView.as_view(), name="detail"),
    path("requests/<int:pk>/approve/", views.ApproveView.as_view(), name="approve"),
    path("requests/<int:pk>/reject/", views.RejectView.as_view(), name="reject"),
    path("timetable/", views.TimetableMonthView.as_view(), name="timetable"),
    path(
        "timetable/<int:year>/<int:month>/<int:day>/",
        views.TimetableDayView.as_view(),
        name="timetable_day",
    ),
    path("accounts/", views.HostAccountListView.as_view(), name="accounts"),
    path("accounts/add/", views.HostAccountCreateView.as_view(), name="account_add"),
    path("accounts/<int:pk>/edit/", views.HostAccountUpdateView.as_view(), name="account_edit"),
]
