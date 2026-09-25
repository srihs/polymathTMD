/*
  Polymath TMD: progressive enhancements (ported from design/f-desk/app.js).

  Why this file is shaped like this: every page works without it (links
  navigate, forms submit, <details> menus open, the phone menu is a plain
  #nav link). This file only adds what needs a script, and it finds elements
  through data-* attributes only, so markup and styles can change freely.
  Every JS-only control is `hidden` in the HTML and revealed here.

  Blocks
    1. Helpers
    2. Layout settings: read, apply, save (values from theme-init.js)
    3. Colour-mode button
    4. Settings panel (<dialog>), with the "Icons only" sync fix
    5. Menu toggle: collapse on desktop, drawer on phone
    6. Dropdowns (<details data-pop>)
    7. Flash messages (close)
    8. Sign-in: the empty-field check
    9. Zoom link requests: weekly fields, error-summary focus
*/
(function () {
  'use strict';

  /* ------------------------------------------------------------------
     1. Helpers
     ------------------------------------------------------------------ */
  var doc = document;
  var root = doc.documentElement;

  function qs(selector, scope) { return (scope || doc).querySelector(selector); }
  function qsa(selector, scope) { return Array.prototype.slice.call((scope || doc).querySelectorAll(selector)); }
  function isRendered(el) { return !!(el && el.getClientRects().length); }

  var phoneQuery = window.matchMedia('(max-width: 991.98px)');

  /* ------------------------------------------------------------------
     2. Layout settings. The four values live on <html>; theme-init.js set
     them before first paint and owns the allowed values and defaults
     (window.tmdLayout), so this block never keeps its own copy.
     The sidebar size stored is always the one chosen in the settings
     panel (chosenNavSize): the menu toggle (block 5) collapses the sidebar
     for this page only and never writes storage.
     ------------------------------------------------------------------ */
  var layout = window.tmdLayout || null;
  var SETTINGS = layout ? layout.settings : {};
  /* The radio names in the settings panel, mapped to the setting keys. */
  var RADIO_KEYS = { theme: 'theme', width: 'width', 'nav-size': 'navSize', 'nav-tone': 'navTone' };
  var chosenNavSize = root.getAttribute('data-nav-size');

  function currentTheme() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function save() {
    if (!layout) { return; }
    var data = {};
    Object.keys(SETTINGS).forEach(function (key) {
      data[key] = key === 'navSize' ? chosenNavSize : root.getAttribute(SETTINGS[key].attr);
    });
    try { window.localStorage.setItem(layout.key, JSON.stringify(data)); } catch (err) { /* storage blocked */ }
  }

  function setSetting(key, value) {
    var rule = SETTINGS[key];
    if (!rule || rule.values.indexOf(value) === -1) { return; }
    root.setAttribute(rule.attr, value);
    if (key === 'navSize') { chosenNavSize = value; }
    save();
    syncAll();
  }

  function resetSettings() {
    if (!layout) { return; }
    try { window.localStorage.removeItem(layout.key); } catch (err) { /* storage blocked */ }
    Object.keys(SETTINGS).forEach(function (key) {
      root.setAttribute(SETTINGS[key].attr, SETTINGS[key].fallback);
    });
    chosenNavSize = SETTINGS.navSize.fallback;
    syncAll();
  }

  function syncAll() {
    syncRadios();
    syncThemeButtons();
    syncToggle();
  }

  /* ------------------------------------------------------------------
     3. Colour-mode button (top bar, sign-in page). CSS picks the moon or
     sun icon from data-theme; this keeps the spoken label in step.
     ------------------------------------------------------------------ */
  var themeButtons = layout ? qsa('[data-theme-toggle]') : [];

  function syncThemeButtons() {
    var label = currentTheme() === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    themeButtons.forEach(function (button) {
      var words = qs('[data-theme-label]', button);
      if (words) { words.textContent = label; }
    });
  }

  themeButtons.forEach(function (button) {
    button.hidden = false;
    button.addEventListener('click', function () {
      setSetting('theme', currentTheme() === 'dark' ? 'light' : 'dark');
    });
  });

  /* ------------------------------------------------------------------
     4. Settings panel. A modal <dialog>, so focus containment and Escape
     come from the browser. Focus goes back to whatever opened it (the user
     menu's summary when opened from inside that menu).
     "Icons only" sync fix (brief 004, criterion 13): the Sidebar size
     radios show chosenNavSize, never the toggle's page-only collapse, and
     a click on the already-checked size applies it too, which ends a
     page-only collapse.
     ------------------------------------------------------------------ */
  var sheet = layout ? qs('[data-settings]') : null;
  var sheetOpener = null;

  function syncRadios() {
    if (!sheet) { return; }
    qsa('input[data-setting]', sheet).forEach(function (input) {
      var key = RADIO_KEYS[input.name];
      var value = key === 'navSize' ? chosenNavSize : root.getAttribute(SETTINGS[key].attr);
      if (key === 'theme') { value = currentTheme(); }
      input.checked = input.value === value;
    });
  }

  if (sheet) {
    qsa('[data-settings-open]').forEach(function (button) {
      button.hidden = false;
      button.addEventListener('click', function () {
        var pop = button.closest('[data-pop]');
        sheetOpener = button;
        if (pop) {
          pop.open = false;
          sheetOpener = qs('summary', pop);
        }
        syncRadios();
        sheet.showModal();
      });
    });

    qsa('[data-settings-close]', sheet).forEach(function (button) {
      button.addEventListener('click', function () { sheet.close(); });
    });

    /* A click on the dimmed page (the backdrop) closes the panel too. */
    sheet.addEventListener('click', function (event) {
      if (event.target !== sheet) { return; }
      var box = sheet.getBoundingClientRect();
      var inside = event.clientX >= box.left && event.clientX <= box.right &&
        event.clientY >= box.top && event.clientY <= box.bottom;
      if (!inside) { sheet.close(); }
    });

    sheet.addEventListener('close', function () {
      if (sheetOpener && isRendered(sheetOpener)) { sheetOpener.focus(); }
    });

    qsa('input[data-setting]', sheet).forEach(function (input) {
      var key = RADIO_KEYS[input.name];
      input.addEventListener('change', function () {
        if (input.checked) { setSetting(key, input.value); }
      });
      if (key === 'navSize') {
        /* No change event fires for the radio that is already checked, so a
           click on the chosen size applies it here; a newly picked size is
           left to the change handler, so it is saved once. */
        input.addEventListener('click', function () {
          if (input.checked && input.value === chosenNavSize) { setSetting(key, input.value); }
        });
      }
    });

    var reset = qs('[data-settings-reset]', sheet);
    if (reset) {
      reset.addEventListener('click', function () {
        resetSettings();
        reset.focus();
      });
    }
  }

  /* ------------------------------------------------------------------
     5. Menu toggle. On desktop it switches the sidebar between "icons only"
     and the size chosen in the settings panel (Standard when the chosen
     size is itself "icons only"), for this page only. On phone it opens
     the sidebar as a drawer over an inert page.
     ------------------------------------------------------------------ */
  var nav = qs('[data-nav]');
  var toggle = qs('[data-nav-toggle]');
  var toggleLabel = toggle ? qs('[data-nav-toggle-label]', toggle) : null;
  var scrim = qs('[data-scrim]');
  var navLink = qs('[data-nav-link]');
  var navClose = qs('[data-nav-close]');
  var pageParts = qsa('[data-drawer-inert]');

  function drawerIsOpen() { return !!(nav && nav.hasAttribute('data-open')); }

  function syncToggle() {
    if (!toggle) { return; }
    var expanded = phoneQuery.matches ? drawerIsOpen() : root.getAttribute('data-nav-size') !== 'icons';
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    if (toggleLabel) { toggleLabel.textContent = expanded ? 'Hide the menu' : 'Show the menu'; }
  }

  function openDrawer() {
    nav.setAttribute('data-open', '');
    if (scrim) { scrim.hidden = false; }
    pageParts.forEach(function (part) { part.inert = true; });
    syncToggle();
    if (navClose) { navClose.focus(); }
  }

  function closeDrawer(returnFocus) {
    if (!drawerIsOpen()) { return; }
    nav.removeAttribute('data-open');
    if (scrim) { scrim.hidden = true; }
    pageParts.forEach(function (part) { part.inert = false; });
    syncToggle();
    if (returnFocus && toggle) { toggle.focus(); }
  }

  if (nav && toggle) {
    toggle.hidden = false;
    if (navLink) { navLink.hidden = true; }

    toggle.addEventListener('click', function () {
      if (phoneQuery.matches) {
        openDrawer();
        return;
      }
      var collapsed = root.getAttribute('data-nav-size') === 'icons';
      var wide = chosenNavSize === 'icons' ? 'standard' : chosenNavSize;
      root.setAttribute('data-nav-size', collapsed ? wide : 'icons');
      syncToggle();
    });

    if (navClose) {
      navClose.addEventListener('click', function (event) {
        event.preventDefault();
        closeDrawer(true);
      });
    }

    if (scrim) {
      scrim.addEventListener('click', function () { closeDrawer(true); });
    }

    nav.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && drawerIsOpen()) { closeDrawer(true); }
    });

    phoneQuery.addEventListener('change', function () {
      closeDrawer(false);
      syncToggle();
    });

    /* Arriving with #nav in the address (the no-script menu link) must not
       leave the drawer stuck open without its scrim. */
    if (window.location.hash === '#nav' && window.history.replaceState) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }

  /* ------------------------------------------------------------------
     6. Dropdowns. <details data-pop> already opens and closes without a
     script; this adds one-at-a-time, Escape and click-outside, each
     returning focus to the summary.
     ------------------------------------------------------------------ */
  var pops = qsa('[data-pop]');

  function openPops() {
    return pops.filter(function (pop) { return pop.open && isRendered(qs('summary', pop)); });
  }

  pops.forEach(function (pop) {
    pop.addEventListener('toggle', function () {
      if (!pop.open) { return; }
      pops.forEach(function (other) {
        if (other !== pop && other.open && isRendered(qs('summary', other))) { other.open = false; }
      });
    });
  });

  doc.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') { return; }
    openPops().forEach(function (pop) {
      pop.open = false;
      qs('summary', pop).focus();
    });
  });

  doc.addEventListener('click', function (event) {
    openPops().forEach(function (pop) {
      if (pop.contains(event.target)) { return; }
      pop.open = false;
      var landedOnControl = event.target.closest && event.target.closest('a, button, input, select, textarea, summary, label, [tabindex]:not([tabindex="-1"])');
      if (!landedOnControl) { qs('summary', pop).focus(); }
    });
  });

  /* ------------------------------------------------------------------
     7. Flash messages (partials/messages.html). They sit in the page flow
     and never time out; Close removes one and puts focus on <main>, so
     keyboard users are not left on a removed element.
     ------------------------------------------------------------------ */
  qsa('[data-flash]').forEach(function (flash) {
    qsa('[data-flash-close]', flash).forEach(function (button) {
      button.hidden = false;
      button.addEventListener('click', function () {
        var main = flash.closest('main');
        var group = flash.parentNode;
        flash.remove();
        if (group && !qs('[data-flash]', group)) { group.remove(); }
        if (main) { main.focus(); }
      });
    });
  });

  /* ------------------------------------------------------------------
     8. Sign-in page: the empty-field check. Instead of a round trip, say
     what is missing in the same notice the server uses, mark the empty field(s) invalid and point
     them at the notice, and focus the first empty one. Typing in a field
     clears its invalid state; the message stays until the next submit.
     ------------------------------------------------------------------ */
  var loginForm = qs('[data-login-form]');
  var loginError = qs('[data-login-error]');
  if (loginForm && loginError) {
    var loginFields = qsa('[data-login-field]', loginForm);

    loginFields.forEach(function (field) {
      field.addEventListener('input', function () { field.removeAttribute('aria-invalid'); });
    });

    loginForm.addEventListener('submit', function (event) {
      var empty = loginFields.filter(function (field) {
        /* data-login-field="trim": spaces alone count as empty (username only;
           a password is taken exactly as typed). */
        var value = field.getAttribute('data-login-field') === 'trim' ? field.value.trim() : field.value;
        return !value;
      });
      if (!empty.length) { return; }
      event.preventDefault();
      var title = qs('[data-login-error-title]', loginError);
      var text = qs('[data-login-error-text]', loginError);
      if (title) { title.textContent = 'Please fill in both boxes'; }
      if (text) { text.textContent = 'Type your username and password, then press Sign in.'; }
      loginError.hidden = false;
      empty.forEach(function (field) {
        field.setAttribute('aria-invalid', 'true');
        field.setAttribute('aria-describedby', loginError.id + ' ' + field.id + '-help');
      });
      empty[0].focus();
    });
  }

  /* ------------------------------------------------------------------
     9. Zoom link requests (brief 005, D.9).
     a. Weekly fields: while the checked [data-repeat] radio is "once", the
        [data-weekly-fields] group is hidden and its inputs disabled, so
        they are not sent (the server ignores them for "once" anyway).
        Typed values stay in the page and come back with "Every week".
        Without JS the group simply always shows.
     b. Error summary: after a failed submit, focus the first
        [data-error-summary] (tabindex="-1"), so it is read out and in view.
     ------------------------------------------------------------------ */
  var repeatRadios = qsa('[data-repeat]');
  var weeklyFields = qs('[data-weekly-fields]');
  if (repeatRadios.length && weeklyFields) {
    var weeklyInputs = qsa('input, select, textarea', weeklyFields);
    var syncWeekly = function () {
      var once = repeatRadios.some(function (radio) { return radio.checked && radio.value === 'once'; });
      weeklyFields.hidden = once;
      weeklyInputs.forEach(function (input) { input.disabled = once; });
    };
    repeatRadios.forEach(function (radio) { radio.addEventListener('change', syncWeekly); });
    syncWeekly();
  }

  var errorSummary = qs('[data-error-summary]');
  if (errorSummary) {
    errorSummary.focus({ preventScroll: true });
    errorSummary.scrollIntoView({ block: 'start' });
  }

  syncAll();
})();
