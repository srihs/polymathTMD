"""Forms for Zoom link requests (brief 005), Zoom host accounts (briefs 008 and 006),
cancelling a booking (brief 011), moving classes (brief 012) and Zoom connections (brief 015).

Labels, help and error copy come from the briefs' Design sections and pinned criteria, so the
form is their one source: the templates only print ``field.label`` and ``field.help_text``.
The rules are not repeated here. Both model forms are ``ModelForm``s, so the model's
``clean()`` runs on every submit and its errors land on the right fields.
"""

import re
from datetime import datetime, timedelta

from django import forms
from django.core import signing
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.forms.models import ModelChoiceIteratorValue
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import (
    CANCEL_REASON_REQUIRED,
    CLASS_NAME_REQUIRED,
    LAST_DATE_NEEDED,
    REASON_REQUIRED,
    WEEKDAY_CHOICES,
    HostAccount,
    LinkRequest,
    ZoomConnection,
)
from .services import MOVE_PAGE_OUT_OF_DATE, NOT_OFFERED, read_move_shown
from .validators import (
    CREDENTIAL_SET_ERROR,
    HOST_KEY_ERROR,
    PHONE_ERROR,
    is_zoom_https_url,
    normalise_phone,
    validate_credential_set,
    validate_host_key,
    validate_zoom_value,
)

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
            # ``format``: an ``<input type=time>`` only takes ``HH:MM``; Django's default
            # (``TIME_INPUT_FORMATS[0]``) would print ``08:30:00`` for a pre-filled value
            # (brief 012, criterion 28). The move forms copy these widgets.
            "start_time": forms.TimeInput(attrs={"type": "time", "step": 300}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time", "step": 300}, format="%H:%M"),
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
    only accounts free for every class (criterion 30, see ``offer()``); since brief 011 they
    say nothing about host keys, which are no longer emailed. Validation uses
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
        (``choice.data.value.instance``), so the template can show its email.
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
        """An https link on zoom.us or a subdomain of it, and nothing that could fool the check.

        The rule is ``validators.is_zoom_https_url``, shared with the start page's redirect
        (brief 011), so the two can't drift apart.
        """
        value = self.cleaned_data["join_url"].strip()
        if not is_zoom_https_url(value):
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


# The one place the cancel reason's limit is set: the server check, the browser's
# ``maxlength`` and the error message all read it (review round 1 nit).
CANCEL_REASON_MAX_LENGTH = 1000
CANCEL_REASON_TOO_LONG = f"Keep the reason to {CANCEL_REASON_MAX_LENGTH} characters or fewer."


class CancelForm(forms.Form):
    """The one field of the cancel confirm page, for a whole booking or one class (brief 011).

    The label, help, error and widget are all set here (criterion 7, G7), so
    ``partials/field.html`` renders the textarea unchanged: ``rows="4"``, and a ``maxlength``
    so the browser stops at the limit the server also checks. Django's ``CharField`` writes
    that ``maxlength`` from ``max_length`` itself, so it isn't repeated in the widget. The
    typed reason is kept on every re-render because the bound form is passed back as it is.
    """

    reason = forms.CharField(
        label="Why is it cancelled?",
        help_text="This goes in the email to the requester.",
        max_length=CANCEL_REASON_MAX_LENGTH,
        error_messages={"required": CANCEL_REASON_REQUIRED, "max_length": CANCEL_REASON_TOO_LONG},
        widget=forms.Textarea(attrs={"rows": "4"}),
    )


# --------------------------------------------------------------------------- Moving (012)

MOVE_DATE_HELP = (
    "Any date within the next year. It doesn't have to be one of the booking's usual days."
)


def _request_form_time_field(name):
    """``start_time`` or ``end_time`` exactly as the request form has it (criterion 5).

    The label, help, "required" message and widget (``type=time``, ``step=300``) are read from
    ``LinkRequestForm.Meta``, their one definition, so the move forms can't drift from it.
    The widget is copied by the field, so the request form's own is never changed.
    """
    meta = LinkRequestForm.Meta
    return forms.TimeField(
        label=meta.labels[name],
        help_text=meta.help_texts[name],
        error_messages=meta.error_messages[name],
        widget=meta.widgets[name],
    )


class _MoveFormMixin(forms.Form):
    """What both move forms share: the signed ``shown`` field and the rules' errors.

    ``shown`` (criterion 30) carries the classes as the page showed them, signed by
    ``LinkRequest.move_fingerprint``. The view sets it on every render with ``set_shown``, so
    a re-render after a refusal acts on the times now on screen. ``clean()`` reads it back
    with ``services.read_move_shown`` into ``cleaned_data["shown"]``; a missing or unreadable
    value becomes a **non-field** error (the error summary would otherwise link to a hidden
    input) and sets ``out_of_date``, which the view answers with a 400.
    """

    shown = forms.CharField(widget=forms.HiddenInput, required=False)

    out_of_date = False

    def set_shown(self, value):
        """Put a fresh ``shown`` on the form, bound or not, for the page about to be drawn."""
        if self.is_bound:
            self.data = self.data.copy()
            self.data[self.add_prefix("shown")] = value
        else:
            self.initial["shown"] = value

    def clean(self):
        cleaned_data = super().clean()
        try:
            cleaned_data["shown"] = read_move_shown(cleaned_data.get("shown"))
        except signing.BadSignature:
            cleaned_data["shown"] = None
            self.out_of_date = True
            self.add_error(None, MOVE_PAGE_OUT_OF_DATE)
        return cleaned_data

    def add_rule_errors(self, errors):
        for name, message in errors.items():
            self.add_error(None if name == NON_FIELD_ERRORS else name, message)


class MoveClassForm(_MoveFormMixin):
    """Move one class: a new date, start and end (brief 012, criterion 5).

    ``clean()`` asks the class itself (``Occurrence.move_errors``), so the form and
    ``services.move_class()`` apply the same rules. G2: the date widget's ``min`` (today) and
    ``max`` (the last date 005's ``DATE_TOO_FAR`` allows) are set here, so
    ``partials/field.html`` prints them with nothing passed in. The initial values are the
    class's current date and times, in Colombo time.
    """

    date = forms.DateField(
        label="Date of the class",
        help_text=MOVE_DATE_HELP,
        error_messages={"required": DATE_REQUIRED, "invalid": DATE_REQUIRED},
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    start_time = _request_form_time_field("start_time")
    end_time = _request_form_time_field("end_time")

    def __init__(self, *args, occurrence, **kwargs):
        self.occurrence = occurrence
        start = timezone.localtime(occurrence.starts_at)
        end = timezone.localtime(occurrence.ends_at)
        # ``FormView`` always passes ``initial`` (an empty dict), so the current values are the
        # base and anything the caller passed goes on top.
        current = {"date": start.date(), "start_time": start.time(), "end_time": end.time()}
        kwargs["initial"] = {**current, **(kwargs.get("initial") or {})}
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        latest = today + timedelta(days=LinkRequest.MAX_DAYS_AHEAD)
        self.fields["date"].widget.attrs.update(min=today.isoformat(), max=latest.isoformat())

    def clean(self):
        cleaned_data = super().clean()
        day = cleaned_data.get("date")
        start, end = cleaned_data.get("start_time"), cleaned_data.get("end_time")
        if day is None or start is None or end is None:
            return cleaned_data
        zone = timezone.get_default_timezone()
        cleaned_data["starts_at"] = datetime.combine(day, start, tzinfo=zone)
        cleaned_data["ends_at"] = datetime.combine(day, end, tzinfo=zone)
        self.add_rule_errors(
            self.occurrence.move_errors(
                starts_at=cleaned_data["starts_at"], ends_at=cleaned_data["ends_at"]
            )
        )
        return cleaned_data


class MoveSeriesForm(_MoveFormMixin):
    """A new time of day for every remaining class (brief 012, criterion 5; D10: time only).

    ``clean()`` asks the booking (``LinkRequest.series_move_errors``). The initial values are
    the booking's current times, which a series move keeps up to date (D4).
    """

    start_time = _request_form_time_field("start_time")
    end_time = _request_form_time_field("end_time")

    def __init__(self, *args, link_request, occurrences=None, **kwargs):
        self.link_request = link_request
        self.occurrences = occurrences
        current = {"start_time": link_request.start_time, "end_time": link_request.end_time}
        kwargs["initial"] = {**current, **(kwargs.get("initial") or {})}
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get("start_time"), cleaned_data.get("end_time")
        if start is None or end is None:
            return cleaned_data
        self.add_rule_errors(
            self.link_request.series_move_errors(
                start_time=start, end_time=end, occurrences=self.occurrences
            )
        )
        return cleaned_data


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
# Brief 011, criterion 30 (D11): keys aren't emailed any more. The change page's key field
# carries this after its own instruction, so the page says it once (P6).
HOST_KEYS_NOT_EMAILED = (
    "Host keys aren't emailed. Teachers start classes with the start link in their approval "
    "email. If that link fails, the IT desk can show the key on this page."
)
HOST_KEY_HELP_KEEP = f"Leave it empty to keep the saved key. {HOST_KEYS_NOT_EMAILED}"
HOST_KEY_HELP_NONE = (
    f"Type the 6 to 10 digits from the account's Zoom profile. {HOST_KEYS_NOT_EMAILED}"
)
# The model field owns this copy; the form field is declared by hand (see the class docstring)
# and borrows it rather than keeping a second copy (review round 1, SF3; brief 015, c. 18).
ZOOM_CONNECTION_HELP = HostAccount._meta.get_field("zoom_connection").help_text
ZOOM_CONNECTION_EMPTY = "No Zoom connection yet"
ZOOM_CONNECTION_CHOICE = "Choose a Zoom connection from the list."


class HostAccountForm(forms.ModelForm):
    """Add or change a Zoom host account; one class for both, so the key rules live once (D6).

    The typed host key is never sent back to the browser (D7). Since brief 011 a saved key can
    be shown to the IT desk on its own page, never here:

    - ``host_key`` is form-only and never has an initial value, so a saved key is never sent
      to the browser.
    - After an invalid submit, the typed key is dropped from the bound data, so the re-render
      can't echo it into the HTML (browser cache, "view source", screenshots).
      ``key_was_typed`` tells the page to say why the box is empty.
    - Every method that holds the typed key in a local is ``@sensitive_variables``, so an
      error report masks it (brief 005, review round 2, nit 2).

    ``zoom_connection`` (brief 015, criterion 18, replacing 006's typed name) picks one of the
    saved Zoom connections. Its choices load only ``pk`` and ``slug``, so no secret column is
    ever selected to build the list. It's declared here, not generated, for its pinned label,
    empty label, help and error.

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
    zoom_connection = forms.ModelChoiceField(
        queryset=ZoomConnection.objects.only("pk", "slug"),
        label="Zoom connection",
        help_text=ZOOM_CONNECTION_HELP,
        required=False,
        empty_label=ZOOM_CONNECTION_EMPTY,
        error_messages={"invalid_choice": ZOOM_CONNECTION_CHOICE},
    )
    remove_host_key = forms.BooleanField(
        label="Remove the saved host key",
        help_text="Tick this if the saved key is wrong and you don't have the new one yet.",
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
        "zoom_connection",
        "host_key",
        "remove_host_key",
    ]

    class Meta:
        model = HostAccount
        fields = [
            "label",
            "email",
            "notes",
            "is_paid",
            "is_active",
            "sort_order",
            "zoom_connection",
        ]
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


# --------------------------------------------------------------------------- Zoom connections

CONNECTION_NAME_REQUIRED = "Type a name for this connection, like zoom-01."
CONNECTION_NAME_TAKEN = "Another Zoom connection already has this name. Choose a different one."
ACCOUNT_ID_ERROR = (
    "Paste the Account ID from the App Credentials page of the Zoom app. It has no spaces."
)
CLIENT_ID_ERROR = (
    "Paste the Client ID from the App Credentials page of the Zoom app. It has no spaces."
)
CLIENT_ID_TAKEN = (
    "The Zoom connection {slug} already uses this Client ID. Each Zoom app needs only one "
    "connection."
)
CLIENT_SECRET_ERROR = (
    "Paste the Client Secret from the App Credentials page of the Zoom app. It has no spaces."
)
WEBHOOK_SECRET_ERROR = (
    "Paste the Secret Token from the Event Subscriptions part of the Zoom app. It has no spaces."
)
WEBHOOK_SECRET_AND_REMOVE = "Type a new webhook secret or tick Remove, not both."
# Criterion 13: the limits are the server's, never a ``maxlength`` the browser cuts to (G2).
ZOOM_ID_MAX_LENGTH = 100
ZOOM_SECRET_MAX_LENGTH = 200

# Criterion 11's table (D20 G1): labels and help by page and stored state. The name and ID
# help is defined once, on the model fields, and only borrowed here (D21 SF3), so the copy the
# page shows can't drift from the model's.
_CONNECTION_FIELD = ZoomConnection._meta.get_field
CONNECTION_NAME_HELP = _CONNECTION_FIELD("slug").help_text
ACCOUNT_ID_HELP = _CONNECTION_FIELD("account_id").help_text
CLIENT_ID_HELP = _CONNECTION_FIELD("client_id").help_text
CLIENT_SECRET_HELP_ADD = (
    "Copy the Client Secret from App Credentials and paste it here. For safety, it's never "
    "shown again once saved."
)
CLIENT_SECRET_HELP = {
    "saved": "Leave it empty to keep the saved one. If the Client Secret was regenerated in "
    "Zoom, paste the new one here.",
    "unreadable": "Paste the Client Secret from App Credentials. The saved one can't be used.",
}
WEBHOOK_SECRET_HELP_ADD = (
    "Optional. The Secret Token from the Event Subscriptions part of the Zoom app. You can add "
    "it later, on this connection's page, which also shows the address Zoom needs."
)
WEBHOOK_SECRET_HELP = {
    "none": "Paste the Secret Token from the Event Subscriptions part of the Zoom app, and "
    "save. Then press Validate in Zoom.",
    "saved": "Leave it empty to keep the saved one. If the Secret Token was regenerated in "
    "Zoom, paste the new one here.",
    "unreadable": "Paste the Secret Token from the Event Subscriptions part of the Zoom app. "
    "The saved one can't be used.",
}
REMOVE_WEBHOOK_SECRET_HELP = (
    "Tick this if the saved secret is wrong and you don't have the new one yet. Changes made in "
    "Zoom then stop being seen here."
)

# A pasted value isn't a word to correct, capitalise, spell-check or autofill. Spell-check
# services must never receive a secret, and "off" keeps it out of form history (D20 G2).
PASTE_ATTRS = {
    "autocomplete": "off",
    "autocapitalize": "none",
    "autocorrect": "off",
    "spellcheck": "false",
}


def _pasted_field(label, required_message, *, required=True):
    """A plain text box for a pasted Zoom value: ``TextInput``, no ``maxlength`` (G2).

    Not ``PasswordInput``: IT must see what they pasted to spot a wrong paste, and a password
    box would bring in the browser's password manager (owner's answer to O1, D20). The length
    limit is checked in the form's ``clean_*`` instead of the browser, so an over-long paste
    is refused, never silently cut short.
    """
    return forms.CharField(
        label=label,
        required=required,
        error_messages={"required": required_message},
        widget=forms.TextInput(attrs=dict(PASTE_ATTRS)),
    )


class ZoomConnectionForm(forms.ModelForm):
    """Add or change a Zoom connection; one class for both, like ``HostAccountForm`` (008 D6).

    Why it's shaped like this (brief 015):

    - **Only the name is a model field**, and only on the add page: it can't be changed once
      saved (D2), so the change form has no ``slug`` field and a posted one changes nothing.
      The Account ID, Client ID and both secrets are form-only and reach the row through
      ``ZoomConnection.set_credentials`` / ``set_webhook_secret`` / ``remove_webhook_secret``,
      so the version bump and the change records stay the model's rules (criterion 2), and
      ``construct_instance`` can never put a typed ID on the row before they compare it.
    - **The secrets are write-only** (D7, 008's host-key rules): the boxes never have an
      initial value, a typed secret is dropped from the bound data after an invalid submit
      (``full_clean``), so the re-render can't echo it, and ``client_secret_was_typed`` /
      ``webhook_secret_was_typed`` tell the page to say why the box is empty (criterion 14).
      Every method holding a typed secret is ``@sensitive_variables``.
    - **Labels and help come from here**, set in ``__init__`` per page and stored state
      (criterion 11, D20 G1), so the template prints them and decides nothing.
    - **An unreadable client secret must be retyped** (D20 P3): an empty New client secret is
      refused then, or someone who fixes only an ID would be told "Saved" while the connection
      still can't be used. The box is ``required`` exactly when it must be filled in (add, or
      change with an unreadable secret; D21 SF2), so the browser and screen readers say so and
      the empty-value error is the field's own ``required`` message, with the pinned text.
    """

    slug = forms.CharField(
        label="Connection name",
        help_text=CONNECTION_NAME_HELP,
        max_length=40,
        validators=[validate_credential_set],
        error_messages={
            "required": CONNECTION_NAME_REQUIRED,
            "max_length": CREDENTIAL_SET_ERROR,
            "invalid": CREDENTIAL_SET_ERROR,
            "unique": CONNECTION_NAME_TAKEN,
        },
        # Typed by hand, so a cut at 40 is visible as it happens; it keeps its maxlength (G2).
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "autocapitalize": "none", "spellcheck": "false"}
        ),
    )
    account_id = _pasted_field("Account ID", ACCOUNT_ID_ERROR)
    client_id = _pasted_field("Client ID", CLIENT_ID_ERROR)
    client_secret = _pasted_field("Client secret", CLIENT_SECRET_ERROR, required=False)
    webhook_secret = _pasted_field("Webhook secret", WEBHOOK_SECRET_ERROR, required=False)
    remove_webhook_secret = forms.BooleanField(
        label="Remove the saved webhook secret",
        help_text=REMOVE_WEBHOOK_SECRET_HELP,
        required=False,
    )

    # The on-screen order, which the error summary and the tab order follow (criterion 11).
    field_order = [
        "slug",
        "account_id",
        "client_id",
        "client_secret",
        "webhook_secret",
        "remove_webhook_secret",
    ]
    SECRET_FIELDS = ("client_secret", "webhook_secret")

    class Meta:
        model = ZoomConnection
        fields = ["slug"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.client_secret_was_typed = False
        self.webhook_secret_was_typed = False
        self.is_add = self.instance.pk is None
        self.credentials_state = None if self.is_add else self.instance.credentials_state
        fields = self.fields
        fields["account_id"].help_text = ACCOUNT_ID_HELP
        fields["client_id"].help_text = CLIENT_ID_HELP
        fields["client_secret"].required = self.is_add or self.credentials_state == "unreadable"
        if self.is_add:
            fields["client_secret"].help_text = CLIENT_SECRET_HELP_ADD
            fields["webhook_secret"].help_text = WEBHOOK_SECRET_HELP_ADD
            del fields["remove_webhook_secret"]
            return
        # The change page: the name is shown, not edited (D2); the IDs are prefilled (D3).
        del fields["slug"]
        webhook_state = self.instance.webhook_secret_state
        fields["account_id"].initial = self.instance.account_id
        fields["client_id"].initial = self.instance.client_id
        fields["client_secret"].label = "New client secret"
        fields["client_secret"].help_text = CLIENT_SECRET_HELP[self.credentials_state]
        fields["webhook_secret"].label = "New webhook secret"
        fields["webhook_secret"].help_text = WEBHOOK_SECRET_HELP[webhook_state]
        # Offered whenever a secret is stored, readable or not (D20 G3, as remove_host_key).
        if not self.instance.webhook_secret_encrypted:
            del fields["remove_webhook_secret"]

    def full_clean(self):
        """Validate, then forget typed secrets if the form is going to be shown again (D7)."""
        super().full_clean()
        if self.is_bound and self._errors:
            self._forget_typed_secrets()

    @sensitive_variables("typed", "data")
    def _forget_typed_secrets(self):
        """Drop both typed secrets from the bound data, noting which were typed (c. 14).

        Shared by ``full_clean`` and ``add_taken_errors``: any page shown again after a
        submit must neither echo a secret nor forget to say why its box is empty.
        """
        data = None
        for name in self.SECRET_FIELDS:
            key = self.add_prefix(name)
            typed = self.data.get(key, "")
            setattr(self, f"{name}_was_typed", bool(typed.strip()))
            if key in self.data:
                if data is None:
                    data = self.data.copy()
                data.pop(key)
        if data is not None:
            self.data = data

    def clean_account_id(self):
        return validate_zoom_value(
            self.cleaned_data["account_id"], max_length=ZOOM_ID_MAX_LENGTH, message=ACCOUNT_ID_ERROR
        )

    def clean_client_id(self):
        value = validate_zoom_value(
            self.cleaned_data["client_id"], max_length=ZOOM_ID_MAX_LENGTH, message=CLIENT_ID_ERROR
        )
        other = self.instance.client_id_taken_by(value)
        if other:
            raise ValidationError(CLIENT_ID_TAKEN.format(slug=other), code="unique")
        return value

    @sensitive_variables("value")
    def clean_client_secret(self):
        """Check a typed client secret; an empty one is the ``required`` rule's (SF2, P3)."""
        value = (self.cleaned_data.get("client_secret") or "").strip()
        if not value:
            return ""
        return validate_zoom_value(
            value, max_length=ZOOM_SECRET_MAX_LENGTH, message=CLIENT_SECRET_ERROR
        )

    @sensitive_variables("value")
    def clean_webhook_secret(self):
        value = (self.cleaned_data.get("webhook_secret") or "").strip()
        if not value:
            return ""
        return validate_zoom_value(
            value, max_length=ZOOM_SECRET_MAX_LENGTH, message=WEBHOOK_SECRET_ERROR
        )

    # cleaned_data holds the typed secrets too, so it's masked along with them.
    @sensitive_variables("cleaned_data")
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("webhook_secret") and cleaned_data.get("remove_webhook_secret"):
            self.add_error("webhook_secret", WEBHOOK_SECRET_AND_REMOVE)
        return cleaned_data

    # cleaned_data holds the typed secrets too, so it's masked along with them.
    @sensitive_variables("cleaned_data")
    def add_taken_errors(self) -> bool:
        """After a unique-constraint ``IntegrityError`` on save, say which value lost (c. 51).

        The checks in ``clean_client_id`` and ``validate_unique`` run before the save, so two
        people saving the same Client ID, or adding the same name, at the same moment can both
        pass them, and the second save then hits the database's unique constraint. The caller
        has rolled that save back to its savepoint; this asks the database again, with the same
        lookups the checks use, and puts each pinned "taken" error on its field (both, when
        both collided). The database's own error text is never read: it would name the values.

        Returns ``False`` when neither value is taken, so the caller re-raises: that error
        wasn't this race, and swallowing it would hide a real fault.
        """
        cleaned_data = self.cleaned_data
        errors = {}
        if "slug" in self.fields:
            slug = cleaned_data.get("slug")
            others = ZoomConnection.objects.filter(slug=slug).exclude(pk=self.instance.pk)
            if slug and others.exists():
                errors["slug"] = CONNECTION_NAME_TAKEN
        other = self.instance.client_id_taken_by(cleaned_data.get("client_id"))
        if other:
            errors["client_id"] = CLIENT_ID_TAKEN.format(slug=other)
        if not errors:
            return False
        for name, message in errors.items():
            self.add_error(name, ValidationError(message, code="unique"))
        self._forget_typed_secrets()
        return True

    @sensitive_variables("cleaned_data", "client_secret", "webhook_secret")
    def save(self, commit=True):
        """Save the connection through the model's secret methods, ``by`` the signed-in user.

        ``set_credentials`` decides whether anything changed (and so whether the version and
        the change record move); the webhook secret is stored, or removed, on its own.
        """
        connection = super().save(commit=False)
        cleaned_data = self.cleaned_data
        client_secret = cleaned_data.get("client_secret", "")
        webhook_secret = cleaned_data.get("webhook_secret", "")
        connection.set_credentials(
            account_id=cleaned_data["account_id"],
            client_id=cleaned_data["client_id"],
            client_secret=client_secret,
            by=self.user,
        )
        if webhook_secret:
            connection.set_webhook_secret(webhook_secret, by=self.user)
        elif cleaned_data.get("remove_webhook_secret"):
            connection.remove_webhook_secret(by=self.user)
        if commit:
            connection.save()
        return connection
