"""Views for Zoom link requests (brief 005), Zoom host accounts (brief 008) and the Zoom
timetable (brief 009).

Four areas:

- **Public** (no sign-in, the public frame): the request form, "check your email", confirm and
  confirmed. Abuse protection is a honeypot, hourly limits counted in the database, CSRF and
  a signed, expiring confirmation link (D8).
- **IT** (``zoom.review_linkrequest``, the shell): the queue, the detail with its clash
  preview, approve and reject. Anonymous visitors are sent to sign in; signed-in users without
  the permission get 403 (``PermissionRequiredMixin``'s default split).
- **Zoom accounts** (the shell): list, add and change host accounts, each page gated by its own
  built-in model permission (``view_``/``add_``/``change_hostaccount``), all held by the
  ``IT desk`` group. There's no delete (D4). The add and change views mask ``host_key`` in
  error reports, and the change view locks the account row on POST so the stop-booking rule
  can't race an approval (criterion 19).
- **Zoom timetable** (``zoom.review_linkrequest``, the shell; brief 009): a read-only month
  wall calendar and a day view. The calendar arithmetic is in ``timetable.py``; these views
  only parse the query, run two queries and call it.

The views stay thin: rules are on the models and QuerySets, and anything spanning several
models, the provider or email is in ``services.py``. Every context variable here is in the
brief's context contract.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.views.generic.detail import SingleObjectMixin

from apps.core.mixins import SignedInPermissionMixin

from . import services, timetable
from .forms import ApproveForm, HostAccountForm, LinkRequestForm, RejectForm
from .models import (
    QUEUE_TABS,
    WEEKDAY_NAMES,
    HostAccount,
    InvalidTransition,
    LinkRequest,
    Occurrence,
    class_date,
    queue_tab,
)
from .providers import get_provider
from .services import Outcome

# The session key that carries the address to "check your email" (popped on display).
SENT_TO_SESSION_KEY = "zoom_sent_to"

APPROVED_EMAIL_FAILED = (
    "Approved, but the email to {email} didn't send. Copy the link below and send it to them "
    "yourself. The host key is in the Zoom account's profile in Zoom."
)
REJECTED = "Not approved. We emailed the reason to {email}."
REJECTED_EMAIL_FAILED = (
    "Not approved, but the email to {email} didn't send. Tell them the reason yourself."
)
APPROVE_FIELDS = ("host_account", "join_url", "meeting_id", "passcode")

VIEW_ACCOUNTS = "zoom.view_hostaccount"
ADD_ACCOUNT = "zoom.add_hostaccount"
CHANGE_ACCOUNT = "zoom.change_hostaccount"

# Success flashes of the accounts pages (brief 008, criteria 10 and 14).
ACCOUNT_ADDED = "Added {label}."
ACCOUNT_SAVED = "Saved {label}."
ACCOUNT_SAVED_NEW_KEY = "Saved {label}. The new host key goes out with the next approved link."
ACCOUNT_SAVED_KEY_REMOVED = "Saved {label}. Its host key was removed."


class ReviewerRequiredMixin(SignedInPermissionMixin):
    """The link-request pages: the queue, the detail, approve and reject."""

    permission_required = services.REVIEW_PERMISSION


# --------------------------------------------------------------------------- Public pages


class LinkRequestCreateView(CreateView):
    """The public request form.

    A valid submit stores the request as ``unverified`` with its classes, emails the confirm
    link and redirects to "check your email". A honeypot hit gets the same redirect with
    nothing stored; a throttled submit re-renders with 429 and nothing stored.
    """

    form_class = LinkRequestForm
    template_name = "zoom/request_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        context.update(
            max_occurrences=LinkRequest.MAX_OCCURRENCES,
            today=today,
            latest_date=today + timedelta(days=LinkRequest.MAX_DAYS_AHEAD),
        )
        return context

    def form_valid(self, form):
        sent_url = reverse("zoom:request_sent")
        if form.is_honeypot_hit:
            self.request.session[SENT_TO_SESSION_KEY] = form.cleaned_data["requester_email"]
            return HttpResponseRedirect(sent_url)

        ip = services.client_ip(self.request)
        if services.is_throttled(email=form.cleaned_data["requester_email"], ip=ip):
            form.add_error(None, services.THROTTLED)
            return self.render_to_response(self.get_context_data(form=form), status=429)

        self.object = form.save(commit=False)
        self.object.submitted_ip = ip
        self.object.save()
        self.object.create_occurrences()
        services.send_confirm_email(self.request, self.object)
        self.request.session[SENT_TO_SESSION_KEY] = self.object.requester_email
        return HttpResponseRedirect(sent_url)


class RequestSentView(TemplateView):
    """ "Check your email". The address is shown once, then forgotten (it's in the session)."""

    template_name = "zoom/request_sent.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sent_to"] = self.request.session.pop(SENT_TO_SESSION_KEY, None)
        context["link_hours"] = settings.ZOOM_CONFIRM_LINK_HOURS
        return context


class ConfirmView(TemplateView):
    """GET shows the request for checking; only POST confirms (mail scanners prefetch GETs)."""

    template_name = "zoom/confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        state, link_request = services.confirm_state(self.kwargs["token"])
        context.update(self._state_context(state, link_request))
        return context

    def post(self, request, *args, **kwargs):
        token = self.kwargs["token"]
        state, link_request = services.confirm_state(token)
        if state == "ready":
            try:
                link_request.mark_verified()
            except InvalidTransition:
                state = "already"
            else:
                services.send_it_new_request_email(request, link_request)
                return redirect("zoom:confirmed", token=token)
        context = super().get_context_data(**kwargs)
        context.update(self._state_context(state, link_request))
        return self.render_to_response(context)

    def _state_context(self, state, link_request):
        occurrences = list(link_request.occurrences.all()) if link_request else []
        return {
            "state": state,
            "link_request": link_request,
            "occurrences": occurrences if state == "ready" else [],
            "occurrence_count": len(occurrences),
            "token": self.kwargs["token"],
        }


class ConfirmedView(TemplateView):
    """ "Request confirmed", named by the same token so no session is needed. Bad token: 404."""

    template_name = "zoom/confirmed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        link_request = services.confirmed_link_request(self.kwargs["token"])
        if link_request is None:
            raise Http404("No confirmed request for this link.")
        context["link_request"] = link_request
        return context


# --------------------------------------------------------------------------- IT pages


class QueueView(ReviewerRequiredMixin, ListView):
    """IT's queue: status tabs with counts, search within the tab, 25 per page."""

    template_name = "zoom/queue.html"
    context_object_name = "link_requests"
    paginate_by = 25

    def get_queryset(self):
        self.status = queue_tab(self.request.GET.get("status"))
        self.q = self.request.GET.get("q", "").strip()
        return (
            LinkRequest.objects.visible_to_it().with_schedule().for_tab(self.status).search(self.q)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counts = LinkRequest.objects.tab_counts()
        context.update(
            tabs=[
                {
                    "value": value,
                    "label": label,
                    "count": counts[value],
                    "current": value == self.status,
                }
                for value, label in QUEUE_TABS
            ],
            status=self.status,
            q=self.q,
            public_form_url=self.request.build_absolute_uri(reverse("zoom:request")),
        )
        return context


class ReviewContextMixin:
    """Builds the whole detail-page context, for the detail view and both error re-renders.

    One builder means an approve or reject that fails shows exactly what a fresh load would,
    with the availability re-read at that moment (criterion 37: "refreshed availability").
    No value built here ever holds a decrypted host key; only ``has_host_key`` is exposed.
    """

    def get_queryset(self):
        return LinkRequest.objects.visible_to_it().select_related("host_account", "decided_by")

    def review_context(
        self,
        link_request,
        *,
        approve_form=None,
        approve_initial=None,
        reject_form=None,
        approve_error=None,
    ):
        occurrences = list(link_request.occurrences.all())
        can_decide = link_request.can_be_decided()
        has_started = link_request.has_started()
        provider = get_provider()

        availability = []
        if can_decide:
            for account, clashes in HostAccount.objects.availability_for(occurrences):
                availability.append(
                    {
                        "account": account,
                        "is_free": not clashes,
                        "has_host_key": account.has_host_key,
                        # Classes of this request that clash, not clash pairs (D22, G4).
                        "busy_count": len({occurrence.pk for occurrence, _ in clashes}),
                        "clashes": [
                            {"occurrence": occurrence, "other": other}
                            for occurrence, other in clashes
                        ],
                    }
                )
        free = [entry["account"] for entry in availability if entry["is_free"]]

        if not can_decide or has_started or not free:
            approve_form = None
        elif approve_form is None:
            approve_form = ApproveForm(
                initial=approve_initial,
                free_accounts=free,
                needs_manual_details=provider.needs_manual_details,
            )
        else:
            approve_form.offer(free)
        if not can_decide:
            reject_form = None
        elif reject_form is None:
            reject_form = RejectForm()

        return {
            "object": link_request,
            "link_request": link_request,
            "occurrences": occurrences,
            "occurrence_count": len(occurrences),
            "can_decide": can_decide,
            "has_started": has_started,
            "availability": availability,
            "free_count": len(free),
            "overlapping_waiting": (
                LinkRequest.objects.overlapping_waiting(link_request, occurrences)
                if can_decide
                else []
            ),
            "earlier_requests": list(LinkRequest.objects.earlier_from_same_requester(link_request)),
            "approve_form": approve_form,
            "reject_form": reject_form,
            "needs_manual_details": provider.needs_manual_details,
            "approve_error": approve_error,
            "can_add_account": self.request.user.has_perm(ADD_ACCOUNT),
            "timetable_url": self.timetable_url(link_request, occurrences),
        }

    @staticmethod
    def timetable_url(link_request, occurrences):
        """``See it on the timetable`` (brief 009, criterion 20), or ``None``.

        Only an approved request has a place on one account's timetable: the month of its
        first class, filtered to its host account. Waiting and rejected requests get ``None``.
        """
        if link_request.status != LinkRequest.Status.APPROVED or not occurrences:
            return None
        first = min(occurrence.starts_at for occurrence in occurrences)
        month = timetable.Month.for_date(timezone.localdate(first))
        return month_page_url(month, link_request.host_account_id)

    def render_review(self, *, status=200, **kwargs):
        context = self.review_context(self.object, **kwargs)
        context["view"] = self
        return self.render_to_response(context, status=status)

    def already_decided(self):
        messages.error(self.request, services.ALREADY_DECIDED)
        return redirect("zoom:detail", pk=self.object.pk)


class LinkRequestDetailView(ReviewerRequiredMixin, ReviewContextMixin, DetailView):
    """Everything IT needs to decide: facts, classes, availability, and the two forms."""

    template_name = "zoom/detail.html"
    context_object_name = "link_request"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.review_context(self.object))
        return context


class _DecisionView(ReviewerRequiredMixin, ReviewContextMixin, SingleObjectMixin, FormView):
    """POST-only base for approve and reject: re-check the status, then the form."""

    http_method_names = ["post"]
    template_name = "zoom/detail.html"
    context_object_name = "link_request"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.can_be_decided():
            return self.already_decided()
        early = self.before_form()
        if early is not None:
            return early
        return super().post(request, *args, **kwargs)

    def before_form(self):
        """A response that ends the request before the form is read, or None."""
        return None

    def detail_redirect(self):
        return redirect("zoom:detail", pk=self.object.pk)


# Not inside the request-wide transaction (ATOMIC_REQUESTS): services.approve() must own the
# outermost transaction, because a MySQL deadlock rolls back the whole transaction and the
# page must still be re-rendered afterwards with fresh reads (D5, criterion 38).
@method_decorator(transaction.non_atomic_requests, name="dispatch")
class ApproveView(_DecisionView):
    form_class = ApproveForm

    def before_form(self):
        # The page itself shows the "already started" notice (criteria 31 and 39).
        if self.object.has_started():
            return self.render_review()
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["needs_manual_details"] = get_provider().needs_manual_details
        return kwargs

    def form_invalid(self, form):
        status = 409 if "host_account" in form.errors else 200
        return self.render_review(approve_form=form, status=status)

    def form_valid(self, form):
        result = services.approve(
            self.object.pk,
            account_id=form.cleaned_data["host_account"].pk,
            by=self.request.user,
            manual=form.manual_details(),
        )
        if result.outcome == Outcome.APPROVED:
            link_request = result.link_request
            if services.send_approved_email(self.request, link_request, result.host_key):
                messages.success(self.request, result.message)
            else:
                messages.warning(
                    self.request, APPROVED_EMAIL_FAILED.format(email=link_request.requester_email)
                )
            return self.detail_redirect()
        if result.outcome == Outcome.ALREADY_DECIDED:
            return self.already_decided()

        self.object.refresh_from_db()
        if result.outcome == Outcome.STARTED:
            return self.render_review(approve_form=form)
        status = 409 if result.outcome == Outcome.CONFLICT else 200
        return self.render_review(approve_form=form, approve_error=result.message, status=status)


class RejectView(_DecisionView):
    form_class = RejectForm

    def form_invalid(self, form):
        # Keep anything typed in the approve form if the page posted it along (criterion 43).
        approve_initial = {
            name: self.request.POST[name] for name in APPROVE_FIELDS if name in self.request.POST
        }
        return self.render_review(reject_form=form, approve_initial=approve_initial or None)

    def form_valid(self, form):
        try:
            self.object.reject(self.request.user, form.cleaned_data["reason"])
        except InvalidTransition:
            return self.already_decided()
        email = self.object.requester_email
        if services.send_rejected_email(self.request, self.object):
            messages.success(self.request, REJECTED.format(email=email))
        else:
            messages.warning(self.request, REJECTED_EMAIL_FAILED.format(email=email))
        return self.detail_redirect()


# --------------------------------------------------------------------------- Zoom timetable


def month_page_url(month, account_id=None) -> str:
    """``/zoom/timetable/?month=2026-10[&account=3]``: the month page for a month and filter.

    The only place a view builds a timetable address as a string, shared by the day view's
    ``month_url`` and the detail page's ``timetable_url`` (brief 009, D9). Templates build
    their other timetable links from ``{% url %}`` plus a query, as the queue does.
    """
    query = {"month": month.value}
    if account_id is not None:
        query["account"] = account_id
    return f"{reverse('zoom:timetable')}?{urlencode(query)}"


class TimetableContextMixin(ReviewerRequiredMixin):
    """What the month page and the day view share: the gate and the account filter.

    Both pages need ``zoom.review_linkrequest`` (D7): every entry links to a request detail,
    which needs it. The filter's accounts come from one query over every account, flagged by
    ``with_timetable_flag`` for the given month; the chosen account is resolved from that
    same list, so the query count doesn't depend on ``?account=`` (criterion 18).
    """

    def account_filter(self, month):
        """``(all_accounts, filter_accounts, selected_account)`` for ``month``, in one query.

        Everything is returned rather than kept on ``self``, so each caller takes what it uses
        and nothing reaches the context by side effect (review round 1, nit 2). The month page
        needs ``all_accounts`` for ``has_accounts``; the day view ignores it.
        """
        all_accounts = list(HostAccount.objects.with_timetable_flag(month.start, month.end))
        filter_accounts, selected = timetable.account_filter(
            all_accounts, timetable.parse_account_id(self.request.GET.get("account"))
        )
        return all_accounts, filter_accounts, selected


class TimetableMonthView(TimetableContextMixin, TemplateView):
    """The wall-calendar month (brief 009): weeks Monday to Sunday, day boxes of classes.

    Read-only. ``?month=`` and ``?account=`` fall back quietly when they're bad (D4). Two
    queries whatever the month holds: the filter's accounts and the month's classes.
    """

    template_name = "zoom/timetable.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month = timetable.parse_month(self.request.GET.get("month"), today)
        all_accounts, filter_accounts, selected = self.account_filter(month)
        occurrences = list(
            Occurrence.objects.for_timetable(month.start, month.end, account=selected)
        )
        booked_count, waiting_count = timetable.entry_counts(occurrences)
        context.update(
            month=month,
            previous_month=month.previous,
            next_month=month.next,
            is_current_month=month == timetable.Month.for_date(today),
            weeks=timetable.build_month(month, occurrences, today),
            weekdays=list(WEEKDAY_NAMES.values()),
            filter_accounts=filter_accounts,
            selected_account=selected,
            show_waiting=selected is None,
            booked_count=booked_count,
            waiting_count=waiting_count,
            has_accounts=bool(all_accounts),
            can_add_account=self.request.user.has_perm(ADD_ACCOUNT),
        )
        return context


class TimetableDayView(TimetableContextMixin, TemplateView):
    """Every class on one date, with no cap: where ``+N more`` and the day number lead.

    The date is in the path, which the app builds, so an impossible one is a 404 (D4). The
    filter offers the accounts of that date's month, by the same rules as the month page.
    """

    template_name = "zoom/timetable_day.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        day = timetable.parse_day(self.kwargs["year"], self.kwargs["month"], self.kwargs["day"])
        if day is None:
            raise Http404("No such date on the timetable.")
        month = timetable.Month.for_date(day)
        _, filter_accounts, selected = self.account_filter(month)
        start, end = timetable.day_bounds(day)
        occurrences = Occurrence.objects.for_timetable(start, end, account=selected)
        context.update(
            day=day,
            day_label=class_date(day),
            previous_day=day - timedelta(days=1),
            next_day=day + timedelta(days=1),
            month=month,
            month_url=month_page_url(month, selected.pk if selected else None),
            entries=timetable.day_entries(occurrences, day),
            filter_accounts=filter_accounts,
            selected_account=selected,
            show_waiting=selected is None,
        )
        return context


# --------------------------------------------------------------------------- Zoom accounts


class HostAccountListView(SignedInPermissionMixin, ListView):
    """Every account, in use first, with its upcoming classes. Not paged: there are few.

    Each accounts view names its own permission, so a user who may only view accounts can open
    the list but not the add or change pages (brief 008, criterion 2).
    """

    permission_required = VIEW_ACCOUNTS
    template_name = "zoom/accounts.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return HostAccount.objects.for_management()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(
            can_add=user.has_perm(ADD_ACCOUNT),
            can_change=user.has_perm(CHANGE_ACCOUNT),
            can_review=user.has_perm(services.REVIEW_PERMISSION),
        )
        return context


class HostAccountFormViewMixin(SignedInPermissionMixin):
    """What add and change share: the form, its user, the page context and the redirect.

    ``host_key_state`` is read from the stored row; the form never changes the key before it's
    saved, so a re-render shows the state as it is. Both concrete views wrap ``dispatch`` in
    ``sensitive_post_parameters("host_key")``, so a typed key is masked in their error reports
    (criterion 24).
    """

    form_class = HostAccountForm
    template_name = "zoom/account_form.html"
    context_object_name = "account"
    is_add = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("zoom:accounts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = None if self.is_add else self.object
        context.update(
            account=account,
            is_add=self.is_add,
            host_key_state=account.host_key_state if account else "none",
        )
        return context


@method_decorator(sensitive_post_parameters("host_key"), name="dispatch")
class HostAccountCreateView(HostAccountFormViewMixin, CreateView):
    permission_required = ADD_ACCOUNT
    is_add = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, ACCOUNT_ADDED.format(label=self.object.label))
        return response


@method_decorator(sensitive_post_parameters("host_key"), name="dispatch")
class HostAccountUpdateView(HostAccountFormViewMixin, UpdateView):
    """Change an account's details and its key; refuses to stop booking while classes are booked.

    On POST the account row is read with ``select_for_update()`` inside the request's
    transaction (``ATOMIC_REQUESTS``), before the form is validated. The form's check of
    upcoming classes and the save then run under that lock, and ``services.approve()`` waits
    for it before booking this account (criterion 19).

    ``saved_label``, ``upcoming_count`` and ``next_class_start`` are captured from the stored
    row when it's read: on an invalid POST, ``construct_instance`` has already put the typed
    values on ``self.object``, and the heading must still name the account as saved (G3, G4).
    """

    permission_required = CHANGE_ACCOUNT

    def get_queryset(self):
        accounts = HostAccount.objects.with_upcoming()
        if self.request.method == "POST":
            accounts = accounts.select_for_update()
        return accounts

    def get_object(self, queryset=None):
        account = super().get_object(queryset)
        self.saved_label = account.label
        self.upcoming_count = account.upcoming_count
        self.next_class_start = account.next_class_start
        return account

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            saved_label=self.saved_label,
            upcoming_count=self.upcoming_count,
            next_class_start=self.next_class_start,
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.key_changed:
            message = ACCOUNT_SAVED_NEW_KEY
        elif form.key_removed:
            message = ACCOUNT_SAVED_KEY_REMOVED
        else:
            message = ACCOUNT_SAVED
        messages.success(self.request, message.format(label=self.object.label))
        return response
