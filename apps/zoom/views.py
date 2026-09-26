"""Views for Zoom link requests (brief 005), Zoom host accounts (brief 008), the Zoom
timetable (brief 009), the live Zoom connection (brief 006), and cancelling and the start link
(brief 011).

Five areas:

- **Public** (no sign-in, the public frame): the request form, "check your email", confirm and
  confirmed. Abuse protection is a honeypot, hourly limits counted in the database, CSRF and
  a signed, expiring confirmation link (D8).
- **IT** (``zoom.review_linkrequest``, the shell): the queue, the detail with its clash
  preview, approve and reject. The detail, approve and reject views are
  ``non_atomic_requests``: they wait on Zoom over HTTP, and no database transaction may be
  held open meanwhile (brief 006, D8, criterion 20). Anonymous visitors are sent to sign in;
  signed-in users without the permission get 403 (``PermissionRequiredMixin``'s default split).
- **Zoom accounts** (the shell): list, add and change host accounts, each page gated by its own
  built-in model permission (``view_``/``add_``/``change_hostaccount``), all held by the
  ``IT desk`` group. There's no delete (D4). The add and change views mask ``host_key`` in
  error reports, and the change view locks the account row on POST so the stop-booking rule
  can't race an approval (criterion 19). "Check connection" (brief 006) is a POST-only view
  that asks Zoom, shows the answer as a message and stores nothing.
- **Zoom timetable** (``zoom.review_linkrequest``, the shell; brief 009): a read-only month
  wall calendar and a day view. The calendar arithmetic is in ``timetable.py``; these views
  only parse the query, run two queries and call it.
- **Brief 011**: cancelling a booking or one class (``zoom.review_linkrequest``, a confirm page
  then a POST, ``non_atomic_requests`` because ``services.cancel()`` owns its transaction and
  calls Zoom); the public start page (a signed token, GET shows, POST asks Zoom and
  redirects); and ``Show host key`` (``zoom.change_hostaccount``, POST only). The start page
  and the reveal send ``Cache-Control: no-store`` and ``Referrer-Policy: no-referrer`` on
  every response, because both carry something that lets its holder act as host.

The views stay thin: rules are on the models and QuerySets, and anything spanning several
models, the provider or email is in ``services.py``. Every context variable here is in the
brief's context contract.
"""

from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from django.views.generic.detail import SingleObjectMixin

from apps.core.mixins import SignedInPermissionMixin

from . import services, timetable
from .forms import ApproveForm, CancelForm, HostAccountForm, LinkRequestForm, RejectForm
from .models import (
    QUEUE_TABS,
    WEEKDAY_NAMES,
    HostAccount,
    HostKeyUnreadable,
    InvalidTransition,
    LinkRequest,
    Occurrence,
    class_date,
    queue_tab,
    zoom_connection_state_for,
)
from .providers import get_provider
from .services import Outcome

# The session key that carries the address to "check your email" (popped on display).
SENT_TO_SESSION_KEY = "zoom_sent_to"

# Brief 011, criterion 30: the start link replaced the host key in the approval email.
APPROVED_EMAIL_FAILED = (
    "Approved, but the email to {email} didn't send. Copy the Zoom link and the start link "
    "below and send them to them yourself."
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
ACCOUNT_SAVED_NEW_KEY = "Saved {label} and its new host key."
ACCOUNT_SAVED_KEY_REMOVED = "Saved {label}. Its host key was removed."
# Brief 011, criterion 41: why Show host key didn't show one. The unreadable text is 008's.
NO_HOST_KEY_SAVED = "{label} has no host key saved."
HOST_KEY_CANT_BE_READ = (
    "A host key is saved, but it can't be read with the current encryption keys. Type it again."
)
# The stored key states in which it can be decrypted and so shown (criterion 44).
READABLE_KEY_STATES = ("saved", "saved_legacy")


def no_referrer(view):
    """Send ``Referrer-Policy: no-referrer`` on every response of ``view`` (brief 011, D4).

    The start page's URL is a start link and the reveal page holds a host key: neither page's
    address may leave the browser as a ``Referer``, to Zoom or anywhere else. Set on the
    response itself, so ``SecurityMiddleware`` (which only fills the header in when it's
    missing) leaves it alone.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        response["Referrer-Policy"] = "no-referrer"
        return response

    return wrapper


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

    Brief 011 adds the cancel and start-link values. Every rule behind them is a model method
    given the classes already loaded for the page, so they cost no query of their own.

    The availability comes from ``services.availability()``, which asks Zoom (brief 006). The
    notice when there's no approve form is the template's, in the order ``has_started``, then
    ``all_unchecked``, then "none free" (D22, G3); ``approve_form`` is ``None`` in all three.
    """

    def get_queryset(self):
        # ``cancelled_by`` too: a cancelled booking's notice names who cancelled it (011, SF1).
        return LinkRequest.objects.visible_to_it().select_related(
            "host_account", "decided_by", "cancelled_by"
        )

    def review_context(
        self,
        link_request,
        *,
        approve_form=None,
        approve_initial=None,
        reject_form=None,
        approve_error=None,
    ):
        # Each cancelled class's row says who cancelled it; joining the user here keeps that to
        # no extra query per class (brief 011, review round 1, SF1).
        occurrences = list(link_request.occurrences.select_related("cancelled_by"))
        can_decide = link_request.can_be_decided()
        has_started = link_request.has_started()
        provider = get_provider()

        availability, free, zoom_checked_at, all_unchecked = [], [], None, False
        if can_decide:
            result = services.availability(
                link_request,
                occurrences,
                provider=provider,
                account_edit_allowed=self.request.user.has_perm(CHANGE_ACCOUNT),
            )
            availability, free = result.entries, result.free_accounts
            zoom_checked_at, all_unchecked = result.zoom_checked_at, result.all_unchecked

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

        approved = link_request.status == LinkRequest.Status.APPROVED
        now = timezone.now()
        in_progress = link_request.class_in_progress(now, occurrences=occurrences)

        return {
            "object": link_request,
            "link_request": link_request,
            "occurrences": occurrences,
            "occurrence_count": len(occurrences),
            "can_decide": can_decide,
            "has_started": has_started,
            "availability": availability,
            "free_count": len(free),
            "checks_zoom": provider.checks_zoom,
            "zoom_checked_at": zoom_checked_at,
            "all_unchecked": all_unchecked,
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
            # Brief 011 (criteria 8 and 31; G1, G2).
            "can_cancel_booking": link_request.can_cancel_booking(now, occurrences=occurrences),
            "cancellable_ids": (
                {o.pk for o in link_request.cancellable_classes(now, occurrences=occurrences)}
                if link_request.repeat == LinkRequest.Repeat.WEEKLY
                else set()
            ),
            "in_progress_id": in_progress.pk if in_progress else None,
            "cancel_blocked_message": (
                link_request.cancel_booking_blocked_message(now, occurrences=occurrences)
                if approved
                else None
            ),
            "start_link": (
                services.start_link(self.request, link_request)
                if approved and provider.can_start
                else None
            ),
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


# Not inside the request-wide transaction: the availability waits on Zoom over HTTP (brief
# 006, D8), and no transaction may be held open meanwhile.
@method_decorator(transaction.non_atomic_requests, name="dispatch")
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
            if services.send_approved_email(self.request, link_request):
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


# Non-atomic for the same reason as the detail: an invalid reason re-renders the page, which
# asks Zoom. ``reject()`` is one conditional UPDATE, so it needs no surrounding transaction.
@method_decorator(transaction.non_atomic_requests, name="dispatch")
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


# --------------------------------------------------------------------------- Cancelling (011)


# Not inside the request-wide transaction (ATOMIC_REQUESTS): services.cancel() must own the
# outermost transaction, because it calls Zoom with the locks held and retries a deadlock,
# which rolls back the whole transaction (criterion 10, as for approve).
@method_decorator(transaction.non_atomic_requests, name="dispatch")
class CancelBookingView(ReviewerRequiredMixin, SingleObjectMixin, FormView):
    """Cancel a whole booking: GET shows the confirm page, POST cancels (brief 011, 5-15).

    Only approved (or already cancelled) bookings have this page; any other request is a 404.
    When there's nothing to cancel, GET and POST both go back to the detail with criterion 6's
    message and no Zoom call. Everything else is ``services.cancel()``; this view parses the
    form, calls it, and picks a response.
    """

    form_class = CancelForm
    template_name = "zoom/cancel_confirm.html"
    context_object_name = "link_request"

    def get_queryset(self):
        return LinkRequest.objects.filter(
            status__in=[LinkRequest.Status.APPROVED, LinkRequest.Status.CANCELLED]
        ).select_related("host_account")

    def get_occurrence(self):
        """The one class being cancelled, or ``None`` for the whole booking."""
        return None

    def setup_objects(self):
        self.object = self.get_object()
        self.occurrence = self.get_occurrence()
        self.occurrences = list(self.object.occurrences.all())

    def blocked_message(self):
        """Criterion 6's message when there's nothing to do, else ``None`` (from the models)."""
        if self.occurrence is not None:
            return self.occurrence.cancel_blocked_message()
        return self.object.cancel_booking_blocked_message(occurrences=self.occurrences)

    def nothing_to_do(self, message):
        messages.error(self.request, message)
        return redirect("zoom:detail", pk=self.object.pk)

    def get(self, request, *args, **kwargs):
        self.setup_objects()
        blocked = self.blocked_message()
        if blocked:
            return self.nothing_to_do(blocked)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.setup_objects()
        blocked = self.blocked_message()
        if blocked:
            return self.nothing_to_do(blocked)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        if self.occurrence is not None:
            to_cancel, kept = [self.occurrence], []
        else:
            to_cancel = self.object.cancellable_classes(now, occurrences=self.occurrences)
            kept = self.object.kept_classes(now, occurrences=self.occurrences)
        context.update(
            link_request=self.object,
            occurrence=self.occurrence,
            checks_zoom=get_provider().checks_zoom,
            to_cancel=to_cancel,
            kept=kept,
            cancel_error=kwargs.get("cancel_error"),
        )
        return context

    def form_valid(self, form):
        reason = form.cleaned_data["reason"]
        result = services.cancel(
            self.object.pk,
            occurrence_id=self.occurrence.pk if self.occurrence else None,
            by=self.request.user,
            reason=reason,
        )
        if result.outcome == Outcome.CANCELLED:
            emailed = services.send_cancelled_email(
                self.request, result.link_request, result.cancelled, result.remaining, reason
            )
            level, text = services.cancelled_message(
                result, emailed=emailed, checks_zoom=get_provider().checks_zoom
            )
            messages.add_message(self.request, level, text)
            return redirect("zoom:detail", pk=self.object.pk)
        if result.outcome == Outcome.NOTHING_TO_DO:
            return self.nothing_to_do(result.message)
        # Nothing was cancelled here: show the page again, fresh, with the reason kept.
        self.setup_objects()
        return self.render_to_response(
            self.get_context_data(form=form, cancel_error=result.message)
        )


class CancelClassView(CancelBookingView):
    """Cancel one class of a weekly booking (brief 011, criterion 5).

    A class of another request is a 404, and so is any class of a one-off booking: its only
    class *is* the booking, which ``zoom:cancel`` cancels.
    """

    def get_occurrence(self):
        if self.object.repeat != LinkRequest.Repeat.WEEKLY:
            raise Http404("A one-off booking is cancelled as a whole.")
        return get_object_or_404(
            Occurrence.objects.select_related("host_account"),
            pk=self.kwargs["occurrence_pk"],
            link_request=self.object,
        )


# --------------------------------------------------------------------------- Start link (011)


# never_cache gives Cache-Control: no-store (and no-cache, must-revalidate, private) on every
# response, the redirect to Zoom included; non-atomic because the POST waits on Zoom.
@method_decorator([never_cache, no_referrer, transaction.non_atomic_requests], name="dispatch")
class StartClassView(TemplateView):
    """ "Start this class", public, from the approval email (brief 011, criteria 19-26).

    GET only shows the state and never calls Zoom, because mail scanners fetch links, and a
    scanner that followed a redirect would hold a working host link (D4). POST, in the
    ``ready`` state, asks Zoom for a fresh ``start_url`` and redirects there (302). That URL is
    only in memory, in ``services.start_class()`` and here, and is never stored or logged.
    """

    template_name = "zoom/start.html"
    # HEAD is answered as GET (Django's View does that), so `curl -I` shows the headers.
    http_method_names = ["get", "head", "post"]

    def get(self, request, *args, **kwargs):
        link_request = services.link_request_from_start_token(kwargs["token"])
        if link_request is None:
            return self.invalid()
        return self.show(link_request, services.start_state(link_request))

    @sensitive_variables("result")
    def post(self, request, *args, **kwargs):
        link_request = services.link_request_from_start_token(kwargs["token"])
        if link_request is None:
            return self.invalid()
        result = services.start_class(link_request, ip=services.client_ip(request))
        if result.url:
            return HttpResponseRedirect(result.url)
        return self.show(link_request, result)

    def base_context(self):
        return {"it_desk_phone": services.it_desk_phone()}

    def invalid(self):
        context = self.base_context()
        context.update(
            state="invalid",
            link_request=None,
            occurrence=None,
            opens_at=None,
            opens_after_other_class=False,
            start_error=None,
            start_error_still=False,
            token=None,
        )
        return self.render_to_response(context, status=404)

    def show(self, link_request, result):
        context = self.base_context()
        context.update(
            state=result.state,
            link_request=link_request,
            occurrence=result.occurrence,
            opens_at=result.opens_at,
            opens_after_other_class=result.opens_after_other_class,
            start_error=result.error,
            start_error_still=result.error_still,
            token=self.kwargs["token"],
        )
        return self.render_to_response(context)


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
        # The *stored* connection name: an invalid submit has already put the typed one on
        # ``self.object``, and the state line describes what's saved (brief 006, criterion 35).
        stored_name = "" if self.is_add else self.saved_credential_set
        context.update(
            account=account,
            is_add=self.is_add,
            host_key_state=account.host_key_state if account else "none",
            # Brief 011, criterion 44: the add page never offers a reveal.
            can_reveal_host_key=False,
            last_key_reveal=None,
            key_reveal_count=0,
            zoom_connection_state=zoom_connection_state_for(stored_name),
            zoom_connection_name=stored_name,
            # G5: the check form's action uses account.pk, so it's only offered with an account.
            can_check_connection=account is not None and self.request.user.has_perm(CHANGE_ACCOUNT),
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
        self.saved_credential_set = account.credential_set
        self.upcoming_count = account.upcoming_count
        self.next_class_start = account.next_class_start
        return account

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Criterion 44: from the state the mixin already worked out, so no second decrypt.
        readable = context["host_key_state"] in READABLE_KEY_STATES
        context.update(
            saved_label=self.saved_label,
            upcoming_count=self.upcoming_count,
            next_class_start=self.next_class_start,
            can_reveal_host_key=readable and self.request.user.has_perm(CHANGE_ACCOUNT),
            last_key_reveal=self.object.last_key_reveal(),
            key_reveal_count=self.object.key_reveal_count(),
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


@method_decorator(transaction.non_atomic_requests, name="dispatch")
class HostAccountCheckView(SignedInPermissionMixin, SingleObjectMixin, View):
    """ "Check connection": ask Zoom whether this account's connection works (criterion 36).

    POST only, because it calls out; gated by ``zoom.change_hostaccount``, which the IT desk
    holds. Non-atomic: no transaction is held open while Zoom answers. The result comes back
    as one message on the change page, and nothing about it is stored (D12).
    """

    permission_required = CHANGE_ACCOUNT
    http_method_names = ["post"]
    model = HostAccount

    def post(self, request, *args, **kwargs):
        account = self.get_object()
        result = services.check_connection(account)
        messages.add_message(request, result.level, result.message)
        return redirect("zoom:account_edit", pk=account.pk)


@method_decorator([never_cache, no_referrer], name="dispatch")
class HostKeyRevealView(SignedInPermissionMixin, SingleObjectMixin, View):
    """ "Show host key": the IT-only fallback when a start link fails (brief 011, 40-44; D11).

    POST only, so nothing prefetches or caches it, and each reveal is one deliberate, recorded
    act; gated by ``zoom.change_hostaccount``, which the IT desk holds. ``never_cache`` and
    ``no_referrer`` cover every response, the page and both redirects. The key is decrypted
    only in ``services.reveal_host_key()``, which records the reveal; this frame holds it as
    ``plain``, masked in error reports, and hands it to ``zoom/host_key_reveal.html`` only.
    """

    permission_required = CHANGE_ACCOUNT
    http_method_names = ["post"]
    model = HostAccount

    @sensitive_variables("plain", "context")
    def post(self, request, *args, **kwargs):
        account = self.get_object()
        try:
            plain = services.reveal_host_key(account, by=request.user)
        except services.NoHostKeySaved:
            messages.error(request, NO_HOST_KEY_SAVED.format(label=account.label))
            return redirect("zoom:account_edit", pk=account.pk)
        except HostKeyUnreadable:
            messages.error(request, HOST_KEY_CANT_BE_READ)
            return redirect("zoom:account_edit", pk=account.pk)
        context = {"account": account, "host_key": plain}
        return render(request, "zoom/host_key_reveal.html", context)
