/*
 * Direction C — Broadsheet · progressive enhancement for the prototype.
 * One IIFE. Every hook is a data-* attribute; nothing here is needed for a page
 * to work. Blocks: 1 helpers · 2 ?demo= state switching · 3 toast ·
 * 4 error summary focus · 5 queue filtering with a live count · 6 dialog ·
 * 7 "On this page" scrollspy (this direction's one flourish).
 */
(function () {
  "use strict";

  /* 1. Helpers ------------------------------------------------------------- */
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var demo = new URLSearchParams(window.location.search).get("demo") || "";
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Clone a symbol from the inline sprite into a fresh <svg>. */
  function icon(name, extraClass) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "icon" + (extraClass ? " " + extraClass : ""));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var use = document.createElementNS(ns, "use");
    use.setAttribute("href", "#i-" + name);
    svg.appendChild(use);
    return svg;
  }

  /* 2. ?demo= state switching — prototype only, never ported ---------------- */
  if (demo) {
    /* Reveal blocks written for this state, hide blocks that belong to the default. */
    $$("[data-demo]").forEach(function (el) {
      if (el.getAttribute("data-demo").split(" ").indexOf(demo) !== -1) { el.hidden = false; }
    });
    $$("[data-demo-hide]").forEach(function (el) {
      if (el.getAttribute("data-demo-hide").split(" ").indexOf(demo) !== -1) { el.hidden = true; }
    });
    /* Mark failed fields: data-demo-invalid="errors" -> aria-invalid="true". */
    $$("[data-demo-invalid]").forEach(function (el) {
      if (el.getAttribute("data-demo-invalid") === demo) { el.setAttribute("aria-invalid", "true"); }
    });
    /* Restore what the user typed: data-demo-value="errors" + data-value="...". */
    $$("[data-demo-value]").forEach(function (el) {
      if (el.getAttribute("data-demo-value") !== demo) { return; }
      var v = el.getAttribute("data-value");
      if (el.type === "radio" || el.type === "checkbox") { el.checked = true; }
      else if (v !== null) { el.value = v; }
    });
    /* Move focus where the state says: data-demo-focus="error". */
    var target = $$("[data-demo-focus]").filter(function (el) { return el.getAttribute("data-demo-focus") === demo; })[0];
    if (target) { target.focus(); }
  }

  /* 3. Toast — role="status", 8 s, pauses on hover and focus ----------------- */
  var toastTpl = $("template[data-toast-template]");
  function showToast(message, withUndo) {
    if (!toastTpl) { return null; }
    var node = toastTpl.content.firstElementChild.cloneNode(true);
    var text = $("[data-toast-text]", node);
    if (text) { text.textContent = message; }
    var undo = $("[data-toast-undo]", node);
    if (undo && !withUndo) { undo.parentNode.removeChild(undo); }
    var p = $("p", node);
    if (p) { p.insertBefore(icon("check-circle"), p.firstChild); }
    document.body.appendChild(node);
    var timer = null;
    var remaining = 8000;
    var started = Date.now();
    function close() { if (node.parentNode) { node.parentNode.removeChild(node); } clearTimeout(timer); }
    function start() { started = Date.now(); timer = setTimeout(close, remaining); }
    function pause() { clearTimeout(timer); remaining -= Date.now() - started; }
    node.addEventListener("mouseenter", pause);
    node.addEventListener("mouseleave", start);
    node.addEventListener("focusin", pause);
    node.addEventListener("focusout", start);
    $$("[data-toast-close], [data-toast-undo]", node).forEach(function (b) { b.addEventListener("click", close); });
    start();
    return node;
  }
  if (demo === "toast") {
    var msg = document.body.getAttribute("data-toast-message") || "Request sent. We gave it the number REQ-2049.";
    showToast(msg, true);
  }
  /* Any element can raise a toast: data-toast="message text". */
  $$("[data-toast]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (el.tagName === "A") { e.preventDefault(); }
      showToast(el.getAttribute("data-toast"), el.hasAttribute("data-toast-with-undo"));
    });
  });

  /* 4. Error summary: focus it on load, and send each link to its field ----- */
  var summary = $("[data-error-summary]");
  if (summary && !summary.hidden) {
    summary.focus();
    $$("a[href^='#']", summary).forEach(function (a) {
      a.addEventListener("click", function (e) {
        var field = $(a.getAttribute("href"));
        if (field) { e.preventDefault(); field.focus(); field.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" }); }
      });
    });
  }

  /* 5. Queue filtering in place, with a live count line ---------------------- */
  var queueForm = $("[data-filter-form]");
  var queue = $("[data-queue]");
  if (queueForm && queue) {
    var rows = $$("tbody tr", queue);
    var countLine = $("[data-count]");
    var apply = $("[data-filter-apply]", queueForm);
    var emptyBlock = $("[data-queue-empty]");
    var pager = $("[data-pager]");
    var debounce = null;
    if (apply) { apply.hidden = true; }

    function textOf(el) { return (el.textContent || "").toLowerCase(); }
    function runFilter() {
      var q = (queueForm.elements.q ? queueForm.elements.q.value : "").trim().toLowerCase();
      var status = queueForm.elements.status ? queueForm.elements.status.value : "";
      var urgency = queueForm.elements.urgency ? queueForm.elements.urgency.value : "";
      var who = queueForm.elements.who ? queueForm.elements.who.value : "";
      var sort = queueForm.elements.sort ? queueForm.elements.sort.value : "newest";
      var shown = 0;
      rows.forEach(function (tr) {
        var ok = true;
        if (q && textOf(tr).indexOf(q) === -1) { ok = false; }
        if (status && tr.getAttribute("data-status") !== status) { ok = false; }
        if (urgency && tr.getAttribute("data-urgency") !== urgency) { ok = false; }
        if (who && tr.getAttribute("data-who") !== who) { ok = false; }
        tr.hidden = !ok;
        if (ok) { shown++; }
      });
      var order = rows.slice().sort(function (a, b) {
        var wa = +a.getAttribute("data-when"), wb = +b.getAttribute("data-when");
        /* Most urgent first lifts only the Urgent rows; everything else keeps newest-first order. */
        if (sort === "urgent") { return ((b.getAttribute("data-urgency") === "Urgent") - (a.getAttribute("data-urgency") === "Urgent")) || (wb - wa); }
        if (sort === "oldest") { return wa - wb; }
        return wb - wa;
      });
      var tbody = $("tbody", queue);
      order.forEach(function (tr) { tbody.appendChild(tr); });
      if (countLine) {
        countLine.textContent = "Showing " + shown + " of " + rows.length + " requests";
      }
      var none = shown === 0;
      if (emptyBlock) { emptyBlock.hidden = !none; }
      queue.hidden = none;
      if (pager) { pager.hidden = none; }
    }
    function showWaiting() {
      if (!countLine) { return; }
      countLine.textContent = "";
      countLine.appendChild(icon("refresh", "icon--spin"));
      countLine.appendChild(document.createTextNode("Finding requests…"));
    }
    function schedule() {
      clearTimeout(debounce);
      showWaiting();
      debounce = setTimeout(runFilter, 250);
    }
    /* The margin selects are tied to the form with form="…", not nested in it,
       so bind to the form's associated elements rather than the form node. */
    Array.prototype.forEach.call(queueForm.elements, function (el) {
      el.addEventListener("input", schedule);
      el.addEventListener("change", schedule);
    });
    queueForm.addEventListener("submit", function (e) { e.preventDefault(); clearTimeout(debounce); runFilter(); });
    $$("[data-filter-clear]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        queueForm.reset();
        runFilter();
        if (queueForm.elements.q) { queueForm.elements.q.focus(); }
      });
    });
    if (demo === "empty") {
      /* A combination that matches nothing: Closed and Urgent. */
      if (queueForm.elements.status) { queueForm.elements.status.value = "Closed"; }
      if (queueForm.elements.urgency) { queueForm.elements.urgency.value = "Urgent"; }
      runFilter();
    }
  }

  /* 6. Dialog: open from a link whose fallback is the confirm section --------- */
  $$("[data-dialog-open]").forEach(function (opener) {
    var dlg = document.getElementById(opener.getAttribute("data-dialog-open"));
    if (!dlg || typeof dlg.showModal !== "function") { return; }
    opener.addEventListener("click", function (e) {
      e.preventDefault();
      dlg.showModal();
      var first = $("button, [href], input, select, textarea", dlg);
      if (first) { first.focus(); }
    });
    dlg.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") { return; }
      var f = $$("button:not([disabled]), [href], input, select, textarea", dlg);
      if (!f.length) { return; }
      var firstEl = f[0], lastEl = f[f.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus(); }
      else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus(); }
    });
    dlg.addEventListener("close", function () { opener.focus(); });
    $$("[data-dialog-cancel]", dlg).forEach(function (b) { b.addEventListener("click", function (e) { e.preventDefault(); dlg.close(); }); });
    $$("[data-dialog-confirm]", dlg).forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        dlg.close();
        showToast(b.getAttribute("data-dialog-confirm"), false);
      });
    });
  });

  /* 7. Disclosures that are open on a wide screen but start closed on a phone.
        Without scripting they stay open, so nothing is ever hidden. ---------- */
  if (window.matchMedia("(max-width: 1079px)").matches) {
    $$("details[data-closed-narrow]").forEach(function (d) { d.open = false; });
  }

  /* 8. Scrollspy for the desktop "On this page" index ------------------------ */
  var index = $("[data-pageindex]");
  if (index && "IntersectionObserver" in window) {
    var links = $$("a[href^='#']", index);
    var headings = links.map(function (a) { return $(a.getAttribute("href")); }).filter(Boolean);
    var mark = function (id) {
      links.forEach(function (a) {
        if (a.getAttribute("href") === "#" + id) { a.setAttribute("aria-current", "true"); }
        else { a.removeAttribute("aria-current"); }
      });
    };
    var visible = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { visible[en.target.id] = en.isIntersecting; });
      var current = headings.filter(function (h) { return visible[h.id]; })[0];
      if (!current) {
        /* Nothing in view: mark the last heading that has scrolled past. */
        var passed = headings.filter(function (h) { return h.getBoundingClientRect().top < 0; });
        current = passed[passed.length - 1];
      }
      if (current) { mark(current.id); }
    }, { rootMargin: "0px 0px -60% 0px" });
    headings.forEach(function (h) { io.observe(h); });
    links.forEach(function (a) { a.addEventListener("click", function () { mark(a.getAttribute("href").slice(1)); }); });
  }
})();
