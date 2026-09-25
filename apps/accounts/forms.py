"""Forms for the Staff and access screens and "Change your password" (brief 010).

Django's own auth forms do the hard parts (password validators, hashing, the mismatch check,
the old-password check). The subclasses here only change what people read: labels, help and
widget attributes, set in ``__init__`` to match the brief's pinned copy (D7 as amended, G2,
G3). The stated exceptions are the staff forms' ``clean_email`` (one address per person, in
any letter case), their ``actor`` handling (only someone with full access sees, or can post,
the full-access box) and ``clean_groups`` (only roles the actor may give, D13).

Rules about *who* may change *what* are on the ``User`` model (``can_grant_full_access``,
``can_give_role``, ``access_change_error``); the forms only ask it and put the answer on the
right field or widget.
"""

from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm,
    SetPasswordForm,
    UserCreationForm,
    UsernameField,
)
from django.contrib.auth.models import Group

from .models import User

EMAIL_REQUIRED = "Type their work email address. Emails about Zoom requests go to it."
EMAIL_TAKEN = "Someone else already uses this email address."
# Criterion 32: a crafted POST that adds a role the actor can't give.
ROLE_NOT_YOURS = "You can only give roles whose rights you have yourself."
TYPE_IT_AGAIN = "Type it again"
NEW_PASSWORD_AGAIN_HELP = "Type the new password again, to check for typos."

# Design D.6: (label, help) for every staff-form field. ``None`` help keeps Django's.
STAFF_FIELD_COPY = {
    "first_name": ("First name", "Like Nimali. You can leave the names empty."),
    "last_name": ("Last name", "Like Perera. Without a name, the desk shows their username."),
    "username": ("Username", "They type this to sign in. Letters, numbers and @ . + - _ only."),
    "email": ("Work email", "Emails about Zoom requests go here."),
    "groups": (
        "Roles",
        "Tick every role they need. With no role, they can sign in but only see Home.",
    ),
    "is_superuser": (
        "Full access to everything",
        "They can do everything here, including changing other people with full access. "
        "Give this to as few people as possible.",
    ),
    "is_active": (
        "Can sign in",
        "Untick this to switch them off. They can't sign in until someone ticks it again. "
        "Their past work stays.",
    ),
    "password1": ("Starting password", None),
    "password2": (TYPE_IT_AGAIN, "Type the same password again, to check for typos."),
}

# Design G3: the details describe someone else, so the browser mustn't offer the viewer's own.
NO_AUTOFILL_FIELDS = ("first_name", "last_name", "username", "email")
TYPED_EXACTLY_FIELDS = ("username", "email")

STAFF_FIELDS = ("first_name", "last_name", "username", "email", "groups", "is_superuser")


def roles_queryset():
    """Every role, by name, with its permissions prefetched (criteria 7, 18 and 35, D3, D12).

    Roles are plain ``Group`` rows made by migrations, so a role a later brief adds appears
    here with no code change. The prefetch (with content types, which ``User.can_give_role``
    compares) lets the form and :func:`role_choices` read each role's permissions without a
    query per role.
    """
    return Group.objects.order_by("name").prefetch_related("permissions__content_type")


class RoleCheckboxes(forms.CheckboxSelectMultiple):
    """Role checkboxes where each role the actor can't give is rendered ``disabled``.

    Django can disable a whole field but not one option, and criterion 32 needs one: a role
    the actor can't give still shows its current state, but can't be changed. ``locked`` holds
    those roles' pks; the form sets it per instance. The disabled box is only what people see:
    browsers don't post disabled boxes, and ``clean_groups`` is what enforces the rule.
    """

    locked = frozenset()

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if getattr(value, "value", value) in self.locked:
            option["attrs"]["disabled"] = True
        return option


def role_choices(bound_field):
    """The ``roles`` context for the staff form: one entry per role checkbox, in form order.

    A template can't look up a dict by a variable, so rather than a ``role_help`` map keyed
    by pk (Design G1) the view hands over this list (D12). Each entry is
    ``{"choice": BoundWidget, "permissions": [names, sorted], "can_give": bool}``. The group
    comes from the choice's ``ModelChoiceIteratorValue.instance``, i.e. the prefetched row,
    and ``can_give`` from the answers the form already worked out with ``User.can_give_role``,
    so building the list costs no queries beyond the one prefetch (criterion 35).
    """
    givable = bound_field.form.givable_role_pks
    entries = []
    for choice in bound_field:
        group = choice.data["value"].instance
        entries.append(
            {
                "choice": choice,
                "permissions": sorted(permission.name for permission in group.permissions.all()),
                "can_give": group.pk in givable,
            }
        )
    return entries


class StaffDetailsMixin:
    """What the add and change forms share: D.6's copy, G3's widget attributes, the roles
    field, the full-access gate and one email per person.

    ``actor`` is the signed-in user doing the adding or changing. Without full access the
    ``is_superuser`` field is removed from the form, so it isn't rendered and a crafted POST
    value for it is never read (criteria 10 and 13).

    The roles the actor may give are worked out once, here, from the prefetched roles
    (``User.can_give_role``, criteria 31 and 35). The others are locked on the widget
    (criterion 32) and kept as they are by :meth:`clean_groups`.
    """

    #: True when the whole roles field is read-only: a non-superuser's own record
    #: (criterion 33). Only ``StaffChangeForm`` ever sets it.
    roles_read_only = False

    def set_up_staff_fields(self, actor):
        self.actor = actor
        if not User.can_grant_full_access(actor):
            self.fields.pop("is_superuser", None)

        for name, (label, help_text) in STAFF_FIELD_COPY.items():
            if name in self.fields:
                self.fields[name].label = label
                if help_text is not None:
                    self.fields[name].help_text = help_text

        email = self.fields["email"]
        email.required = True
        email.error_messages["required"] = EMAIL_REQUIRED

        groups = self.fields["groups"]
        groups.queryset = roles_queryset()
        groups.required = False
        # Evaluates the queryset once; the widget then renders from the same cached rows.
        roles = list(groups.queryset)
        self.givable_role_pks = frozenset(
            role.pk for role in roles if User.can_give_role(actor, role)
        )
        groups.widget.locked = frozenset(role.pk for role in roles) - self.givable_role_pks

        attrs = self.fields["username"].widget.attrs
        attrs.pop("autofocus", None)
        for name in NO_AUTOFILL_FIELDS:
            self.fields[name].widget.attrs["autocomplete"] = "off"
        for name in TYPED_EXACTLY_FIELDS:
            self.fields[name].widget.attrs.update(autocapitalize="none", spellcheck="false")

    def clean_email(self):
        """One address per person, whatever the letter case (criterion 9).

        Only checked here. Storing it trimmed and lower-cased is ``User.clean()``'s job, which
        the model form runs after this (review round 1, nit 4). ``EmailField`` already strips
        spaces, and ``iexact`` ignores letter case, so the check needs no normalising of its own.
        """
        email = self.cleaned_data.get("email")
        others = User.objects.filter(email__iexact=email)
        if self.instance.pk is not None:
            others = others.exclude(pk=self.instance.pk)
        if email and others.exists():
            raise forms.ValidationError(EMAIL_TAKEN, code="email_taken")
        return email

    def clean_groups(self):
        """The roles to save: only those the actor may give can change (criterion 32).

        - Roles the actor may give follow the POST.
        - Roles they may not give keep their stored state. Browsers don't post disabled
          boxes, so leaving one out never counts as removing it.
        - Posting a role they may not give, which the person doesn't already hold, can only
          be a crafted request (its box is disabled). It's refused with a field error, and
          nothing is saved.

        A disabled field (your own roles, criterion 33) already holds the stored value, from
        Django, so it's returned unchanged.
        """
        posted = self.cleaned_data.get("groups")
        if self.fields["groups"].disabled:
            return posted
        posted_pks = {group.pk for group in posted or ()}
        held_pks = (
            set(self.instance.groups.values_list("pk", flat=True))
            if self.instance.pk is not None
            else set()
        )
        givable = self.givable_role_pks
        if (posted_pks - held_pks) - givable:
            raise forms.ValidationError(ROLE_NOT_YOURS, code="role_not_yours")
        keep_pks = (posted_pks & givable) | (held_pks - givable)
        return [role for role in self.fields["groups"].queryset if role.pk in keep_pks]


class StaffCreateForm(StaffDetailsMixin, UserCreationForm):
    """Add a person, with a starting password the adder types (D9).

    ``UserCreationForm`` brings the case-insensitive username check, the two password
    fields, the validators and hashing. New people can sign in (``is_active`` defaults to
    true and isn't shown) and ``is_staff`` stays false: it means nothing now the admin is gone
    (D5).
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = STAFF_FIELDS
        field_classes = {"username": UsernameField}
        widgets = {"groups": RoleCheckboxes}

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_up_staff_fields(actor)


class StaffChangeForm(StaffDetailsMixin, forms.ModelForm):
    """Change someone's details, roles, full access and whether they can sign in.

    The guards (criterion 13) are rules on ``User``; ``clean()`` asks
    ``instance.access_change_error()`` and attaches each answer to its field. It runs before
    ``_post_clean()`` copies the typed values onto the instance, so the instance still holds
    what's stored, which is what the rules compare against.

    On your own record, unless you have full access, the roles field is disabled (Django's
    ``disabled=True``): every box shows its stored state and nothing posted for it counts
    (criterion 33). So nobody gives themselves a role, and nobody locks themselves out of
    Staff and access by unticking ``Staff managers``.
    """

    class Meta:
        model = User
        fields = (*STAFF_FIELDS, "is_active")
        field_classes = {"username": UsernameField}
        widgets = {"groups": RoleCheckboxes}

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_up_staff_fields(actor)
        is_self = actor is not None and actor.pk == self.instance.pk
        if is_self and not User.can_grant_full_access(actor):
            self.fields["groups"].disabled = True
            self.roles_read_only = True

    def clean_username(self):
        """Usernames are unique in any letter case, as on the add form (``UserCreationForm``)."""
        username = self.cleaned_data.get("username")
        taken = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if username and taken.exists():
            raise forms.ValidationError(
                self.instance.unique_error_message(User, ["username"]), code="unique"
            )
        return username

    def clean(self):
        cleaned_data = super().clean()
        stored = self.instance
        is_superuser = (
            cleaned_data.get("is_superuser", stored.is_superuser)
            if "is_superuser" in self.fields
            else stored.is_superuser
        )
        errors = stored.access_change_error(
            actor=self.actor,
            is_active=cleaned_data.get("is_active", stored.is_active),
            is_superuser=is_superuser,
        )
        for field, message in errors.items():
            self.add_error(field, message)
        return cleaned_data


class StaffSetPasswordForm(SetPasswordForm):
    """Django's ``SetPasswordForm`` with D.6's wording; labels and help only (D7, G2)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password2"].label = TYPE_IT_AGAIN
        self.fields["new_password2"].help_text = NEW_PASSWORD_AGAIN_HELP


class OwnPasswordChangeForm(PasswordChangeForm):
    """Django's ``PasswordChangeForm`` with D.6's wording; labels and help only (D7, G2)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Your current password"
        self.fields["old_password"].help_text = "The one you use to sign in now."
        self.fields["new_password2"].label = TYPE_IT_AGAIN
        self.fields["new_password2"].help_text = NEW_PASSWORD_AGAIN_HELP
