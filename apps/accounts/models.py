"""The project's own user model, and the rules for who may manage whom (brief 010).

``User`` was defined up front so staff-profile rules have one home from day one. Brief 010
adds that home's first real rules: who may change a person on the Staff and access screens,
who may give full access, and the guards that stop anyone locking themselves or the whole desk
out. They live here, not in the views or forms, so every screen that touches a user (and every
test) asks the same questions and gets the same answers.
"""

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models

# Django's built-in model permissions on ``User`` that gate Staff and access (D2). Defined once
# here, the model that owns them; the views import them (review round 1, nit 5).
VIEW_USER_PERMISSION = "accounts.view_user"
ADD_USER_PERMISSION = "accounts.add_user"
CHANGE_USER_PERMISSION = "accounts.change_user"

# Criterion 13's guard errors. ``{name}`` is the target's ``__str__``.
OWN_SIGN_IN_ERROR = (
    "You can't switch off your own sign-in. Ask someone else with Staff and access to do it."
)
OWN_FULL_ACCESS_ERROR = (
    "You can't remove your own full access. Ask another person with full access to do it."
)
LAST_SUPERUSER_ERROR = (
    "{name} is the only person with full access. Give someone else full access first."
)


def permission_labels(permissions):
    """``{"app_label.codename", …}`` for some ``Permission`` rows, the form Django's
    ``get_all_permissions()`` uses, so the two can be compared as sets.

    Reads ``content_type`` per row, so callers pass rows whose content type is prefetched
    (criterion 35).
    """
    return {f"{p.content_type.app_label}.{p.codename}" for p in permissions}


class UserQuerySet(models.QuerySet):
    """The listing and guard queries for users, so views never write their own filters."""

    def with_granted_permissions(self):
        """Prefetch what :meth:`User.granted_permissions` reads (criterion 35).

        Roles, their permissions and those permissions' content types, plus the user's own
        permissions: then asking "may the viewer change this person?" costs no query per
        person, however many there are.
        """
        return self.prefetch_related(
            "groups",
            "groups__permissions__content_type",
            "user_permissions__content_type",
        )

    def staff_list(self):
        """Everyone, for the Staff and access list (criterion 5).

        People who can sign in come first (``-is_active``), then by name, with the username as
        the tiebreak so the order is total and paging is stable. Roles and permissions are
        prefetched, so the list, including each row's "may the viewer change them?" answer,
        costs the same number of queries for 3 people as for 40 (criteria 6 and 35).
        """
        return self.with_granted_permissions().order_by(
            "-is_active", "last_name", "first_name", "username"
        )

    def active_superusers(self):
        """Everyone who has full access and can still sign in: the last-superuser guard's pool."""
        return self.filter(is_active=True, is_superuser=True)


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    """Django's ``UserManager`` plus :class:`UserQuerySet`'s methods.

    It stays a subclass of Django's manager so ``create_user``, ``create_superuser`` and
    ``manage.py createsuperuser`` keep working (criterion 22), and it's serialised into the
    migrations (``use_in_migrations`` is inherited) so data migrations get it too.
    """


class User(AbstractUser):
    """Staff user of the Technology Management Desk.

    Defined up front so fields (department, phone, role…) can be added later
    without swapping the user model mid-project. Users are never deleted, only switched off
    (``is_active=False``): past decisions such as ``LinkRequest.decided_by`` must keep pointing
    at a real person (brief 010, D4).
    """

    objects = UserManager()

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username

    def clean(self):
        """Store email trimmed and lower-cased, so "same address" means the same text.

        The Staff and access forms treat two addresses differing only in letter case as the
        same person (criterion 9). The column stays non-unique, as ``AbstractUser`` defines it:
        the form enforces uniqueness, and a database constraint would be a risky migration over
        existing rows for no extra safety on these screens.
        """
        super().clean()
        self.email = (self.email or "").strip().lower()

    @property
    def initials(self):
        """Up to two capital letters that stand in for the user, e.g. in the avatar.

        The fallback order (first and last name, else whichever one is set, else
        the username) is a rule, so it lives here rather than as a filter chain
        repeated in templates; brief 005 reuses it for "who is on it". Names are
        stripped first so a name made only of spaces counts as unset. A saved user
        always has a username, so the result is never empty for one.
        """
        names = [n.strip() for n in (self.first_name, self.last_name) if n and n.strip()]
        if not names:
            names = [self.username.strip()] if self.username else []
        return "".join(name[0] for name in names).upper()

    # ------------------------------------------------------------------ management rules

    @staticmethod
    def can_grant_full_access(actor):
        """Only someone with full access may give or take full access (criteria 10 and 13).

        A static method because the add form asks it before any target user exists; it's also
        callable on an instance. ``is_active`` is checked too, because Django's own permission
        checks refuse an inactive superuser and this rule must never be looser than them.
        """
        return bool(actor and actor.is_active and actor.is_superuser)

    @staticmethod
    def can_give_role(actor, group):
        """May ``actor`` give this role to someone, or take it away (criterion 31, D13)?

        A superuser may give any role. Anyone else may give a role only when they already hold
        every right in it, so nobody hands out more than they have: a Staff manager who isn't
        in ``IT desk`` can't give ``IT desk``, and a role a later brief adds is covered with no
        list of role names here. Giving and removing are the same rule, because only people
        who hold a role should decide who has it.

        Static, like :meth:`can_grant_full_access`, because it's about the actor and the role,
        not about the person being changed. ``group.permissions`` should be prefetched with
        their content types (criterion 35). ``get_all_permissions()`` is cached on the actor,
        so it runs once per request.
        """
        if User.can_grant_full_access(actor):
            return True
        if actor is None:
            return False
        return permission_labels(group.permissions.all()) <= actor.get_all_permissions()

    def granted_permissions(self):
        """Every right this person's roles and own permissions grant, as ``"app.codename"``.

        Unlike Django's ``get_all_permissions()``, this doesn't depend on whether they can
        sign in. Django reports no rights at all for a switched-off user, which would make a
        switched-off Staff manager look harmless to :meth:`can_be_managed_by`, so a peer could
        switch them back on (D13). Reads only what
        :meth:`UserQuerySet.with_granted_permissions` prefetches.
        """
        from_roles = (p for group in self.groups.all() for p in group.permissions.all())
        return permission_labels(from_roles) | permission_labels(self.user_permissions.all())

    def can_be_managed_by(self, actor):
        """May ``actor`` open this person's change and set-password pages (criterion 11)?

        - A superuser may change anyone.
        - Anyone else needs ``accounts.change_user``, and then may open:
          - their own record, where their roles are read-only (criterion 33) and their
            password is changed on "Change your password" (criterion 34);
          - someone without full access, who isn't a Staff manager themselves, and whose
            rights are all rights the actor holds.

        Why so tight (D8 as amended, D13): setting someone's password is a way to become them,
        so reaching a person with full access, another Staff manager, or anyone with rights
        the actor lacks would let a Staff manager take those rights by the back door.
        """
        if self.can_grant_full_access(actor):
            return True
        if actor is None or not actor.has_perm(CHANGE_USER_PERMISSION):
            return False
        if actor.pk == self.pk:
            return True
        if self.is_superuser:
            return False
        granted = self.granted_permissions()
        return CHANGE_USER_PERMISSION not in granted and granted <= actor.get_all_permissions()

    def access_change_error(self, *, actor, is_active, is_superuser):
        """The field errors for changing this person's sign-in and full access, or ``{}``.

        ``self`` must hold the *stored* values (the change form calls this from ``clean()``,
        before the typed values are copied onto the instance); ``is_active`` and
        ``is_superuser`` are the values asked for. The rules (criterion 13):

        - nobody switches off their own sign-in, or removes their own full access, so no one
          can lock themselves out by mistake;
        - the only active superuser can't be switched off or lose full access, so the desk
          always keeps someone who can change everyone.

        The self rules win when both apply to a field, because their advice is the one that
        helps. A staff manager's form has no ``is_superuser`` field, so the caller passes the
        stored value and nothing here fires for it.

        The last-superuser check locks rows with ``select_for_update()``, so call this inside a
        transaction; requests always are (``ATOMIC_REQUESTS``).
        """
        losing = {
            "is_active": self.is_active and not is_active,
            "is_superuser": self.is_superuser and not is_superuser,
        }
        if not any(losing.values()):
            return {}

        own_errors = {"is_active": OWN_SIGN_IN_ERROR, "is_superuser": OWN_FULL_ACCESS_ERROR}
        is_self = actor is not None and actor.pk == self.pk
        is_last_superuser = False
        if self.is_active and self.is_superuser:
            # Lock the whole pool, in pk order, so two superusers switching each other off at
            # the same moment can't both pass: the second waits, then sees the first's change.
            pool = type(self).objects.active_superusers().select_for_update().order_by("pk")
            others = [pk for pk in pool.values_list("pk", flat=True) if pk != self.pk]
            is_last_superuser = not others
        errors = {}
        for field, lost in losing.items():
            if not lost:
                continue
            if is_self:
                errors[field] = own_errors[field]
            elif is_last_superuser:
                errors[field] = LAST_SUPERUSER_ERROR.format(name=self)
        return errors
