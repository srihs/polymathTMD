"""Forms for Zoom link requests (brief 005) and Zoom host accounts (brief 008).

Labels, help and error copy come from the briefs' Design sections and pinned criteria, so the
form is their one source: the templates only print ``field.label`` and ``field.help_text``.
The rules are not repeated here. Both model forms are ``ModelForm``s, so the model's
``clean()`` runs on every submit and its errors land on the right fields.
"""

import re
from urllib.parse import urlsplit

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.forms.models import ModelChoiceIteratorValue
from django.views.decorators.debug import sensitive_variables

from .models import (
    CLASS_NAME_REQUIRED,
    LAST_DATE_NEEDED,
    REASON_REQUIRED,
    WEEKDAY_CHOICES,
    HostAccount,
    LinkRequest,
)
from .services import NOT_OFFERED
from .validators import HOST_KEY_ERROR, PHONE_ERROR, normalise_phone, validate_host_key

EMAIL_ERROR = (
    "Type an email address you can open now, like nimali@example.com. We'll send a link to it."
)
NAME_REQUIRED = "Type your full name."
DATE_REQUIRED = "Choose the date of the class."
START_REQUIRED = "Type the time the class starts, like 8:30 am."
END_REQUIRED = "Type the time the class ends, like 11:30 am."
JOIN_URL_REQUIRED = "Paste the Zoom link for this meeting."
JOIN_URL_INVALID = (
    "Paste the link Zoom gave you. It starts with https:// and ends in zoom.us before the "
    "first /, like https://us02web.zoom.us/j/12345678901."
)
MEETING_ID_INVALID = "Type the meeting ID from Zoom: 9 to 11 digits, like 123 4567 8901."
PASSCODE_TOO_LONG = "A Zoom passcode is at most 10 characters. Check you copied only the passcode."


class LinkRequestForm(forms.ModelForm):
    """The public request form.

    ``website`` is a honeypot: people never see it, so any value means a bot. The view treats
    such a submit as a success without storing anything (criterion 9). ``weekdays`` is shown
    as seven checkboxes and stored as the model's sorted ``"1,3"`` string.
    """

    weekdays = forms.MultipleChoiceField(
        label="Days of the week",
        help_text="Tick every day the class happens.",
        choices=WEEKDAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    # Wider than the stored E.164 value, so "(077) 123-4567"-style typing isn't cut short.
    requester_phone = forms.CharField(
        label="Your phone number",
        help_text="In case IT needs to call you about the times, like 077 123 4567.",
        max_length=40,
        error_messages={"required": PHONE_ERROR},
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel", "inputmode": "tel"}),
    )
    website = forms.CharField(
        label="Leave this empty",
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta:
        model = LinkRequest
        fields = [
            "class_name",
            "wants_recording",
            "notes",
            "first_date",
            "start_time",
            "end_time",
            "repeat",
            "weekdays",
            "last_date",
            "requester_name",
            "requester_email",
            "requester_phone",
        ]
        labels = {
            "class_name": "Class name",
            "wants_recording": "Record this class to the Zoom cloud",
            "notes": "Anything IT should know (optional)",
            "first_date": "Date of the class",
            "start_time": "Starts at",
            "end_time": "Ends at",
            "repeat": "How often is the class?",
            "last_date": "Date of the last class",
            "requester_name": "Your full name",
            "requester_email": "Your email address",
        }
        help_texts = {
            "class_name": "The name students and IT will see, like CCC Batch 3 - Mathematics.",
            "wants_recording": "Tick this if you need a recording. IT turns recording on in Zoom.",
            "notes": "For example, a co-host who needs to join early. Up to 1000 characters.",
            "first_date": "For a weekly class, choose the date of the first class.",
            "start_time": "Sri Lanka time, on a 5-minute step, like 8:30 am.",
            "end_time": "On the same day as it starts.",
            "repeat": 'Choose "Every week" if the class is on the same days at the same time '
            "each week.",
            "last_date": "We'll book every ticked day up to and including this date. One "
            f"request can cover up to {LinkRequest.MAX_OCCURRENCES} classes.",
            "requester_name": "So IT knows who the link is for.",
            "requester_email": "We'll send a link here to check it's yours. IT will send the "
            "Zoom link here too.",
        }
        error_messages = {
            "class_name": {"required": CLASS_NAME_REQUIRED},
            "first_date": {"required": DATE_REQUIRED, "invalid": DATE_REQUIRED},
            "start_time": {"required": START_REQUIRED, "invalid": START_REQUIRED},
            "end_time": {"required": END_REQUIRED, "invalid": END_REQUIRED},
            "last_date": {"invalid": LAST_DATE_NEEDED},
            "requester_name": {"required": NAME_REQUIRED},
            "requester_email": {"required": EMAIL_ERROR, "invalid": EMAIL_ERROR},
        }
        widgets = {
            "class_name": forms.TextInput(attrs={"autocomplete": "off"}),
            "wants_recording": forms.CheckboxInput,
            "notes": forms.Textarea(attrs={"rows": 4}),
            "first_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "step": 300}),
            "end_time": forms.TimeInput(attrs={"type": "time", "step": 300}),
            "repeat": forms.RadioSelect(attrs={"data-repeat": ""}),
            "last_date": forms.DateInput(attrs={"type": "date"}),
            "requester_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "requester_email": forms.EmailInput(
                attrs={"autocomplete": "email", "spellcheck": "false", "autocapitalize": "none"}
            ),
        }

    def clean_weekdays(self):
        return ",".join(sorted(self.cleaned_data["weekdays"], key=int))

    def clean_requester_email(self):
        return self.cleaned_data["requester_email"].strip().lower()

    def clean_requester_phone(self):
        return normalise_phone(self.cleaned_data["requester_phone"])

    @property
    def is_honeypot_hit(self) -> bool:
        return bool(self.cleaned_data.get("website", "").strip())


class ApproveForm(forms.Form):
    """Pick the account; with the manual provider, also paste the meeting details.

    ``host_account`` offers only the free accounts but accepts any bookable one. The radios list
    only accounts free for every class (criterion 30, see ``offer()``), while validation uses
    ``HostAccount.objects.bookable()``, so a pick that turned busy since the page loaded reaches
    the service's locked re-check and gets the specific "booked a moment ago" answer (criterion
    37). Unpaid, inactive or unknown accounts fail here with ``Choose one of the free accounts
    listed.``
    """

    host_account = forms.ModelChoiceField(
        label="Book it on",
        help_text="Only accounts free for every class are listed.",
        queryset=HostAccount.objects.none(),
        empty_label=None,
        widget=forms.RadioSelect,
        error_messages={"required": NOT_OFFERED, "invalid_choice": NOT_OFFERED},
    )

    def __init__(self, *args, free_accounts=(), needs_manual_details=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["host_account"].queryset = HostAccount.objects.bookable()
        self.offer(free_accounts)
        if needs_manual_details:
            self.fields["join_url"] = forms.CharField(
                label="Zoom link",
                help_text="Copy the invite link from the meeting in Zoom. It starts with "
                "https:// and has zoom.us in it.",
                max_length=1000,
                error_messages={"required": JOIN_URL_REQUIRED, "max_length": JOIN_URL_INVALID},
                widget=forms.URLInput(
                    attrs={"inputmode": "url", "spellcheck": "false", "autocomplete": "off"}
                ),
            )
            self.fields["meeting_id"] = forms.CharField(
                label="Meeting ID",
                help_text="The 9 to 11 digit number from Zoom. Spaces are fine.",
                max_length=40,
                error_messages={"required": MEETING_ID_INVALID, "max_length": MEETING_ID_INVALID},
                widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
            )
            self.fields["passcode"] = forms.CharField(
                label="Passcode",
                help_text="Leave this empty if the meeting has no passcode.",
                max_length=10,
                required=False,
                error_messages={"max_length": PASSCODE_TOO_LONG},
                widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            )

    def offer(self, free_accounts):
        """Show ``free_accounts`` as the radios, the first one pre-selected (criterion 30).

        Called again after a failed approve with the refreshed list, so the radios always
        match the availability shown on the same page. Each choice value carries the account
        (``choice.data.value.instance``), so the template can show its email and host-key word.
        """
        field = self.fields["host_account"]
        self.free_accounts = list(free_accounts)
        field.widget.choices = [
            (ModelChoiceIteratorValue(account.pk, account), field.label_from_instance(account))
            for account in self.free_accounts
        ]
        if self.free_accounts and not self.is_bound:
            self.initial.setdefault("host_account", self.free_accounts[0].pk)

    def clean_join_url(self):
        r"""An https link on zoom.us or a subdomain of it, and nothing that could fool the check.

        A backslash is refused outright: browsers treat ``\`` like ``/``, so
        ``https://evil.example\.zoom.us/…`` would pass a host-suffix test yet open evil.example.
        ``URLValidator`` then rejects anything else that isn't a well-formed https URL.
        """
        value = self.cleaned_data["join_url"].strip()
        if "\\" in value:
            raise ValidationError(JOIN_URL_INVALID)
        try:
            URLValidator(schemes=["https"])(value)
            parts = urlsplit(value)
            host = (parts.hostname or "").lower()
        except (ValidationError, ValueError):
            raise ValidationError(JOIN_URL_INVALID) from None
        if parts.scheme != "https" or not (host == "zoom.us" or host.endswith(".zoom.us")):
            raise ValidationError(JOIN_URL_INVALID)
        return value

    def clean_meeting_id(self):
        digits = self.cleaned_data["meeting_id"].replace(" ", "")
        if not re.fullmatch(r"[0-9]{9,11}", digits):
            raise ValidationError(MEETING_ID_INVALID)
        return digits

    def manual_details(self):
        """The typed meeting details for ``ManualProvider``, or None when not asked for."""
        if "join_url" not in self.fields:
            return None
        return {
            "join_url": self.cleaned_data["join_url"],
            "meeting_id": self.cleaned_data["meeting_id"],
            "passcode": self.cleaned_data.get("passcode", ""),
        }


class RejectForm(forms.Form):
    reason = forms.CharField(
        label="Why can't it go ahead?",
        help_text="The requester sees this in their email. Say what they can do instead, like "
        '"Please use the Grade 10 batch link instead."',
        max_length=1000,
        error_messages={"required": REASON_REQUIRED},
        widget=forms.Textarea(attrs={"rows": 4}),
    )


# --------------------------------------------------------------------------- Zoom accounts

ACCOUNT_LABEL_REQUIRED = "Type a short name for the account, like Zoom 01."
ACCOUNT_LABEL_TAKEN = "Another Zoom account already has this name. Choose a different one."
ACCOUNT_EMAIL_INVALID = (
    "Type the email address this Zoom account signs in with, like zoom01@polymath.edu.lk."
)
ACCOUNT_EMAIL_TAKEN = "Another Zoom account already signs in with this email address."
KEY_AND_REMOVE = "Type a new host key or tick Remove, not both."
KEY_NOT_KEPT = "For your safety, the host key you typed wasn't kept. Type it again."

HOST_KEY_HELP_ADD = (
    "Optional. The 6 to 10 digits from the Profile page of this account in Zoom. You can add "
    "it later."
)
HOST_KEY_HELP_KEEP = "Leave it empty to keep the saved key."
HOST_KEY_HELP_NONE = "Type the 6 to 10 digits from the account's Zoom profile."


class HostAccountForm(forms.ModelForm):
    """Add or change a Zoom host account; one class for both, so the key rules live once (D6).

    The host key is write-only (D7):

    - ``host_key`` is form-only and never has an initial value, so a saved key is never sent
      to the browser.
    - After an invalid submit, the typed key is dropped from the bound data, so the re-render
      can't echo it into the HTML (browser cache, "view source", screenshots).
      ``key_was_typed`` tells the page to say why the box is empty.
    - Every method that holds the typed key in a local is ``@sensitive_variables``, so an
      error report masks it (brief 005, review round 2, nit 2).

    ``clean()`` also asks the account whether the ``In use`` or ``Paid`` tick may be removed
    (``stop_booking_errors``, brief 008, criterion 17). The view has locked the account row
    before the form is validated, and ``construct_instance`` only runs after ``clean()``, so
    ``self.instance`` still holds the stored values here, label included.
    """

    host_key = forms.CharField(
        label="Host key",
        help_text=HOST_KEY_HELP_ADD,
        required=False,
        max_length=10,
        error_messages={"max_length": HOST_KEY_ERROR},
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "inputmode": "numeric", "spellcheck": "false"}
        ),
    )
    remove_host_key = forms.BooleanField(
        label="Remove the saved host key",
        help_text="Tick this if the saved key is wrong and you don't have the new one yet. "
        "Approval emails will then tell the requester to ask the IT desk for the host key.",
        required=False,
    )

    # The on-screen order, which the error summary and the tab order follow (Design, G1).
    field_order = [
        "label",
        "email",
        "notes",
        "is_paid",
        "is_active",
        "sort_order",
        "host_key",
        "remove_host_key",
    ]

    class Meta:
        model = HostAccount
        # credential_set stays off this form until brief 006 needs it (D5).
        fields = ["label", "email", "notes", "is_paid", "is_active", "sort_order"]
        labels = {
            "label": "Name",
            "email": "Zoom sign-in email",
            "notes": "Notes",
            "is_paid": "Paid account",
            "is_active": "In use",
            "sort_order": "Order",
        }
        help_texts = {
            "label": "A short name IT uses for this account, like Zoom 01.",
            "email": "The email address this account signs in to Zoom with.",
            "notes": "Optional. Anything IT should remember, like who pays for it or when it "
            "renews.",
            "is_paid": "Free Zoom accounts end meetings after 40 minutes, so only paid accounts "
            "can be booked.",
            "is_active": "Untick it to stop new bookings on this account. Nothing is deleted, and "
            "you can tick it again later.",
            "sort_order": "Lower numbers are suggested first when several accounts are free.",
        }
        error_messages = {
            "label": {"required": ACCOUNT_LABEL_REQUIRED, "unique": ACCOUNT_LABEL_TAKEN},
            "email": {
                "required": ACCOUNT_EMAIL_INVALID,
                "invalid": ACCOUNT_EMAIL_INVALID,
                "unique": ACCOUNT_EMAIL_TAKEN,
            },
        }
        widgets = {
            "label": forms.TextInput(attrs={"autocomplete": "off"}),
            # "off", or browsers offer the signed-in IT person's own address (Design, G5).
            "email": forms.EmailInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "sort_order": forms.NumberInput(
                attrs={"min": "0", "step": "1", "inputmode": "numeric"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.key_was_typed = False
        self.key_changed = False
        self.key_removed = False
        host_key = self.fields["host_key"]
        if self.instance.pk is not None:
            host_key.label = "New host key"
            host_key.help_text = (
                HOST_KEY_HELP_KEEP if self.instance.has_host_key else HOST_KEY_HELP_NONE
            )
        if not self.instance.has_host_key:
            del self.fields["remove_host_key"]

    @sensitive_variables("typed", "data")
    def full_clean(self):
        """Validate, then forget a typed key if the form is going to be shown again (D7)."""
        super().full_clean()
        if not self.is_bound or not self._errors:
            return
        name = self.add_prefix("host_key")
        typed = self.data.get(name, "")
        self.key_was_typed = bool(typed.strip())
        if name in self.data:
            data = self.data.copy()
            data.pop(name)
            self.data = data

    @sensitive_variables("value")
    def clean_host_key(self):
        value = self.cleaned_data["host_key"].strip()
        if value:
            validate_host_key(value)
        return value

    # cleaned_data holds the typed key too, so it's masked along with it.
    @sensitive_variables("cleaned_data")
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("host_key") and cleaned_data.get("remove_host_key"):
            self.add_error("host_key", KEY_AND_REMOVE)
        if self.instance.pk is not None:
            errors = self.instance.stop_booking_errors(
                is_active=cleaned_data.get("is_active", self.instance.is_active),
                is_paid=cleaned_data.get("is_paid", self.instance.is_paid),
            )
            for field, message in errors.items():
                self.add_error(field, message)
        return cleaned_data

    @sensitive_variables("key")
    def save(self, commit=True):
        """Save the account; store, replace or remove the key through ``set_host_key``.

        ``key_changed`` / ``key_removed`` tell the view which success message to show.
        """
        account = super().save(commit=False)
        key = self.cleaned_data.get("host_key", "")
        if key:
            account.set_host_key(key, by=self.user)
            self.key_changed = True
        elif self.cleaned_data.get("remove_host_key"):
            account.set_host_key("", by=self.user)
            self.key_removed = True
        if commit:
            account.save()
            self._save_m2m()
        return account
