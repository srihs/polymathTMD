/*
  Polymath TMD — Direction B "Parchment" — progressive enhancements.

  One IIFE. Binds only through data-* attributes, never classes or DOM
  shape. Every page works with this file absent: the phone menu and the
  filter panel are native <details>, the filter form submits with its own
  Apply button, the confirm dialog falls back to a section at the foot of
  the page, and every form is a real <form>.

  Blocks:
    1. helpers and the icon cloner
    2. toasts (role="status", 8 s, pauses on hover and focus, Undo, Close)
    3. phone menu: close after a link inside it is followed
    4. request queue: in-place filter and sort with a live result line
    5. confirm dialog: <dialog>, focus trap, Escape, focus return
    6. busy button on submit
    7. ?demo= state hooks (prototype only, never ported)
    8. error summary: focus on load, links move focus into the field
*/
(function () {
  'use strict';

  /* ---------------------------------------------------------------------
     1. Helpers
     --------------------------------------------------------------------- */
  var doc = document;
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var XLINK_NS = 'http://www.w3.org/1999/xlink';
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var OUT_MS = reduceMotion ? 0 : 180;
  var TOAST_MS = 8000;

  function qs(sel, root) { return (root || doc).querySelector(sel); }
  function qsa(sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); }
  function focusables(root) {
    return qsa('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])', root)
      .filter(function (el) { return el.offsetParent !== null || el === doc.activeElement; });
  }

  /* Clone an icon from the page's inline sprite (<symbol id="i-name">). */
  function icon(name, className) {
    var svg = doc.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', className || 'icon');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    var use = doc.createElementNS(SVG_NS, 'use');
    use.setAttribute('href', '#i-' + name);
    use.setAttributeNS(XLINK_NS, 'xlink:href', '#i-' + name);
    svg.appendChild(use);
    return svg;
  }

  function el(tag, className, text) {
    var node = doc.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  /* ---------------------------------------------------------------------
     2. Toasts
     --------------------------------------------------------------------- */
  var toastRegion = qs('[data-toast-region]');

  function showToast(text, options) {
    if (!toastRegion) return;
    var opts = options || {};
    var toast = el('div', 'toast');
    toast.setAttribute('role', 'status');
    toast.appendChild(icon('check-circle', 'icon toast__icon'));
    toast.appendChild(el('p', 'toast__text', text));

    var timer = null;
    function dismiss() {
      window.clearTimeout(timer);
      toast.classList.remove('is-in');
      toast.classList.add('is-out');
      window.setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, OUT_MS);
    }
    function start() { window.clearTimeout(timer); timer = window.setTimeout(dismiss, TOAST_MS); }
    function pause() { window.clearTimeout(timer); }

    if (opts.undo) {
      var undo = el('button', 'btn btn--toast', 'Undo');
      undo.type = 'button';
      undo.addEventListener('click', function () {
        dismiss();
        if (typeof opts.onUndo === 'function') opts.onUndo();
      });
      toast.appendChild(undo);
    }
    var close = el('button', 'btn btn--icon');
    close.type = 'button';
    close.setAttribute('aria-label', 'Close');
    close.appendChild(icon('close-circle', 'icon'));
    close.addEventListener('click', dismiss);
    toast.appendChild(close);

    toast.addEventListener('mouseenter', pause);
    toast.addEventListener('mouseleave', start);
    toast.addEventListener('focusin', pause);
    toast.addEventListener('focusout', start);

    toastRegion.appendChild(toast);
    window.requestAnimationFrame(function () { toast.classList.add('is-in'); });
    start();
    return toast;
  }

  qsa('[data-toast-trigger]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      showToast(btn.getAttribute('data-toast-text') || '', { undo: btn.hasAttribute('data-toast-undo') });
    });
  });

  /* ---------------------------------------------------------------------
     3. Phone menu: close after following a link inside it
     --------------------------------------------------------------------- */
  qsa('[data-menu]').forEach(function (menu) {
    menu.addEventListener('click', function (event) {
      var link = event.target.closest && event.target.closest('a[href]');
      if (link && menu.contains(link)) menu.removeAttribute('open');
    });
  });

  /* ---------------------------------------------------------------------
     4. Request queue: in-place filter and sort
     --------------------------------------------------------------------- */
  var filterForm = qs('[data-filter-form]');
  var filterList = qs('[data-filter-list]');
  var resultLine = qs('[data-result-line]');
  var emptyState = qs('[data-empty-state]');
  var pagination = qs('[data-pagination]');
  /* 'Most urgent first' lifts only the Urgent rows; everything else keeps the newest-first order. */
  var URGENCY_RANK = { 'Urgent': 1 };

  function setResultLine(shown, total) {
    if (!resultLine) return;
    resultLine.textContent = 'Showing ' + shown + ' of ' + total + ' requests';
  }

  if (filterForm && filterList && resultLine) {
    var items = qsa('[data-filter-item]', filterList);
    var total = items.length;
    var searchBox = qs('[data-filter-search]', filterForm);
    var statusBox = qs('[data-filter-status]', filterForm);
    var urgencyBox = qs('[data-filter-urgency]', filterForm);
    var assigneeBox = qs('[data-filter-assignee]', filterForm);
    var sortBox = qs('[data-filter-sort]', filterForm);
    var applyButton = qs('[data-filter-apply]', filterForm);
    var pending = null;

    /* The Apply button is only needed without scripting. */
    if (applyButton) applyButton.hidden = true;

    function runFilter() {
      var q = searchBox ? searchBox.value.trim().toLowerCase() : '';
      var status = statusBox ? statusBox.value : '';
      var urgency = urgencyBox ? urgencyBox.value : '';
      var who = assigneeBox ? assigneeBox.value : '';
      var sort = sortBox ? sortBox.value : 'newest';
      var shown = 0;

      items.forEach(function (item) {
        var ok = true;
        if (status && item.getAttribute('data-status') !== status) ok = false;
        if (urgency && item.getAttribute('data-urgency') !== urgency) ok = false;
        if (who === 'nobody') {
          if (item.getAttribute('data-assignee')) ok = false;
        } else if (who && item.getAttribute('data-assignee') !== who) {
          ok = false;
        }
        if (q && item.textContent.toLowerCase().indexOf(q) === -1) ok = false;
        item.hidden = !ok;
        if (ok) shown += 1;
      });

      var sorted = items.slice().sort(function (a, b) {
        var ra = a.getAttribute('data-raised') || '';
        var rb = b.getAttribute('data-raised') || '';
        if (sort === 'oldest') return ra < rb ? -1 : ra > rb ? 1 : 0;
        if (sort === 'urgent') {
          var ua = URGENCY_RANK[a.getAttribute('data-urgency')] || 0;
          var ub = URGENCY_RANK[b.getAttribute('data-urgency')] || 0;
          if (ua !== ub) return ub - ua;
        }
        return ra > rb ? -1 : ra < rb ? 1 : 0;
      });
      sorted.forEach(function (item) { filterList.appendChild(item); });

      setResultLine(shown, total);
      filterList.hidden = shown === 0;
      if (emptyState) emptyState.hidden = shown > 0;
      if (pagination) pagination.hidden = shown === 0;
    }

    /* Show the wait line briefly so the change is announced, then filter. */
    function scheduleFilter() {
      window.clearTimeout(pending);
      resultLine.textContent = '';
      resultLine.appendChild(icon('refresh-circle', 'icon icon--sm spin'));
      resultLine.appendChild(doc.createTextNode('Finding requests…'));
      pending = window.setTimeout(runFilter, 250);
    }

    filterForm.addEventListener('input', scheduleFilter);
    filterForm.addEventListener('change', scheduleFilter);
    filterForm.addEventListener('submit', function (event) { event.preventDefault(); runFilter(); });

    qsa('[data-filter-clear]').forEach(function (clear) {
      clear.addEventListener('click', function (event) {
        event.preventDefault();
        filterForm.reset();
        runFilter();
        if (searchBox) searchBox.focus();
      });
    });
  }

  /* ---------------------------------------------------------------------
     5. Confirm dialog
     --------------------------------------------------------------------- */
  qsa('[data-dialog-open]').forEach(function (opener) {
    var dialog = doc.getElementById(opener.getAttribute('data-dialog-open'));
    if (!dialog || typeof dialog.showModal !== 'function') return;

    /* The no-JavaScript fallback section is not needed once we can open a dialog. */
    qsa('[data-dialog-fallback="' + dialog.id + '"]').forEach(function (section) { section.hidden = true; });

    opener.addEventListener('click', function (event) {
      event.preventDefault();
      dialog.showModal();
      var first = qs('[data-dialog-confirm]', dialog) || focusables(dialog)[0];
      if (first) first.focus();
    });

    dialog.addEventListener('close', function () { opener.focus(); });

    qsa('[data-dialog-close]', dialog).forEach(function (btn) {
      btn.addEventListener('click', function () { dialog.close(); });
    });

    /* Keep Tab inside the dialog while it is open. */
    dialog.addEventListener('keydown', function (event) {
      if (event.key !== 'Tab') return;
      var list = focusables(dialog);
      if (!list.length) return;
      var first = list[0];
      var last = list[list.length - 1];
      if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first.focus(); }
    });

    /* A click on the backdrop closes, as Escape does. */
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) dialog.close();
    });

    var confirm = qs('[data-dialog-confirm]', dialog);
    if (confirm) {
      confirm.addEventListener('click', function (event) {
        event.preventDefault();
        dialog.close();
        showToast(confirm.getAttribute('data-toast-text') || '', { undo: true });
      });
    }
  });

  /* ---------------------------------------------------------------------
     6. Busy button on submit: label, spinner, aria-busy, locked width
     --------------------------------------------------------------------- */
  qsa('[data-busy-form]').forEach(function (form) {
    form.addEventListener('submit', function () {
      var button = qs('[data-busy-label]', form);
      if (!button) return;
      button.style.minWidth = button.offsetWidth + 'px';
      button.setAttribute('aria-busy', 'true');
      button.textContent = '';
      button.appendChild(icon('refresh-circle', 'icon icon--sm spin'));
      button.appendChild(doc.createTextNode(button.getAttribute('data-busy-label')));
    });
  });

  /* ---------------------------------------------------------------------
     7. ?demo= state hooks — prototype only
        error · errors · empty · toast · denied
     --------------------------------------------------------------------- */
  var demo = null;
  try { demo = new URLSearchParams(window.location.search).get('demo'); } catch (err) { demo = null; }

  if (demo) {
    doc.body.setAttribute('data-demo-state', demo);

    qsa('[data-demo="' + demo + '"]').forEach(function (node) { node.hidden = false; });
    qsa('[data-demo-hide="' + demo + '"]').forEach(function (node) { node.hidden = true; });
    qsa('[data-demo-fill="' + demo + '"]').forEach(function (field) {
      field.value = field.getAttribute('data-demo-value') || '';
    });
    qsa('[data-demo-check="' + demo + '"]').forEach(function (field) { field.checked = true; });

    /* A failed field: aria-invalid, its error message shown and linked after the help text. */
    qsa('[data-demo-invalid="' + demo + '"]').forEach(function (field) {
      field.setAttribute('aria-invalid', 'true');
      var errorId = field.getAttribute('data-error-id');
      if (!errorId) return;
      var ids = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
      if (ids.indexOf(errorId) === -1) ids.push(errorId);
      field.setAttribute('aria-describedby', ids.join(' '));
      var message = doc.getElementById(errorId);
      if (message) message.hidden = false;
    });

    if (demo === 'toast') {
      showToast('Request sent. We gave it the number REQ-2049.', { undo: true });
      var h1 = qs('h1');
      if (h1) { h1.setAttribute('tabindex', '-1'); h1.focus(); }
    }

    if (demo === 'empty') {
      if (filterList) filterList.hidden = true;
      if (pagination) pagination.hidden = true;
      if (emptyState) emptyState.hidden = false;
      setResultLine(0, filterList ? qsa('[data-filter-item]', filterList).length : 0);
    }

    if (demo === 'denied') {
      var main = qs('main');
      var card = qs('[data-denied]');
      var heading = qs('h1');
      if (main && card && heading) {
        Array.prototype.forEach.call(main.children, function (child) {
          if (child !== card) child.hidden = true;
        });
        heading.textContent = "You can't open this page";
        heading.hidden = false;
        card.insertBefore(heading, card.firstElementChild ? card.firstElementChild.nextSibling : null);
        card.hidden = false;
        heading.setAttribute('tabindex', '-1');
        heading.focus();
      }
    }

    var focusTarget = qs('[data-demo-focus="' + demo + '"]');
    if (focusTarget && demo !== 'errors') focusTarget.focus();
  }

  /* ---------------------------------------------------------------------
     8. Error summary: focus it on load, and its links move focus into fields
     --------------------------------------------------------------------- */
  qsa('[data-error-summary]').forEach(function (summary) {
    qsa('a[href^="#"]', summary).forEach(function (link) {
      link.addEventListener('click', function (event) {
        var target = doc.getElementById(link.getAttribute('href').slice(1));
        if (!target) return;
        event.preventDefault();
        target.focus();
        if (target.scrollIntoView) target.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
      });
    });
    if (!summary.hidden) summary.focus();
  });
})();
