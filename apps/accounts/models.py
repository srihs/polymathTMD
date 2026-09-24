"""The project's own user model, so staff-profile rules have one home from day one."""

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Staff user of the Technology Management Desk.

    Defined up front so fields (department, phone, role…) can be added later
    without swapping the user model mid-project.
    """

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username

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
