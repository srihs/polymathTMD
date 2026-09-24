/*
 * Polymath TMD — Direction D "Signpost" — progressive enhancements.
 * Every page works without this file. It binds only to data-* hooks and adds:
 *   1. ?demo= state switching (prototype-only; never ported into templates)
 *   2. sign-in error and form-error demos, including focus on the error summary
 *   3. success toast rendering, dismissal and Undo
 *   4. in-place queue filtering with a live result line
 *   5. the <dialog> confirm modal with focus return
 *   6. the busy state on the request form's submit button
 * No framework, no build step, no third-party script.
 */
(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var demo = params.get("demo");
  var doc = document;

  function $(sel, root) { return (root || doc).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); }

  /* ------------------------------------------------------------------
     1. ?demo= switching: show [data-demo="x"], hide [data-demo-hide="x"]
     ------------------------------------------------------------------ */
  $$("[data-nojs]").forEach(function (el) { el.hidden = true; });

  if (demo) {
    $$("[data-demo]").forEach(function (el) {
      if (el.getAttribute("data-demo").split(" ").indexOf(demo) !== -1) { el.hidden = false; }
    });
    $$("[data-demo-hide]").forEach(function (el) {
      if (el.getAttribute("data-demo-hide").split(" ").indexOf(demo) !== -1) { el.hidden = true; }
    });
  }

  /* No-permission demo: the page heading and lead say why, so the page
     keeps exactly one <h1> and it is the visible one. */
  var denied = $("[data-denied-title]");
  if (demo === "denied" && denied) {
    var deniedHeading = $("h1");
    var deniedLead = $("[data-lead]");
    if (deniedHeading) { deniedHeading.textContent = denied.getAttribute("data-denied-title"); }
    if (deniedLead) { deniedLead.textContent = denied.getAttribute("data-denied-lead"); }
  }

  /* On a phone the filter disclosure starts closed; without script it
     starts open, which still works. */
  var filterDetails = $("[data-filter-details]");
  if (filterDetails && window.matchMedia("(max-width: 1023px)").matches) {
    filterDetails.open = false;
  }

  /* ------------------------------------------------------------------
     2a. Sign-in error demo: keep the typed username, flag both fields,
         point them at the alert, and put focus in the password box.
     ------------------------------------------------------------------ */
  var loginAlert = $("[data-login-error]");
  if (demo === "error" && loginAlert) {
    var username = $("[data-login-username]");
    var password = $("[data-login-password]");
    if (username) {
      username.value = username.getAttribute("data-demo-value") || username.value;
      username.setAttribute("aria-invalid", "true");
      username.setAttribute("aria-describedby", (username.getAttribute("aria-describedby") || "") + " " + loginAlert.id);
    }
    if (password) {
      password.setAttribute("aria-invalid", "true");
      password.setAttribute("aria-describedby", (password.getAttribute("aria-describedby") || "") + " " + loginAlert.id);
      password.focus();
    }
  }

  /* ------------------------------------------------------------------
     2b. Form-errors demo: restore what the user typed, mark the failed
         fields, reveal their messages, focus the summary.
     ------------------------------------------------------------------ */
  var errorForm = $("form[data-demo-errors]");
  if (demo === "errors" && errorForm) {
    $$("[data-demo-value]", errorForm).forEach(function (el) {
      el.value = el.getAttribute("data-demo-value");
    });
    $$("[data-demo-checked]", errorForm).forEach(function (el) { el.checked = true; });
    errorForm.getAttribute("data-demo-errors").split(" ").forEach(function (id) {
      var field = doc.getElementById(id);
      var message = doc.getElementById(id + "-error");
      if (field) { field.setAttribute("aria-invalid", "true"); }
      if (message) { message.hidden = false; }
    });
    var summary = $("[data-error-summary]");
    if (summary) {
      summary.hidden = false;
      summary.focus();
      $$("a[href^='#']", summary).forEach(function (link) {
        link.addEventListener("click", function (event) {
          var target = doc.getElementById(link.getAttribute("href").slice(1));
          if (target) { event.preventDefault(); target.focus(); target.scrollIntoView({ block: "center" }); }
        });
      });
    }
  }

  /* ------------------------------------------------------------------
     3. Toast: cloned from <template data-toast-template>, role="status",
        8 s, pauses while hovered or focused, Undo and Close both dismiss.
     ------------------------------------------------------------------ */
  var toastRegion = $("[data-toast-region]");
  var toastTemplate = $("[data-toast-template]");

  function showToast(text, undoLabel) {
    if (!toastRegion || !toastTemplate) { return; }
    var node = toastTemplate.content.firstElementChild.cloneNode(true);
    var timer = null;
    $("[data-toast-text]", node).textContent = text;
    var undo = $("[data-toast-undo]", node);
    if (undo && !undoLabel) { undo.remove(); }
    function dismiss() { if (node.parentNode) { node.parentNode.removeChild(node); } }
    function arm() { clearTimeout(timer); timer = setTimeout(dismiss, 8000); }
    function pause() { clearTimeout(timer); }
    node.addEventListener("mouseenter", pause);
    node.addEventListener("mouseleave", arm);
    node.addEventListener("focusin", pause);
    node.addEventListener("focusout", arm);
    $$("[data-toast-close], [data-toast-undo]", node).forEach(function (btn) {
      btn.addEventListener("click", dismiss);
    });
    toastRegion.appendChild(node);
    arm();
  }

  var toastText = doc.body.getAttribute("data-toast");
  if (demo === "toast" && toastText) {
    showToast(toastText, doc.body.getAttribute("data-toast-undo") === "true");
    /* After a redirect, focus lands on the page's heading. */
    var heading = $("h1");
    if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus(); }
  }

  /* ------------------------------------------------------------------
     4. Queue filtering: the <form method="get"> still works; with script,
        rows filter in place, the result line updates, Apply is hidden.
     ------------------------------------------------------------------ */
  var filterForm = $("form[data-filter]");
  if (filterForm) {
    var rows = $$("[data-row]");
    var list = $("[data-rows]");
    var countLine = $("[data-count]");
    var waitLine = $("[data-wait]");
    var emptyState = $("[data-empty]");
    var pagination = $("[data-pagination]");
    var total = rows.length;
    var waitTimer = null;
    var urgencyRank = { "Urgent": 0, "Normal": 1, "Can wait": 2 };

    $$("[data-apply]", filterForm).forEach(function (el) { el.hidden = true; });

    function readForm() {
      var data = new FormData(filterForm);
      return {
        q: (data.get("q") || "").toString().trim().toLowerCase(),
        status: data.get("status") || "",
        urgency: data.get("urgency") || "",
        assignee: data.get("assignee") || "",
        sort: data.get("sort") || "newest"
      };
    }

    function applyFilters() {
      var f = readForm();
      var shown = 0;
      var visible = [];
      rows.forEach(function (row) {
        var hit = true;
        if (f.q && row.textContent.toLowerCase().indexOf(f.q) === -1) { hit = false; }
        if (f.status && row.getAttribute("data-status") !== f.status) { hit = false; }
        if (f.urgency && row.getAttribute("data-urgency") !== f.urgency) { hit = false; }
        if (f.assignee && row.getAttribute("data-assignee") !== f.assignee) { hit = false; }
        row.hidden = !hit;
        if (hit) { shown++; visible.push(row); }
      });
      visible.sort(function (a, b) {
        var ra = a.getAttribute("data-raised"), rb = b.getAttribute("data-raised");
        if (f.sort === "oldest") { return ra < rb ? -1 : ra > rb ? 1 : 0; }
        if (f.sort === "urgent") {
          var d = urgencyRank[a.getAttribute("data-urgency")] - urgencyRank[b.getAttribute("data-urgency")];
          if (d !== 0) { return d; }
        }
        return ra > rb ? -1 : ra < rb ? 1 : 0;
      });
      if (list) { visible.forEach(function (row) { list.appendChild(row); }); }
      if (countLine) {
        countLine.hidden = false;
        countLine.textContent = "Showing " + shown + " of " + total + " requests";
      }
      if (waitLine) { waitLine.hidden = true; }
      if (emptyState) { emptyState.hidden = shown !== 0; }
      if (list) { list.hidden = shown === 0; }
      if (pagination) { pagination.hidden = shown === 0; }
    }

    function scheduleFilters() {
      clearTimeout(waitTimer);
      if (waitLine && countLine) { countLine.hidden = true; waitLine.hidden = false; }
      waitTimer = setTimeout(applyFilters, 250);
    }

    filterForm.addEventListener("input", scheduleFilters);
    filterForm.addEventListener("change", scheduleFilters);
    filterForm.addEventListener("submit", function (event) { event.preventDefault(); applyFilters(); });
    $$("[data-clear]").forEach(function (el) {
      el.addEventListener("click", function (event) {
        event.preventDefault();
        filterForm.reset();
        applyFilters();
        var first = $("input, select", filterForm);
        if (first) { first.focus(); }
      });
    });

    if (demo === "empty") {
      /* Choices no request matches: every Fixed request already has someone on it. */
      var statusSel = $("[name='status']", filterForm);
      var assigneeSel = $("[name='assignee']", filterForm);
      if (statusSel) { statusSel.value = "Fixed"; }
      if (assigneeSel) { assigneeSel.value = "Nobody yet"; }
      var details = $("details", filterForm);
      if (details) { details.open = true; }
      applyFilters();
    }
  }

  /* ------------------------------------------------------------------
     5. Confirm dialog: the link falls back to the on-page confirm section;
        with script it opens the <dialog>, which traps focus and closes on
        Escape natively. Focus returns to the opener on close.
     ------------------------------------------------------------------ */
  $$("[data-open-dialog]").forEach(function (opener) {
    var dialog = doc.getElementById(opener.getAttribute("data-open-dialog"));
    if (!dialog || typeof dialog.showModal !== "function") { return; }
    opener.addEventListener("click", function (event) {
      event.preventDefault();
      dialog.showModal();
      var first = $("[data-dialog-first]", dialog) || $("button, a, input", dialog);
      if (first) { first.focus(); }
    });
    dialog.addEventListener("close", function () { opener.focus(); });
    $$("[data-close-dialog]", dialog).forEach(function (btn) {
      btn.addEventListener("click", function (event) { event.preventDefault(); dialog.close(); });
    });
  });

  /* ------------------------------------------------------------------
     6. Busy button: the submit reads "Sending…" while the page changes.
     ------------------------------------------------------------------ */
  $$("form[data-busy-label]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var btn = $("[type='submit']", form);
      if (!btn) { return; }
      btn.setAttribute("aria-busy", "true");
      var label = $("[data-btn-label]", btn);
      if (label) { label.textContent = form.getAttribute("data-busy-label"); }
      var spinner = $("[data-btn-spinner]", btn);
      if (spinner) { spinner.hidden = false; }
    });
  });

  /* ------------------------------------------------------------------
     7. Design kit only: pressable specimens that show the busy state.
     ------------------------------------------------------------------ */
  $$("[data-kit-toast]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showToast(btn.getAttribute("data-kit-toast"), true);
    });
  });
})();
