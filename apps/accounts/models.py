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
