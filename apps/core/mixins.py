"""View mixins every section shares.

They live in ``core`` because apps don't import each other's views (CLAUDE.md, loose
coupling), yet every signed-in section needs the same gate. ``zoom`` (briefs 005 and 008) and
``accounts`` (brief 010) both use :class:`SignedInPermissionMixin` from here, so the rule for
"not signed in" versus "signed in without the permission" is written once.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class SignedInPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Anonymous: redirect to sign in. Signed in without the permission: 403.

    ``LoginRequiredMixin`` comes first so a visitor who isn't signed in is sent to sign in
    (with ``next``) rather than shown a 403; a signed-in user who lacks the permission gets
    ``PermissionDenied``, which Django's default ``handler403`` renders with
    ``templates/403.html`` (brief 010, D11). Each view sets ``permission_required``, and may
    extend ``has_permission()`` with an object-level rule.
    """
