"""Sign-in, sign-out, Staff and access, and "Change your password" (namespace ``accounts``).

Sign-in and sign-out are Django's own views. The staff pages (brief 010) have no delete and
no role editor: people are switched off, not deleted (D4), and roles are fixed by migrations
(D3), so neither has a URL.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password/", views.OwnPasswordChangeView.as_view(), name="password_change"),
    path("staff/", views.StaffListView.as_view(), name="staff"),
    path("staff/add/", views.StaffCreateView.as_view(), name="staff_add"),
    path("staff/<int:pk>/edit/", views.StaffUpdateView.as_view(), name="staff_edit"),
    path("staff/<int:pk>/password/", views.StaffSetPasswordView.as_view(), name="staff_password"),
]
