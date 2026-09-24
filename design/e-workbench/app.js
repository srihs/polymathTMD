/* ==========================================================================
   Polymath TMD — Direction E "Workbench" — progressive enhancements only.

   Every page works with this file absent: forms submit, links navigate, the
   menu is an anchor, the confirm dialog renders inline. This IIFE only adds:
     1  toasts
     2  the "/" search shortcut
     3  in-place filtering with a live result line
     4  the pane swap on requests.html (record filled from the row's data-*)
     5  disclosures closed by default on a phone
     6  the confirm <dialog>: open, trap, close, return focus
     7  error-summary links that move focus to the field
     8  section-index marking
     9  busy buttons on submit
    10  ?demo= state switching — prototype-only, never ported to templates
    11  the account menu <details>: Escape, outside click and focus-out close it
   Everything binds through data-* attributes, never classes or DOM shape.
   ========================================================================== */
(function () {
  "use strict";

  var doc = document;
  var $ = function (sel, root) { return (root || doc).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); };
  var phone = window.matchMedia("(max-width: 1079px)");
  var live = $("[data-live]");
  var SVG = "http://www.w3.org/2000/svg";

  function announce(text) {
    if (!live) return;
    live.textContent = "";
    window.setTimeout(function () { live.textContent = text; }, 50);
  }

  function icon(name, cls) {
    var svg = doc.createElementNS(SVG, "svg");
    svg.setAttribute("class", "icon" + (cls ? " " + cls : ""));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var use = doc.createElementNS(SVG, "use");
    use.setAttribute("href", "#i-" + name);
    svg.appendChild(use);
    return svg;
  }

  function button(cls, label, ariaLabel) {
    var b = doc.createElement("button");
    b.type = "button";
    b.className = cls;
    if (ariaLabel) { b.setAttribute("aria-label", ariaLabel); b.appendChild(icon(label)); }
    else { b.textContent = label; }
    return b;
  }

  /* 1. Toasts — role="status", 8 seconds, paused while hovered or focused */
  var toasts = $("[data-toasts]");
  function toast(text, opts) {
    if (!toasts) return null;
    var t = doc.createElement("div");
    t.className = "toast on-chrome";
    t.setAttribute("role", "status");
    t.appendChild(icon("check"));
    var s = doc.createElement("span");
    s.className = "toast__text";
    s.textContent = text;
    t.appendChild(s);
    var timer;
    function remove() {
      window.clearTimeout(timer);
      t.classList.add("is-leaving");
      window.setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 140);
    }
    if (opts && opts.undo) {
      var u = button("btn btn--quiet btn--compact", "Undo");
      u.addEventListener("click", function () { remove(); opts.undo(); });
      t.appendChild(u);
    }
    var c = button("btn btn--icon btn--compact", "close", "Close");
    c.addEventListener("click", remove);
    t.appendChild(c);
    toasts.appendChild(t);
    function start() { timer = window.setTimeout(remove, 8000); }
    function pause() { window.clearTimeout(timer); }
    t.addEventListener("mouseenter", pause);
    t.addEventListener("focusin", pause);
    t.addEventListener("mouseleave", start);
    t.addEventListener("focusout", start);
    start();
    return t;
  }

  /* 2. "/" focuses the search box, unless you are already typing somewhere */
  doc.addEventListener("keydown", function (e) {
    if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    var typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
    if (typing) return;
    var q = $("#q");
    if (q) { e.preventDefault(); q.focus(); }
  });

  /* 3. In-place filtering with a live result line */
  var filters = $("[data-filters]");
  var rowsList = $("[data-rows]");
  var rows = $$("[data-row]");
  var applyFilters = null;
  if (filters && rows.length) {
    $$("[data-js-hide]").forEach(function (el) { el.hidden = true; });
    var q = $("#q");
    var sort = $("[data-sort]");
    var countLine = $("[data-count]");
    var countMarkup = countLine ? countLine.innerHTML : "";
    var emptyBlock = $("[data-empty]");
    var record = $("[data-record]");
    var recordEmpty = $("[data-record-empty]");
    var timer;
    var URG = { "Urgent": 0, "Normal": 1, "Can wait": 2 };

    function readForm() {
      var f = { q: q ? q.value.trim().toLowerCase() : "" };
      $$("[data-filter]", filters).forEach(function (s) { f[s.getAttribute("data-filter")] = s.value; });
      return f;
    }
    function matches(li, f) {
      if (f.status && li.getAttribute("data-status") !== f.status) return false;
      if (f.urgency && li.getAttribute("data-urgency") !== f.urgency) return false;
      if (f.who) {
        var who = li.getAttribute("data-who") || "";
        if (f.who === "-" ? who !== "" : who !== f.who) return false;
      }
      if (f.q) {
        var a = li.querySelector("[data-open-request]");
        var hay = (li.textContent + " " + (a ? a.getAttribute("data-by") + " " + a.getAttribute("data-device") : "")).toLowerCase();
        if (hay.indexOf(f.q) === -1) return false;
      }
      return true;
    }
    function sortRows() {
      if (!sort || !rowsList) return;
      var mode = sort.value;
      var sorted = rows.slice().sort(function (a, b) {
        var ia = +a.getAttribute("data-order"), ib = +b.getAttribute("data-order");
        if (mode === "oldest") return ib - ia;
        if (mode === "urgent") {
          var d = URG[a.getAttribute("data-urgency")] - URG[b.getAttribute("data-urgency")];
          return d || ia - ib;
        }
        return ia - ib;
      });
      sorted.forEach(function (li) { rowsList.appendChild(li); });
    }
    applyFilters = function () {
      var f = readForm();
      var n = 0;
      rows.forEach(function (li) {
        var ok = matches(li, f);
        li.hidden = !ok;
        if (ok) n++;
      });
      sortRows();
      if (countLine) {
        countLine.innerHTML = countMarkup;
        var cn = $("[data-count-n]", countLine);
        if (cn) cn.textContent = String(n);
      }
      if (emptyBlock) emptyBlock.hidden = n > 0;
      if (rowsList) rowsList.hidden = n === 0;
      if (record) record.hidden = n === 0;
      if (recordEmpty) recordEmpty.hidden = n > 0;
      announce(n === 0 ? "No requests match what you chose" : "Showing " + n + " of 8 requests");
    };
    function schedule() {
      window.clearTimeout(timer);
      if (countLine) {
        countLine.textContent = "";
        var sp = doc.createElement("span");
        sp.className = "spinner";
        sp.setAttribute("aria-hidden", "true");
        countLine.appendChild(sp);
        countLine.appendChild(doc.createTextNode(" Finding requests…"));
      }
      timer = window.setTimeout(applyFilters, 150);
    }
    filters.addEventListener("change", schedule);
    filters.addEventListener("submit", function (e) { e.preventDefault(); window.clearTimeout(timer); applyFilters(); });
    if (sort) sort.addEventListener("change", schedule);
    if (q) {
      q.addEventListener("input", schedule);
      var searchForm = q.form;
      if (searchForm) searchForm.addEventListener("submit", function (e) { e.preventDefault(); window.clearTimeout(timer); applyFilters(); });
    }
    $$("[data-clear-filters]").forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        filters.reset();
        if (q) q.value = "";
        if (sort) sort.value = "newest";
        applyFilters();
        var first = $("[data-filter]", filters);
        if (first) first.focus();
      });
    });
    // A no-script submit lands here with the choices in the URL; honour them.
    var params = new URLSearchParams(window.location.search);
    var fromUrl = false;
    ["status", "urgency", "who", "sort", "q"].forEach(function (k) {
      if (!params.has(k)) return;
      var el = k === "q" ? q : k === "sort" ? sort : $("[data-filter='" + k + "']", filters);
      if (el) { el.value = params.get(k); fromUrl = true; }
    });
    if (fromUrl) applyFilters();
  }

  /* 4. Pane swap — the record pane is filled from the row's data-* attributes */
  var panes = $("[data-pane-swap]");
  if (panes) {
    var recordPane = $("[data-record]");
    var lastRow = null;
    function setView(v) { if (v) panes.setAttribute("data-view", v); else panes.removeAttribute("data-view"); }
    function syncView(m) { setView(m.matches ? "list" : null); }
    syncView(phone);
    phone.addEventListener("change", syncView);

    function setField(name, value) {
      var el = $("[data-record-field='" + name + "']", recordPane);
      if (el) el.textContent = value;
    }
    function fill(a) {
      setField("ref", a.getAttribute("data-ref"));
      setField("title", a.getAttribute("data-title"));
      setField("by", a.getAttribute("data-by"));
      setField("device", a.getAttribute("data-device"));
      setField("who", a.getAttribute("data-who") || "Nobody yet");
      setField("raised", a.getAttribute("data-raised"));
      var where = $("[data-record-fact='where']", recordPane);
      if (where) { where.hidden = !a.hasAttribute("data-where"); setField("where", a.getAttribute("data-where") || ""); }
      var told = $("[data-record-told]", recordPane);
      if (told) { told.hidden = !a.hasAttribute("data-told"); setField("told", a.getAttribute("data-told") || ""); }
      var link = $("[data-record-device-link]", recordPane);
      if (link) link.hidden = /^Not about/.test(a.getAttribute("data-device") || "");
      ["urgency", "status"].forEach(function (slot) {
        var target = $("[data-record-slot='" + slot + "']", recordPane);
        var source = a.querySelector(slot === "urgency" ? ".chip" : ".badge");
        if (target && source) { target.textContent = ""; target.appendChild(source.cloneNode(true)); }
      });
      var crumb = $("[data-crumb-current]");
      if (crumb) crumb.textContent = a.getAttribute("data-ref");
    }
    $$("[data-open-request]").forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (!recordPane) return;
        e.preventDefault();
        lastRow = a;
        $$("[data-open-request]").forEach(function (o) { o.removeAttribute("aria-current"); });
        a.setAttribute("aria-current", "true");
        recordPane.classList.add("is-loading");
        window.setTimeout(function () {
          fill(a);
          recordPane.classList.remove("is-loading");
          if (phone.matches) { setView("record"); window.scrollTo(0, 0); }
          var h = $("[data-record-field='title']", recordPane);
          if (h) h.focus();
          announce("Showing " + a.getAttribute("data-ref"));
        }, 140);
      });
    });
    $$("[data-back]").forEach(function (b) {
      b.addEventListener("click", function (e) {
        e.preventDefault();
        setView("list");
        (lastRow || $("[data-open-request]")).focus();
      });
    });
  }

  /* 5. Disclosures that start closed on a phone */
  if (phone.matches) {
    $$("[data-phone-closed]").forEach(function (d) { d.removeAttribute("open"); });
  }

  /* 6. Confirm dialog — modal with script, inline section without */
  $$("dialog[data-dialog]").forEach(function (d) {
    d.removeAttribute("open");
    var opener = null;
    $$("[data-dialog-open='" + d.id + "']").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        opener = btn;
        d.showModal();
        var first = d.querySelector("button, [href], input:not([type=hidden])");
        if (first) first.focus();
      });
    });
    d.addEventListener("close", function () { if (opener) opener.focus(); });
    d.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      var f = $$("button, [href], input:not([type=hidden]), select, textarea", d).filter(function (el) { return !el.disabled; });
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    var form = $("[data-return-form]", d);
    if (form) {
      form.addEventListener("submit", function (e) {
        if (e.submitter && e.submitter.getAttribute("formmethod") === "dialog") return;
        e.preventDefault();
        d.close();
        var al = $("[data-returned-alert]");
        if (al) al.hidden = false;
        toast("IT-0142 is back in the ICT Store.");
        announce("IT-0142 is back in the ICT Store.");
      });
    }
  });

  /* 7. Error-summary links move focus to the field */
  $$("[data-focus-field]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      var target = $(a.getAttribute("href"));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ block: "center" });
      target.focus();
    });
  });

  /* 8. Section index — mark the item you chose */
  $$("[data-index]").forEach(function (list) {
    $$("a", list).forEach(function (a) {
      a.addEventListener("click", function () {
        $$("a", list).forEach(function (o) { o.removeAttribute("aria-current"); });
        a.setAttribute("aria-current", "true");
      });
    });
  });

  /* 9. Busy buttons — label swaps, width holds, aria-busy set */
  $$("form[data-busy]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var buttons = $$("[data-busy-label]").filter(function (b) { return b.form === form; });
      buttons.forEach(function (b) {
        b.style.width = b.getBoundingClientRect().width + "px";
        b.setAttribute("aria-busy", "true");
        b.textContent = "";
        var sp = doc.createElement("span");
        sp.className = "spinner";
        sp.setAttribute("aria-hidden", "true");
        b.appendChild(sp);
        b.appendChild(doc.createTextNode(b.getAttribute("data-busy-label")));
      });
    });
  });

  /* 10. ?demo= — prototype-only state switching. Never ported to templates. */
  var demo = new URLSearchParams(window.location.search).get("demo") || "";
  if (demo) {
    $$("[data-demo-show]").forEach(function (el) {
      if (el.getAttribute("data-demo-show").split(" ").indexOf(demo) > -1) el.hidden = false;
    });
    $$("[data-demo-hide]").forEach(function (el) {
      if (el.getAttribute("data-demo-hide").split(" ").indexOf(demo) > -1) el.hidden = true;
    });
    var focusTarget = null;
    $$("[data-demo-state]").forEach(function (el) {
      if (el.getAttribute("data-demo-state") !== demo) return;
      if (el.hasAttribute("data-demo-value")) el.value = el.getAttribute("data-demo-value");
      if (el.hasAttribute("data-demo-checked")) el.checked = true;
      if (el.hasAttribute("data-demo-invalid")) el.setAttribute("aria-invalid", "true");
      /* The error id joins aria-describedby only now: a hidden error referenced all the time is still read as the field's description. */
      if (el.hasAttribute("data-demo-describedby")) el.setAttribute("aria-describedby", ((el.getAttribute("aria-describedby") || "") + " " + el.getAttribute("data-demo-describedby")).trim());
      if (el.hasAttribute("data-demo-focus")) focusTarget = el;
    });
    if (demo === "empty" && applyFilters) {
      var st = $("[data-filter='status']"), who = $("[data-filter='who']");
      if (st) st.value = "Waiting on someone";
      if (who) who.value = "Ruwan Jayasuriya";
      applyFilters();
    }
    if (demo === "toast") {
      toast("Request sent. We gave it the number REQ-2049.", {
        undo: function () { $$("[data-demo-show~='toast']").forEach(function (el) { el.hidden = true; }); }
      });
    }
    if (demo === "returned") toast("IT-0142 is back in the ICT Store.");
    var summary = $("[data-error-summary]");
    if (summary && !summary.hidden) summary.focus();
    else if (focusTarget) focusTarget.focus();
  }

  /* 11. Account menu — a native <details> that opens and closes without script; this only adds the ways people expect a menu to close */
  $$("[data-utility]").forEach(function (d) {
    var toggle = $("summary", d);
    d.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && d.open) { d.open = false; if (toggle) toggle.focus(); }
    });
    doc.addEventListener("click", function (e) {
      if (d.open && !d.contains(e.target)) d.open = false;
    });
    d.addEventListener("focusout", function (e) {
      if (d.open && e.relatedTarget && !d.contains(e.relatedTarget)) d.open = false;
    });
  });
})();
