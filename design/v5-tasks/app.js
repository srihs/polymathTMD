/* Polymath Inventory — v5 "Tasks First" — shared behaviour (vanilla JS, no build step).
   Every page works without this file; it adds dialogs, toasts, the drawer, live filters,
   the quantity stepper, form checks and the dashboard chart. */
(function () {
  'use strict';

  document.documentElement.classList.add('js');
  var qs = function (s, r) { return (r || document).querySelector(s); };
  var qsa = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var params = new URLSearchParams(location.search);
  var demo = params.get('demo');
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function iconEl(name) {
    var tpl = qs('#tpl-icons');
    if (!tpl) return document.createElement('span');
    var holder = tpl.content.querySelector('[data-icon="' + name + '"] svg');
    return holder ? holder.cloneNode(true) : document.createElement('span');
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function fmt(n) { return Number(n).toLocaleString('en-US'); }
  function money(n) { return 'Rs ' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  /* ------------------------------------------------------------------ Toasts */
  var TOAST_MS = 6000;
  function showToast(opts) {
    var box = qs('#toasts');
    if (!box) return;
    var type = opts.type || 'success';
    var t = el('div', 'toast toast-' + type);
    if (type === 'error') t.setAttribute('role', 'alert');
    var iconName = { success: 'ok', info: 'info', warning: 'warn', error: 'error' }[type];
    t.appendChild(iconEl(iconName));
    var body = el('div');
    body.appendChild(el('p', 'toast-title', opts.title));
    if (opts.text) body.appendChild(el('p', 'toast-text', opts.text));
    if (opts.undo) {
      var acts = el('div', 'toast-actions');
      var u = el('button', 'btn btn-secondary btn-sm');
      u.type = 'button';
      u.appendChild(iconEl('undo'));
      u.appendChild(document.createTextNode('Undo'));
      u.addEventListener('click', function () { opts.undo(); dismiss(); });
      acts.appendChild(u);
      body.appendChild(acts);
    }
    t.appendChild(body);
    var close = el('button', 'btn btn-ghost btn-icon btn-sm toast-close');
    close.type = 'button';
    close.setAttribute('aria-label', 'Close message');
    close.appendChild(iconEl('close'));
    close.addEventListener('click', dismiss);
    t.appendChild(close);
    var timer = el('div', 'toast-timer');
    var bar = el('span');
    bar.style.animationDuration = TOAST_MS + 'ms';
    timer.appendChild(bar);
    t.appendChild(timer);
    box.appendChild(t);

    var remaining = TOAST_MS, started = Date.now(), handle = null;
    function start() { started = Date.now(); handle = setTimeout(dismiss, remaining); }
    function pause() { clearTimeout(handle); remaining -= Date.now() - started; }
    t.addEventListener('mouseenter', pause);
    t.addEventListener('mouseleave', start);
    t.addEventListener('focusin', pause);
    t.addEventListener('focusout', function (e) { if (!t.contains(e.relatedTarget)) start(); });
    if (!opts.sticky) start();
    function dismiss() {
      clearTimeout(handle);
      if (!t.isConnected) return;
      t.classList.add('is-leaving');
      setTimeout(function () { t.remove(); }, 200);
    }
    return t;
  }
  window.showToast = showToast;

  /* ------------------------------------------------------------------ Modals */
  var openState = null;
  function openModal(id, trigger) {
    var bd = document.getElementById(id);
    if (!bd) return;
    if (openState) closeModal();
    bd.hidden = false;
    document.body.classList.add('has-modal');
    var dialog = qs('[role="dialog"]', bd);
    openState = { bd: bd, dialog: dialog, trigger: trigger || document.activeElement };
    // Start on the first thing to fill in; otherwise the first button in the footer (never the X).
    var first = qs('.modal-body input, .modal-body select, .modal-body textarea', dialog) ||
      qs('.modal-foot button', dialog) || qs(FOCUSABLE, dialog);
    setTimeout(function () { (first || dialog).focus(); }, 30);
  }
  function closeModal() {
    if (!openState) return;
    var s = openState;
    openState = null;
    s.bd.hidden = true;
    document.body.classList.remove('has-modal');
    if (s.trigger && s.trigger.focus) s.trigger.focus();
  }
  window.openModal = openModal;
  window.closeModal = closeModal;

  document.addEventListener('click', function (e) {
    var o = e.target.closest('[data-modal-open]');
    if (o) { e.preventDefault(); openModal(o.getAttribute('data-modal-open'), o); return; }
    var c = e.target.closest('[data-modal-close]');
    if (c && openState) {
      var after = c.getAttribute('data-toast-after');
      closeModal();
      if (after) showToast({ type: after, title: 'You left the form', text: 'Nothing was saved. Your draft was not kept.' });
      return;
    }
    if (openState && e.target === openState.bd) closeModal();
  });
  document.addEventListener('keydown', function (e) {
    if (!openState) return;
    if (e.key === 'Escape') { e.preventDefault(); closeModal(); return; }
    if (e.key === 'Tab') {
      var f = qsa(FOCUSABLE, openState.dialog).filter(function (n) { return n.offsetParent !== null; });
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  /* ------------------------------------------------------------------ Drawer (phone nav) */
  var sidebar = qs('#sidebar');
  var toggles = qsa('[data-drawer-toggle]');
  var drawerBackdrop = null, drawerTrigger = null;
  function drawerOpen(trigger) {
    if (!sidebar) return;
    drawerTrigger = trigger || null;
    sidebar.classList.add('is-open');
    toggles.forEach(function (t) { t.setAttribute('aria-expanded', 'true'); });
    drawerBackdrop = el('div', 'drawer-backdrop');
    drawerBackdrop.addEventListener('click', drawerClose);
    document.body.appendChild(drawerBackdrop);
    var f = qs('[data-drawer-close]', sidebar) || qs(FOCUSABLE, sidebar);
    setTimeout(function () { if (f) f.focus(); }, 60);
  }
  function drawerClose() {
    if (!sidebar || !sidebar.classList.contains('is-open')) return;
    sidebar.classList.remove('is-open');
    toggles.forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
    if (drawerBackdrop) { drawerBackdrop.remove(); drawerBackdrop = null; }
    if (drawerTrigger) drawerTrigger.focus();
  }
  toggles.forEach(function (t) {
    t.addEventListener('click', function () {
      sidebar.classList.contains('is-open') ? drawerClose() : drawerOpen(t);
    });
  });
  qsa('[data-drawer-close]').forEach(function (b) { b.addEventListener('click', drawerClose); });
  if (sidebar) {
    sidebar.addEventListener('click', function (e) { if (e.target.closest('a')) drawerClose(); });
    sidebar.addEventListener('keydown', function (e) {
      if (!sidebar.classList.contains('is-open')) return;
      if (e.key === 'Escape') { drawerClose(); return; }
      if (e.key === 'Tab') {
        var f = qsa(FOCUSABLE, sidebar);
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  /* ------------------------------------------------------------------ Dismissable boxes */
  qsa('[data-dismiss]').forEach(function (b) {
    b.addEventListener('click', function () {
      var box = b.closest('[data-dismiss-box], .alert');
      if (box) box.hidden = true;
    });
  });

  /* ------------------------------------------------------------------ Row menus */
  function closeMenus(except) {
    qsa('[data-menu][aria-expanded="true"]').forEach(function (b) {
      if (b === except) return;
      b.setAttribute('aria-expanded', 'false');
      b.nextElementSibling.hidden = true;
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-menu]');
    if (b) {
      var list = b.nextElementSibling;
      var open = b.getAttribute('aria-expanded') === 'true';
      closeMenus(b);
      b.setAttribute('aria-expanded', open ? 'false' : 'true');
      list.hidden = open;
      if (!open) { var f = qs('.menu-item', list); if (f) f.focus(); }
      return;
    }
    if (!e.target.closest('.menu-list')) closeMenus();
  });
  document.addEventListener('keydown', function (e) {
    var list = e.target.closest && e.target.closest('.menu-list');
    if (!list) return;
    var items = qsa('.menu-item', list), i = items.indexOf(e.target);
    if (e.key === 'Escape') { var btn = list.previousElementSibling; closeMenus(); btn.focus(); }
    if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
  });

  /* ------------------------------------------------------------------ Quantity stepper */
  function stepperValue(input) { var v = parseInt(input.value, 10); return isNaN(v) ? 0 : v; }
  function updateTotal(qty) {
    var form = qty.closest('form');
    if (!form || !form.hasAttribute('data-stock-form')) return;
    var out = qs('[data-new-total]', form);
    if (!out) return;
    var cur = parseInt(form.getAttribute('data-current'), 10) || 0;
    var v = stepperValue(qs('input', qty));
    var total = form.getAttribute('data-stock-form') === 'give' ? cur - v : cur + v;
    out.textContent = fmt(Math.max(total, 0)) + ' ' + form.getAttribute('data-unit');
  }
  qsa('.qty[data-qty]').forEach(function (qty) {
    var input = qs('input', qty);
    if (!input) return;
    var allowNeg = qty.hasAttribute('data-allow-negative');
    qsa('[data-step]', qty).forEach(function (b) {
      b.addEventListener('click', function () {
        var v = stepperValue(input) + parseInt(b.getAttribute('data-step'), 10);
        if (!allowNeg && v < 0) v = 0;
        var form = qty.closest('form');
        if (form && form.getAttribute('data-stock-form') === 'give') {
          v = Math.min(v, parseInt(form.getAttribute('data-current'), 10) || 0);
        }
        input.value = v;
        updateTotal(qty);
      });
    });
    input.addEventListener('input', function () { updateTotal(qty); });
  });

  /* ------------------------------------------------------------------ Stock change forms (receive / give / adjust) */
  function applyStock(form, from, to) {
    var unit = form.getAttribute('data-unit');
    qsa('[data-stock-form]').forEach(function (f) {
      if (f.getAttribute('data-item') !== form.getAttribute('data-item')) return;
      f.setAttribute('data-current', to);
      qsa('[data-current-label]', f).forEach(function (n) { n.textContent = fmt(to); });
      var q = qs('[data-qty]', f); if (q) updateTotal(q);
    });
    var count = qs('[data-stock-count]');
    if (count && form.getAttribute('data-item') === 'A4 Copy Paper') {
      count.textContent = fmt(to);
      var meter = qs('[data-meter]');
      if (meter) {
        var max = +meter.getAttribute('data-max'), re = +meter.getAttribute('data-reorder');
        qs('.meter-fill', meter).style.width = Math.min(100, to / max * 100) + '%';
        meter.setAttribute('aria-valuenow', to);
        meter.setAttribute('aria-valuetext', to + ' ' + unit + '. Reorder level is ' + re + '.');
        var note = qs('[data-meter-note]');
        if (note) note.textContent = to > re
          ? 'You have ' + fmt(to - re) + ' more than the reorder level. No need to order yet.'
          : 'This is at or below the reorder level. Time to order more.';
      }
      var val = qs('[data-stock-value]');
      if (val) val.textContent = money(to * 1450);
    }
  }
  qsa('[data-stock-form]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var mode = form.getAttribute('data-stock-form');
      var reason = qs('select[required]', form);
      if (reason) {
        var err = document.getElementById(reason.getAttribute('aria-describedby'));
        if (!reason.value) {
          reason.setAttribute('aria-invalid', 'true');
          reason.closest('.field').classList.add('has-error');
          if (err) err.hidden = false;
          reason.focus();
          return;
        }
        reason.removeAttribute('aria-invalid');
        reason.closest('.field').classList.remove('has-error');
        if (err) err.hidden = true;
      }
      var unit = form.getAttribute('data-unit');
      var item = form.getAttribute('data-item');
      var from = parseInt(form.getAttribute('data-current'), 10) || 0;
      var v = stepperValue(qs('[data-qty] input', form));
      if (v === 0) { showToast({ type: 'warning', title: 'Nothing changed', text: 'The amount was 0, so the stock stays at ' + fmt(from) + ' ' + unit + '.' }); return; }
      var to = mode === 'give' ? from - v : from + v;
      if (to < 0) to = 0;
      applyStock(form, from, to);
      var row = addHistory(mode, v, to, form);
      closeModal();
      var what = { receive: 'Received ' + fmt(v) + ' ' + unit + ' of ' + item + '.',
                   give: 'Gave out ' + fmt(v) + ' ' + unit + (qs('#gv-who') ? ' to ' + qs('#gv-who').value : '') + '.',
                   adjust: 'Adjusted by ' + (v > 0 ? '+' : '') + fmt(v) + ' ' + unit + '. Reason saved.' }[mode];
      showToast({
        type: 'success',
        title: 'Stock updated — ' + fmt(from) + ' → ' + fmt(to) + ' ' + unit,
        text: what,
        undo: function () {
          applyStock(form, to, from);
          if (row) row.remove();
          showToast({ type: 'info', title: 'Change undone', text: 'Stock is back to ' + fmt(from) + ' ' + unit + '.' });
        }
      });
    });
  });
  function addHistory(mode, v, to, form) {
    var tbody = qs('[data-history]');
    if (!tbody || form.getAttribute('data-item') !== 'A4 Copy Paper') return null;
    var tr = document.createElement('tr');
    var cells = [
      ['When', 'Today, just now'],
      ['What happened', { receive: 'Received from ' + (qs('#rc-sup') ? qs('#rc-sup').value : 'supplier'), give: 'Given out to ' + (qs('#gv-who') ? qs('#gv-who').value : ''), adjust: 'Adjusted: ' + (qs('#adj-reason') ? qs('#adj-reason').value : '') }[mode]],
      ['Change', (mode === 'give' ? '−' : (v > 0 ? '+' : '')) + fmt(Math.abs(v) === v || mode === 'give' ? v : v)],
      ['Stock after', fmt(to)],
      ['Who', 'Nimali Perera']
    ];
    cells.forEach(function (c, i) {
      var td = document.createElement('td');
      td.setAttribute('data-label', c[0]);
      if (i === 0) { td.className = 'cell-full'; var s = el('strong', null, c[1]); td.appendChild(s); }
      else td.textContent = c[1];
      if (i === 2 || i === 3) td.className = 'num';
      tr.appendChild(td);
    });
    tbody.insertBefore(tr, tbody.firstChild);
    return tr;
  }

  /* ------------------------------------------------------------------ Dashboard: reorder */
  qsa('[data-reorder]').forEach(function (b) {
    var original = b.innerHTML;
    b.addEventListener('click', function () {
      var name = b.getAttribute('data-reorder');
      b.disabled = true;
      b.textContent = 'Added to order';
      showToast({
        type: 'success', title: 'Added to the next order',
        text: name + ': ' + b.getAttribute('data-reorder-qty') + '. The office will see it in Orders.',
        undo: function () { b.disabled = false; b.innerHTML = original; }
      });
    });
  });

  /* ------------------------------------------------------------------ Chart (inline SVG from JSON) */
  var NS = 'http://www.w3.org/2000/svg';
  function svg(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function barPath(x, y, w, h, r) {
    if (h <= 0) return '';
    r = Math.min(r, h, w / 2);
    return 'M' + x + ',' + (y + h) + 'V' + (y + r) + 'Q' + x + ',' + y + ' ' + (x + r) + ',' + y +
      'H' + (x + w - r) + 'Q' + (x + w) + ',' + y + ' ' + (x + w) + ',' + (y + r) + 'V' + (y + h) + 'Z';
  }
  function drawChart(host) {
    var data = JSON.parse(qs('#' + host.getAttribute('data-chart')).textContent);
    host.textContent = '';
    var W = Math.max(300, host.clientWidth), H = W < 520 ? 240 : 272;
    var m = { l: 40, r: 8, t: 26, b: 40 };
    var pw = W - m.l - m.r, ph = H - m.t - m.b;
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H }, host);
    var y = function (v) { return m.t + ph - (v / data.max) * ph; };
    for (var t = 0; t <= data.max; t += data.step) {
      svg('line', { x1: m.l, x2: W - m.r, y1: Math.round(y(t)) + 0.5, y2: Math.round(y(t)) + 0.5, 'class': t === 0 ? 'base-line' : 'grid-line' }, s);
      var tl = svg('text', { x: m.l - 10, y: y(t) + 4, 'text-anchor': 'end', 'class': 'tick' }, s);
      tl.textContent = fmt(t);
    }
    var n = data.days.length, band = pw / n;
    var bw = Math.min(24, Math.max(8, (band - 18) / 2)), gap = 2;
    var maxIn = Math.max.apply(null, data.days.map(function (d) { return d.in; }));
    var maxOut = Math.max.apply(null, data.days.map(function (d) { return d.out; }));
    var tip = el('div', 'chart-tip'); tip.style.opacity = 0; tip.setAttribute('aria-hidden', 'true');
    host.appendChild(tip);

    data.days.forEach(function (d, i) {
      var cx = m.l + band * i + band / 2;
      var g = svg('g', { 'class': 'group', tabindex: 0, role: 'img',
        'aria-label': d.long + ': ' + d.in + ' came in, ' + d.out + ' went out' }, s);
      svg('rect', { x: cx - band / 2 + 3, y: m.t - 8, width: band - 6, height: ph + 8, rx: 10, 'class': 'hit-bg' }, g);
      var xi = cx - bw - gap / 2, xo = cx + gap / 2;
      var p1 = barPath(xi, y(d.in), bw, y(0) - y(d.in), 4);
      var p2 = barPath(xo, y(d.out), bw, y(0) - y(d.out), 4);
      if (p1) svg('path', { d: p1, 'class': 'bar-in' }, g);
      if (p2) svg('path', { d: p2, 'class': 'bar-out' }, g);
      if (d.in === maxIn) { var a = svg('text', { x: xi + bw / 2, y: y(d.in) - 7, 'text-anchor': 'middle', 'class': 'value-label' }, g); a.textContent = d.in; }
      if (d.out === maxOut) { var b = svg('text', { x: xo + bw / 2, y: y(d.out) - 7, 'text-anchor': 'middle', 'class': 'value-label' }, g); b.textContent = d.out; }
      var xl = svg('text', { x: cx, y: H - m.b + 24, 'text-anchor': 'middle', 'class': 'x-label' + (d.today ? ' is-today' : '') }, s);
      xl.textContent = d.label;
      svg('rect', { x: cx - band / 2, y: m.t - 8, width: band, height: ph + 8, 'class': 'hit' }, g);

      function show() {
        qsa('.group.is-active', s).forEach(function (o) { o.classList.remove('is-active'); });
        g.classList.add('is-active');
        tip.textContent = '';
        tip.appendChild(el('p', 'chart-tip-title', d.long));
        [['Came in', d.in, 'var(--chart-in)'], ['Went out', d.out, 'var(--chart-out)']].forEach(function (r) {
          var row = el('div', 'chart-tip-row');
          var k = el('span', 'line-key'); k.style.background = r[2];
          row.appendChild(k); row.appendChild(el('strong', null, fmt(r[1]))); row.appendChild(el('span', 'muted', r[0]));
          tip.appendChild(row);
        });
        var top = y(Math.max(d.in, d.out)) - 14;
        tip.style.left = Math.min(Math.max(cx, 95), W - 95) + 'px';
        tip.style.top = Math.max(top, 70) + 'px';
        tip.style.opacity = 1;
      }
      function hide() { g.classList.remove('is-active'); tip.style.opacity = 0; }
      g.addEventListener('pointerenter', show);
      g.addEventListener('pointerleave', hide);
      g.addEventListener('focus', show);
      g.addEventListener('blur', hide);
    });
  }
  qsa('[data-chart]').forEach(function (host) {
    drawChart(host);
    if ('ResizeObserver' in window) {
      var lastW = host.clientWidth;
      new ResizeObserver(function () {
        if (Math.abs(host.clientWidth - lastW) > 4) { lastW = host.clientWidth; drawChart(host); }
      }).observe(host);
    }
  });

  /* ------------------------------------------------------------------ Items: filters, empty state, archive */
  var filterForm = qs('[data-filter-form]');
  if (filterForm) {
    var rows = qsa('#items-table tbody tr');
    var q = qs('#q'), fc = qs('#f-cat'), fl = qs('#f-loc'), fs = qs('#f-status');
    var countEl = qs('#results-count'), empty = qs('#items-empty'), tableWrap = qs('#items-table-wrap'), pager = qs('#items-pager');
    function applyFilters() {
      var term = q.value.trim().toLowerCase(), shown = 0;
      rows.forEach(function (r) {
        if (r.hasAttribute('data-archived-now')) { r.hidden = true; return; }
        var ok = (!term || r.textContent.toLowerCase().indexOf(term) > -1) &&
          (!fc.value || r.getAttribute('data-cat') === fc.value) &&
          (!fl.value || r.getAttribute('data-loc') === fl.value) &&
          (!fs.value || r.getAttribute('data-status').split(' ').indexOf(fs.value) > -1);
        r.hidden = !ok;
        if (ok) shown++;
      });
      var filtered = term || fc.value || fl.value || fs.value;
      countEl.textContent = filtered ? (shown === 1 ? '1 item matches' : shown + ' items match') : 'Showing 13 of 248 items';
      empty.hidden = shown !== 0;
      tableWrap.hidden = shown === 0;
      pager.hidden = shown === 0;
      var termOut = qs('[data-empty-term]');
      if (termOut) termOut.textContent = q.value.trim() || 'these filters';
    }
    [q, fc, fl, fs].forEach(function (c) { c.addEventListener('input', applyFilters); c.addEventListener('change', applyFilters); });
    filterForm.addEventListener('submit', function (e) { e.preventDefault(); applyFilters(); });
    qsa('[data-filter-clear]').forEach(function (b) {
      b.addEventListener('click', function (e) { e.preventDefault(); filterForm.reset(); applyFilters(); q.focus(); });
    });
    var ft = qs('[data-filter-toggle]');
    function setFiltersOpen(open) {
      filterForm.classList.toggle('is-expanded', open);
      ft.setAttribute('aria-expanded', open ? 'true' : 'false');
      ft.lastChild.textContent = open ? 'Hide filters' : 'Show filters';
    }
    if (ft) ft.addEventListener('click', function () { setFiltersOpen(!filterForm.classList.contains('is-expanded')); });
    if (params.get('q')) q.value = params.get('q');
    if (ft && params.get('status')) setFiltersOpen(true);
    if (params.get('status')) fs.value = params.get('status');
    if (demo === 'empty') q.value = 'projector screen';
    applyFilters();

    var archiveRow = null;
    qsa('[data-archive]').forEach(function (b) {
      b.addEventListener('click', function () {
        archiveRow = b.closest('tr');
        qs('[data-archive-name]').textContent = b.getAttribute('data-archive');
        closeMenus();
        openModal('archive-modal', b.closest('.menu').querySelector('[data-menu]'));
      });
    });
    var confirmBtn = qs('[data-archive-confirm]');
    if (confirmBtn) confirmBtn.addEventListener('click', function () {
      if (!archiveRow) return;
      var row = archiveRow, name = qs('[data-archive-name]').textContent;
      row.setAttribute('data-archived-now', '');
      closeModal();
      applyFilters();
      showToast({ type: 'success', title: name + ' archived', text: 'It’s hidden from lists. Its history is kept.',
        undo: function () { row.removeAttribute('data-archived-now'); applyFilters(); } });
    });
    qsa('[data-restore]').forEach(function (b) {
      b.addEventListener('click', function () {
        showToast({ type: 'success', title: b.getAttribute('data-restore') + ' restored', text: 'It’s back in the item list with 0 in stock.' });
      });
    });
  }

  /* ------------------------------------------------------------------ Add item form */
  var itemForm = qs('[data-item-form]');
  if (itemForm) {
    var summary = qs('#error-summary'), list = qs('[data-error-list]');
    var stepNames = { 'step-details': 'Details', 'step-stock': 'Stock', 'step-price': 'Price' };
    var fields = qsa('[data-rule]', itemForm);

    function check(f) {
      var rule = f.getAttribute('data-rule');
      if (rule === 'radio') return !!qs('input:checked', f);
      var v = f.value.trim();
      if (rule === 'required') return v !== '';
      if (rule === 'whole') return /^\d+$/.test(v);
      if (rule === 'money') return /^\d{1,3}(,?\d{3})*(\.\d{1,2})?$/.test(v) && v !== '';
      return true;
    }
    function setError(f, on) {
      var wrap = f.matches('fieldset') ? f : f.closest('[data-field]');
      var id = f.id + '-err';
      var err = document.getElementById(id);
      wrap.classList.toggle('has-error', on);
      var target = f.matches('fieldset') ? null : f;
      if (on) {
        if (!err) {
          err = el('p', 'field-error'); err.id = id;
          err.appendChild(iconEl('error'));
          err.appendChild(el('span', null, f.getAttribute('data-msg')));
          var anchor = f.matches('fieldset') ? qs('.chips', f) : (f.closest('.input-group') || f.closest('.qty') || f);
          anchor.insertAdjacentElement('afterend', err);
        }
        if (target) {
          target.setAttribute('aria-invalid', 'true');
          var d = (target.getAttribute('aria-describedby') || '').split(' ').filter(Boolean);
          if (d.indexOf(id) < 0) { d.push(id); target.setAttribute('aria-describedby', d.join(' ')); }
        } else {
          qsa('input', f).forEach(function (r) { r.setAttribute('aria-describedby', id); });
        }
      } else {
        if (err) err.remove();
        if (target) {
          target.removeAttribute('aria-invalid');
          var dd = (target.getAttribute('aria-describedby') || '').split(' ').filter(function (x) { return x && x !== id; });
          dd.length ? target.setAttribute('aria-describedby', dd.join(' ')) : target.removeAttribute('aria-describedby');
        }
      }
    }
    function updateSteps() {
      qsa('[data-step-for]').forEach(function (li) {
        var sec = document.getElementById(li.getAttribute('data-step-for'));
        var req = qsa('[data-rule]', sec);
        var errs = qsa('.has-error', sec).length;
        var done = req.every(check);
        li.classList.toggle('has-error', errs > 0);
        li.classList.toggle('is-done', done && errs === 0);
        var st = qs('[data-step-status]', li);
        if (!st.dataset.base) st.dataset.base = st.textContent;
        st.textContent = errs ? (errs === 1 ? '1 thing to fix' : errs + ' things to fix') : (done ? 'Done' : st.dataset.base);
      });
    }
    function validate(focusSummary) {
      var bad = fields.filter(function (f) { var ok = check(f); setError(f, !ok); return !ok; });
      list.textContent = '';
      bad.forEach(function (f) {
        var li = el('li');
        var a = el('a', null, f.getAttribute('data-msg'));
        a.href = '#' + f.id;
        a.addEventListener('click', function (e) {
          e.preventDefault();
          var sec = f.closest('[data-section]');
          sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
          var target = f.matches('fieldset') ? qs('input', f) : f;
          setTimeout(function () { target.focus({ preventScroll: true }); }, 350);
        });
        li.appendChild(a);
        li.appendChild(el('span', 'step-tag', ' (Step ' + (Object.keys(stepNames).indexOf(f.closest('[data-section]').id) + 1) + ': ' + stepNames[f.closest('[data-section]').id] + ')'));
        list.appendChild(li);
      });
      qs('[data-error-count]').textContent = bad.length === 1 ? '1 thing' : bad.length + ' things';
      summary.hidden = bad.length === 0;
      updateSteps();
      if (bad.length && focusSummary) { summary.focus(); window.scrollTo({ top: 0 }); }
      return bad.length === 0;
    }
    itemForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (validate(true)) {
        showToast({ type: 'success', title: 'Item saved', text: qs('#f-name').value.trim() + ' is now in the list. Next, you can receive stock for it.' });
      }
    });
    fields.forEach(function (f) {
      var ev = f.matches('fieldset, select') ? 'change' : 'blur';
      f.addEventListener(ev, function () {
        var wrap = f.matches('fieldset') ? f : f.closest('[data-field]');
        if (wrap.classList.contains('has-error') && check(f)) {
          setError(f, false);
          if (!summary.hidden) validate(false);
        }
        updateSteps();
      }, true);
      f.addEventListener('input', function () { updateSteps(); });
    });
    // Current step follows the scroll position
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          qsa('[data-step-for]').forEach(function (li) {
            li.classList.toggle('is-current', li.getAttribute('data-step-for') === en.target.id);
            var a = qs('a', li);
            li.getAttribute('data-step-for') === en.target.id ? a.setAttribute('aria-current', 'step') : a.removeAttribute('aria-current');
          });
        });
      }, { rootMargin: '-35% 0px -55% 0px' });
      qsa('[data-section]').forEach(function (s) { io.observe(s); });
    }
    if (demo === 'errors') {
      qs('#f-category').value = 'Stationery';
      qs('#f-desc').value = 'Red ink, chisel tip, refillable';
      qs('#f-reorder').value = '40';
      qs('#f-cost').value = 'Rs 180';
      validate(true);
    } else {
      updateSteps();
    }
  }

  /* ------------------------------------------------------------------ Login */
  var loginForm = qs('[data-login-form]');
  if (loginForm) {
    var errBox = qs('#login-error');
    if (demo === 'error') {
      errBox.hidden = false;
      qs('#username').value = 'nimali.p';
      qs('#password').setAttribute('aria-invalid', 'true');
      qs('#username').setAttribute('aria-invalid', 'true');
    }
    loginForm.addEventListener('submit', function (e) {
      var u = qs('#username'), p = qs('#password');
      if (!u.value.trim() || !p.value) {
        e.preventDefault();
        errBox.hidden = false;
        qs('.alert-title', errBox).textContent = 'Please fill in both boxes';
        qs('.alert-text', errBox).textContent = 'Type your username and password, then press Sign in.';
        (u.value.trim() ? p : u).focus();
        return;
      }
      e.preventDefault();
      location.href = 'dashboard.html';
    });
  }
  qsa('[data-toggle-password]').forEach(function (b) {
    var input = document.getElementById(b.getAttribute('data-toggle-password'));
    b.addEventListener('click', function () {
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      b.setAttribute('aria-pressed', show ? 'true' : 'false');
      qs('span', b).textContent = show ? 'Hide' : 'Show';
      b.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
  });

  /* ------------------------------------------------------------------ UI kit */
  var SAMPLE = {
    success: { type: 'success', title: 'Item saved', text: 'Whiteboard Marker, Red is now in the list.' },
    info: { type: 'info', title: 'Delivery due on 18 September', text: '10 Wireless Mice from Island Tech Solutions.' },
    warning: { type: 'warning', title: 'Only 3 cricket balls left', text: 'That’s below the reorder level of 12.' },
    error: { type: 'error', title: 'We couldn’t save that', text: 'The connection dropped. Your numbers are still here. Try again in a moment.' },
    undo: { type: 'success', title: 'Stock updated — 142 → 192 reams', text: 'A4 Copy Paper. Changed your mind? Press Undo.', undo: function () { showToast({ type: 'info', title: 'Change undone', text: 'Stock is back to 142 reams.' }); } }
  };
  qsa('[data-toast]').forEach(function (b) {
    b.addEventListener('click', function () { showToast(SAMPLE[b.getAttribute('data-toast')]); });
  });
  qsa('[data-loading-demo]').forEach(function (b) {
    b.addEventListener('click', function () {
      var label = b.innerHTML;
      b.classList.add('is-loading'); b.setAttribute('aria-busy', 'true'); b.lastChild.textContent = 'Saving…';
      setTimeout(function () {
        b.classList.remove('is-loading'); b.removeAttribute('aria-busy'); b.innerHTML = label;
        showToast(SAMPLE.success);
      }, 1600);
    });
  });
  qsa('[data-skeleton-toggle]').forEach(function (b) {
    b.addEventListener('click', function () {
      var loading = b.getAttribute('aria-pressed') === 'true';
      var box = b.closest('.kit-demo');
      qs('[data-skeleton]', box).hidden = loading;
      qs('[data-skeleton-done]', box).hidden = !loading;
      b.setAttribute('aria-pressed', loading ? 'false' : 'true');
      b.lastChild.textContent = loading ? 'Show loading again' : 'Show the finished list';
    });
  });
  qsa('[data-reason-form]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var s = qs('select', f), err = qs('.field-error', f);
      if (!s.value) {
        s.setAttribute('aria-invalid', 'true'); s.closest('.field').classList.add('has-error'); err.hidden = false; s.focus(); return;
      }
      s.removeAttribute('aria-invalid'); s.closest('.field').classList.remove('has-error'); err.hidden = true;
      closeModal();
      showToast({ type: 'success', title: 'Safety Goggles archived', text: 'Reason: ' + s.value + '.', undo: function () { showToast({ type: 'info', title: 'Safety Goggles restored' }); } });
    });
  });
  qsa('[data-type-form]').forEach(function (f) {
    var input = qs('input', f), btn = qs('[data-type-submit]', f), help = qs('[data-type-help]', f);
    var match = f.getAttribute('data-match');
    input.addEventListener('input', function () {
      var ok = input.value.trim().toLowerCase() === match.toLowerCase();
      btn.disabled = !ok;
      help.textContent = ok ? 'The name matches. You can now clear the history.' : 'The red button turns on when the name matches.';
    });
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      if (btn.disabled) return;
      closeModal();
      input.value = ''; btn.disabled = true;
      showToast({ type: 'success', title: 'History cleared for Safety Goggles', text: 'The office can bring it back if needed.' });
    });
  });

  /* ------------------------------------------------------------------ Demo hooks & task deep links */
  var task = params.get('task');
  if (demo === 'modal' && qs('#adjust-modal')) {
    openModal('adjust-modal');
    qs('#adj-qty').value = 50;
    qs('#adj-reason').value = 'Found extra stock';
    updateTotal(qs('#adjust-modal [data-qty]'));
  }
  if (task === 'receive' && qs('#receive-modal')) openModal('receive-modal');
  if (task === 'give' && qs('#give-modal')) openModal('give-modal');
  if (demo === 'toast') {
    showToast({ type: 'success', title: 'Stock updated — 142 → 192 reams', text: 'Received 50 reams of A4 Copy Paper.', sticky: true,
      undo: function () { showToast({ type: 'info', title: 'Change undone', text: 'Stock is back to 142 reams.' }); } });
  }
  if (demo === 'drawer' && sidebar) drawerOpen(qs('.menu-btn'));
})();
