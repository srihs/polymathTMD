/* Polymath College · Technology Management Desk — direction A "Ledger" — app.js
 *
 * One IIFE of progressive enhancements. Every hook is a data-* attribute, never
 * a class or a DOM position. Every page works with this file missing: forms
 * submit, links navigate, <details> opens, the confirm step is a section at the
 * foot of device.html. Nothing here is a framework, a build step or a CDN script.
 *
 * Blocks
 *   0  setup: mark the document as scripted, read ?demo=
 *   1  icons: clone a glyph from the page's <symbol> sprite
 *   2  toast: render, pause on hover/focus, auto-dismiss after 8 s
 *   3  demo states (prototype-only; never ported into templates)
 *   4  requests queue: filter and sort in place with a live result line
 *   5  search box clear button
 *   6  error summary: links move focus to the field
 *   7  dialog: open, focus title, trap Tab, return focus, toast on confirm
 *   8  phone: collapse the filter disclosure so the list is above the fold
 */
(function () {
  'use strict';

  /* 0 — setup ---------------------------------------------------------- */
  var doc = document;
  var root = doc.documentElement;
  root.setAttribute('data-js', '');

  var params = new URLSearchParams(window.location.search);
  var demo = params.get('demo');
  var phone = window.matchMedia('(max-width: 1023px)');
  var SVG_NS = 'http://www.w3.org/2000/svg';

  function all(selector, scope) {
    return Array.prototype.slice.call((scope || doc).querySelectorAll(selector));
  }

  /* 1 — icons ------------------------------------------------------------ */
  function icon(name, extraClass) {
    var svg = doc.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'icon' + (extraClass ? ' ' + extraClass : ''));
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.setAttribute('fill', 'currentColor');
    var use = doc.createElementNS(SVG_NS, 'use');
    use.setAttribute('href', '#' + name);
    svg.appendChild(use);
    return svg;
  }

  /* 2 — toast ------------------------------------------------------------- */
  var TOAST_MS = 8000;
  var TOAST_OUT_MS = 120;

  function toast(text, options) {
    var region = doc.querySelector('[data-toast-region]');
    if (!region) { return; }
    options = options || {};

    var el = doc.createElement('div');
    el.className = 'toast';
    el.setAttribute('role', 'status');
    el.appendChild(icon('i-check'));

    var span = doc.createElement('span');
    span.className = 'toast-text';
    span.textContent = text;
    el.appendChild(span);

    if (options.undo) {
      var undo = doc.createElement('button');
      undo.type = 'button';
      undo.className = 'btn btn-quiet';
      undo.appendChild(icon('i-undo'));
      undo.appendChild(doc.createTextNode('Undo'));
      undo.addEventListener('click', function () { dismiss(); });
      el.appendChild(undo);
    }

    var close = doc.createElement('button');
    close.type = 'button';
    close.className = 'btn btn-quiet btn-icon';
    close.setAttribute('aria-label', 'Close this message');
    close.title = 'Close this message';
    close.appendChild(icon('i-close'));
    close.addEventListener('click', function () { dismiss(); });
    el.appendChild(close);

    var timer = null;
    function arm() { clearTimeout(timer); timer = setTimeout(dismiss, TOAST_MS); }
    function pause() { clearTimeout(timer); }
    function dismiss() {
      clearTimeout(timer);
      el.classList.add('is-leaving');
      setTimeout(function () { if (el.parentNode) { el.parentNode.removeChild(el); } }, TOAST_OUT_MS);
    }
    el.addEventListener('mouseenter', pause);
    el.addEventListener('mouseleave', arm);
    el.addEventListener('focusin', pause);
    el.addEventListener('focusout', arm);

    region.appendChild(el);
    arm();
    return el;
  }

  /* 3 — demo states --------------------------------------------------------- */
  if (demo) {
    all('[data-demo="' + demo + '"]').forEach(function (el) { el.hidden = false; });
    all('[data-demo-hide="' + demo + '"]').forEach(function (el) { el.setAttribute('data-demo-hidden', ''); });
  }

  function describe(field, id) {
    var ids = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
    if (ids.indexOf(id) === -1) { ids.push(id); }
    field.setAttribute('aria-describedby', ids.join(' '));
  }

  if (demo === 'error' || demo === 'errors') {
    // keep everything the person typed
    all('[data-demo-value]').forEach(function (field) { field.value = field.getAttribute('data-demo-value'); });
    all('[data-demo-checked]').forEach(function (field) { field.checked = true; });
    // mark only the fields that failed
    all('[data-demo-invalid]').forEach(function (field) {
      field.setAttribute('aria-invalid', 'true');
      describe(field, field.getAttribute('data-demo-invalid'));
    });
    var summary = doc.querySelector('[data-error-summary]');
    var focusTarget = doc.querySelector('[data-demo-focus]');
    if (summary) { summary.focus(); }
    else if (focusTarget) { focusTarget.value = ''; focusTarget.focus(); }
  }

  if (demo === 'toast') {
    toast('Request sent. We gave it the number REQ-2049.', { undo: true });
    var h1 = doc.querySelector('h1');
    if (h1) { h1.setAttribute('tabindex', '-1'); h1.focus({ preventScroll: true }); }
  }

  if (demo === 'returned') {
    toast('IT-0142 is back in the ICT Store.');
  }

  /* 4 — requests queue: filter and sort in place ------------------------------ */
  var filterForm = doc.querySelector('[data-filter-form]');
  var queueBody = doc.querySelector('[data-queue-body]');
  if (filterForm && queueBody) {
    var rows = all('tr', queueBody);
    var total = rows.length;
    var resultLine = doc.querySelector('[data-result-line]');
    var queueWrap = doc.querySelector('[data-queue-wrap]');
    var queueEmpty = doc.querySelector('[data-queue-empty]');
    var queuePages = doc.querySelector('[data-queue-pages]');
    var searchBox = doc.querySelector('[data-filter-search]');
    var sortBox = doc.querySelector('[data-filter-sort]');
    var keyed = all('[data-filter-key]', filterForm);
    var sortCols = all('[data-sort-col]');
    var pending = null;
    var WAIT_MS = 250;

    function setResult(count) {
      if (!resultLine) { return; }
      resultLine.textContent = '';
      resultLine.appendChild(doc.createTextNode('Showing '));
      var strong = doc.createElement('strong');
      strong.setAttribute('data-result-count', '');
      strong.textContent = String(count);
      resultLine.appendChild(strong);
      resultLine.appendChild(doc.createTextNode(' of ' + total + ' requests'));
    }

    function setWaiting() {
      if (!resultLine) { return; }
      resultLine.textContent = '';
      var spin = doc.createElement('span');
      spin.className = 'spinner';
      spin.setAttribute('aria-hidden', 'true');
      resultLine.appendChild(spin);
      resultLine.appendChild(doc.createTextNode('Finding requests…'));
    }

    function apply() {
      var q = searchBox ? searchBox.value.trim().toLowerCase() : '';
      var wants = {};
      keyed.forEach(function (select) { wants[select.getAttribute('data-filter-key')] = select.value; });

      var shown = 0;
      rows.forEach(function (row) {
        var ok = true;
        Object.keys(wants).forEach(function (key) {
          if (wants[key] && row.getAttribute('data-' + key) !== wants[key]) { ok = false; }
        });
        if (ok && q) {
          var hay = (row.textContent + ' ' + (row.getAttribute('data-device') || '')).toLowerCase();
          if (hay.indexOf(q) === -1) { ok = false; }
        }
        row.hidden = !ok;
        if (ok) { shown++; }
      });

      if (sortBox) {
        var mode = sortBox.value;
        var sorted = rows.slice().sort(function (a, b) {
          var ra = a.getAttribute('data-raised'), rb = b.getAttribute('data-raised');
          if (mode === 'oldest') { return ra < rb ? -1 : ra > rb ? 1 : 0; }
          if (mode === 'urgent') {
            var d = Number(a.getAttribute('data-rank')) - Number(b.getAttribute('data-rank'));
            if (d !== 0) { return d; }
          }
          return ra > rb ? -1 : ra < rb ? 1 : 0;
        });
        sorted.forEach(function (row) { queueBody.appendChild(row); });
        sortCols.forEach(function (th) {
          var col = th.getAttribute('data-sort-col');
          if (col === 'raised' && mode !== 'urgent') { th.setAttribute('aria-sort', mode === 'oldest' ? 'ascending' : 'descending'); }
          else if (col === 'urgent' && mode === 'urgent') { th.setAttribute('aria-sort', 'descending'); }
          else { th.removeAttribute('aria-sort'); }
        });
      }

      var empty = shown === 0;
      if (queueWrap) { queueWrap.hidden = empty; }
      if (queuePages) { queuePages.hidden = empty; }
      if (queueEmpty) { queueEmpty.hidden = !empty; }
      setResult(shown);
    }

    function schedule() {
      clearTimeout(pending);
      setWaiting();
      pending = setTimeout(apply, WAIT_MS);
    }

    filterForm.addEventListener('submit', function (event) { event.preventDefault(); clearTimeout(pending); apply(); });
    filterForm.addEventListener('input', schedule);
    filterForm.addEventListener('change', schedule);

    if (demo === 'empty') {
      if (queueWrap) { queueWrap.hidden = true; }
      if (queuePages) { queuePages.hidden = true; }
      if (searchBox) { searchBox.value = 'visualiser'; }
      setResult(0);
    }

    /* 5 — search box clear ------------------------------------------------ */
    var clearButton = doc.querySelector('[data-filter-clear]');
    if (clearButton && searchBox) {
      clearButton.addEventListener('click', function () {
        searchBox.value = '';
        searchBox.focus();
        schedule();
      });
    }
  }

  /* 6 — error summary links move focus to the field ------------------------- */
  all('[data-focus-field]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      var target = doc.getElementById(link.getAttribute('href').slice(1));
      if (target) {
        event.preventDefault();
        target.scrollIntoView({ block: 'center' });
        target.focus();
      }
    });
  });

  /* busy button: lock width, swap label, mark busy (a real send would reset it) */
  var requestForm = doc.querySelector('[data-request-form]');
  if (requestForm) {
    requestForm.addEventListener('submit', function () {
      var button = requestForm.querySelector('[data-busy-label]');
      if (!button) { return; }
      button.style.minWidth = button.offsetWidth + 'px';
      button.setAttribute('aria-busy', 'true');
      button.textContent = '';
      var spin = doc.createElement('span');
      spin.className = 'spinner';
      spin.setAttribute('aria-hidden', 'true');
      button.appendChild(spin);
      button.appendChild(doc.createTextNode(button.getAttribute('data-busy-label')));
    });
  }

  /* 7 — dialog ------------------------------------------------------------------ */
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  all('[data-dialog-open]').forEach(function (opener) {
    var dialog = doc.getElementById(opener.getAttribute('data-dialog-open'));
    if (!dialog || typeof dialog.showModal !== 'function') { return; }

    opener.addEventListener('click', function (event) {
      event.preventDefault();
      dialog.showModal();
      var title = dialog.querySelector('h2');
      if (title) { title.focus(); }
    });

    dialog.addEventListener('keydown', function (event) {
      if (event.key !== 'Tab') { return; }
      var items = all(FOCUSABLE, dialog);
      if (!items.length) { return; }
      var first = items[0], last = items[items.length - 1];
      if (event.shiftKey && (doc.activeElement === first || doc.activeElement === dialog.querySelector('h2'))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && doc.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });

    dialog.addEventListener('close', function () {
      opener.focus();
      if (dialog.returnValue === 'confirm') {
        toast('IT-0142 is back in the ICT Store.');
      }
      dialog.returnValue = '';
    });
  });

  /* 8 — phone: collapse the filter disclosure ------------------------------------ */
  all('[data-filters-more]').forEach(function (details) {
    if (phone.matches) { details.open = false; }
  });
}());
