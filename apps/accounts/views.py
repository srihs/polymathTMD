"""The Staff and access screens and "Change your password" (brief 010).

Staff and access replaces the Django admin's user pages: list people, add someone with a
starting password, change their details, roles, full access and sign-in, and set them a new
password. Each page is gated by Django's built-in permission on ``accounts.User``
(``view_``/``add_``/``change_user``); anonymous visitors are sent to sign in and everyone else
without the permission gets 403 (``SignedInPermissionMixin``). The change and set-password
pages add an object-level rule, ``User.can_be_managed_by()``: a non-superuser reaches only
people whose rights they hold themselves, never someone with full access or another Staff
manager (D13).

The views stay thin: who may do what is on the ``User`` model, and the labels and checks are
on the forms. Every context variable is in the brief's context contract. Nobody is deleted
(D4), so there's no delete view.
"""

import copy

from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.core.mixins import SignedInPermissionMixin

from .forms import (
    OwnPasswordChangeForm,
    StaffChangeForm,
    StaffCreateForm,
    StaffSetPasswordForm,
    role_choices,
)
from .models import (
    ADD_USER_PERMISSION,
    CHANGE_USER_PERMISSION,
    VIEW_USER_PERMISSION,
    User,
)

# Success flashes (Design D.6).
PERSON_ADDED = (
    "Added {name}. Give them their username and starting password yourself, not by email."
)
PERSON_SAVED = "Saved {name}."
PASSWORD_SET = "Saved a new password for {name}. Give it to them yourself, not by email."
OWN_PASSWORD_CHANGED = "Your password was changed."


class StaffListView(SignedInPermissionMixin, ListView):
    """Everyone with a username, people who can sign in first, 50 to a page (criterion 5).

    ``can_manage`` is set on each row of the page so the template knows which names to link
    (criteria 11 and 34). It costs no query per row (criterion 35): the viewer's permissions
    are cached after the first call, and each person's rights come from ``staff_list()``'s
    prefetches.
    """

    permission_required = VIEW_USER_PERMISSION
    template_name = "accounts/staff_list.html"
    context_object_name = "people"
    paginate_by = 50

    def get_queryset(self):
        return User.objects.staff_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viewer = self.request.user
        for person in context["people"]:
            person.can_manage = person.can_be_managed_by(viewer)
        context["can_add"] = viewer.has_perm(ADD_USER_PERMISSION)
        return context


class StaffFormViewMixin(SignedInPermissionMixin):
    """What add and change share: the form's ``actor``, the ``roles`` context and the redirect.

    ``context_object_name`` is set explicitly: ``UpdateView`` would otherwise name the object
    after its model, ``user``, and overwrite the auth context processor's ``user`` (the
    viewer), which the shell and the template's "is this you?" check read (G4). ``person``
    itself is set by each view, so this mixin needs nothing from its siblings (review round 1,
    nit 3).
    """

    template_name = "accounts/staff_form.html"
    context_object_name = "person"
    is_add = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("accounts:staff")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context.update(
            roles=role_choices(form["groups"]),
            roles_read_only=form.roles_read_only,
            is_add=self.is_add,
        )
        return context


class ManagedPersonMixin(SignedInPermissionMixin):
    """The change and set-password pages: ``change_user``, and the viewer may manage the target.

    ``has_permission()`` checks the model permission first, so someone without it gets 403
    before the target is even looked up (and can't probe which ids exist). A missing target is
    404 for everyone who may manage people.

    The person is loaded with their roles' permissions prefetched, which
    ``can_be_managed_by`` compares with the viewer's.
    """

    permission_required = CHANGE_USER_PERMISSION

    @cached_property
    def person(self):
        return get_object_or_404(User.objects.with_granted_permissions(), pk=self.kwargs["pk"])

    def has_permission(self):
        return super().has_permission() and self.person.can_be_managed_by(self.request.user)


@method_decorator(sensitive_post_parameters(), name="dispatch")
class StaffCreateView(StaffFormViewMixin, CreateView):
    """Add a person with a starting password (criteria 7–10).

    ``sensitive_post_parameters()`` masks every posted value, the two passwords included, in
    error reports (criterion 17).
    """

    permission_required = ADD_USER_PERMISSION
    form_class = StaffCreateForm
    is_add = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = None
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, PERSON_ADDED.format(name=self.object))
        return response


class StaffUpdateView(ManagedPersonMixin, StaffFormViewMixin, UpdateView):
    """Change someone's details, roles, full access and sign-in (criteria 11–14).

    The form edits its own copy of the person, and the page context gets the stored one, so
    after a refused save the heading and the guard messages still name the person as saved,
    not as typed.
    """

    form_class = StaffChangeForm

    def get_object(self, queryset=None):
        return copy.copy(self.person)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.person
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, PERSON_SAVED.format(name=self.object))
        return response


@method_decorator(sensitive_post_parameters(), name="dispatch")
class StaffSetPasswordView(ManagedPersonMixin, FormView):
    """Set a new password for someone else (criterion 15).

    Django's ``SetPasswordForm`` changes the hash, and with it the session auth hash, so every
    session that person already has stops working on its next request.

    Your own pk is sent to "Change your password" instead (criterion 34, review round 1, nit
    2): setting your own password here would skip the old-password check and sign you out.
    The redirect comes after the permission check, so someone without ``change_user`` still
    gets 403, as on every other staff page.
    """

    form_class = StaffSetPasswordForm
    template_name = "accounts/staff_password.html"

    def _is_own_record(self):
        return self.person.pk == self.request.user.pk

    def get(self, request, *args, **kwargs):
        if self._is_own_record():
            return redirect("accounts:password_change")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self._is_own_record():
            return redirect("accounts:password_change")
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.person
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["person"] = self.person
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, PASSWORD_SET.format(name=self.person))
        return redirect("accounts:staff_edit", pk=self.person.pk)


class OwnPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    """Change your own password, in the shell (criterion 16).

    Django's view already requires sign-in, wraps ``dispatch`` in
    ``sensitive_post_parameters()`` and keeps the user signed in afterwards
    (``update_session_auth_hash``). The flash on Home replaces a separate "done" page.
    """

    form_class = OwnPasswordChangeForm
    success_url = reverse_lazy("core:home")
    success_message = OWN_PASSWORD_CHANGED
