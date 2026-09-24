/*
  Polymath TMD, direction F "Desk": progressive enhancements.

  Why this file is shaped like this: every page works without it (links
  navigate, forms submit, <details> menus open, the phone menu is a plain
  link). This file only adds what needs a script, and it finds elements
  through data-* attributes so the markup and styles can change freely.

  Blocks
    1. Helpers
    2. Layout settings: read, apply, save
    3. Colour-mode button
    4. Settings panel (<dialog>)
    5. Menu toggle: collapse on desktop, drawer on phone
    6. Dropdowns (<details data-pop>)
    7. Toast
    8. Error summary links
    9. ?demo= state hooks (prototype only, never ported)
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
     2. Layout settings. The four values live on <html> (theme-init.js set
     them before first paint). The page opens in light mode; dark mode is
     only ever a saved choice.
     The sidebar size stored is always the one chosen in the settings
     panel: the menu button (block 5) collapses the sidebar for this page
     only, so it can always return to the chosen size, even after a reload.
     The allowed values below must match the list in theme-init.js.
     ------------------------------------------------------------------ */
  var STORE_KEY = 'tmd-layout';
  /* "fallback" is the first-visit look the client approved (light mode,
     full width, standard sidebar, purple sidebar), and what Reset returns
     to. theme-init.js sets the same defaults before first paint. */
  var SETTINGS = {
    theme: { attr: 'data-theme', values: ['light', 'dark'], fallback: 'light' },
    width: { attr: 'data-width', values: ['full', 'boxed'], fallback: 'full' },
    navSize: { attr: 'data-nav-size', values: ['standard', 'compact', 'icons'], fallback: 'standard' },
    navTone: { attr: 'data-nav-tone', values: ['light', 'dark', 'purple'], fallback: 'purple' }
  };
  /* The radio names in the settings panel, mapped to the keys above. */
  var RADIO_KEYS = { theme: 'theme', width: 'width', 'nav-size': 'navSize', 'nav-tone': 'navTone' };
  /* The size chosen in the settings panel (theme-init.js already put the
     saved one on <html>). */
  var chosenNavSize = root.getAttribute('data-nav-size') || 'standard';

  function currentTheme() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function save() {
    var data = {};
    Object.keys(SETTINGS).forEach(function (key) {
      var value = key === 'navSize' ? chosenNavSize : root.getAttribute(SETTINGS[key].attr);
      if (value) { data[key] = value; }
    });
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (err) { /* storage blocked */ }
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
    try { window.localStorage.removeItem(STORE_KEY); } catch (err) { /* storage blocked */ }
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
     3. Colour-mode button (top bar, sign-in page)
     ------------------------------------------------------------------ */
  var themeButtons = qsa('[data-theme-toggle]');

  function syncThemeButtons() {
    var dark = currentTheme() === 'dark';
    themeButtons.forEach(function (button) {
      var label = qs('[data-theme-label]', button);
      var use = qs('use', button);
      if (label) { label.textContent = dark ? 'Switch to light mode' : 'Switch to dark mode'; }
      if (use) { use.setAttribute('href', dark ? '#i-sun' : '#i-moon'); }
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
     come from the browser. Focus goes back to whatever opened it.
     ------------------------------------------------------------------ */
  var sheet = qs('[data-settings]');
  var sheetOpener = null;

  function syncRadios() {
    if (!sheet) { return; }
    qsa('input[data-setting]', sheet).forEach(function (input) {
      var key = RADIO_KEYS[input.name];
      var value = key === 'theme' ? currentTheme() : root.getAttribute(SETTINGS[key].attr);
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
      input.addEventListener('change', function () {
        if (!input.checked) { return; }
        setSetting(RADIO_KEYS[input.name], input.value);
      });
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
     and the size chosen in the settings panel (or Standard, when the chosen
     size is itself "icons only"). This is not saved: a reload shows the
     chosen size again. The panel's radios still show what is on screen.
     On phone it opens the sidebar as a drawer over the page.
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
      syncAll();
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

    /* Arriving with #nav in the address (the no-script menu link) should not
       leave the drawer stuck open without its scrim. */
    if (window.location.hash === '#nav' && window.history.replaceState) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }

  /* ------------------------------------------------------------------
     6. Dropdowns. <details data-pop> already opens and closes without a
     script; this adds one-at-a-time, Escape, and click-outside.
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
     7. Toast. It never times out; Close and Undo dismiss it.
     ------------------------------------------------------------------ */
  qsa('[data-flash]').forEach(function (flash) {
    qsa('[data-flash-undo]', flash).forEach(function (button) { button.hidden = false; });
    qsa('[data-flash-close], [data-flash-undo]', flash).forEach(function (button) {
      button.addEventListener('click', function () { flash.hidden = true; });
    });
  });

  /* ------------------------------------------------------------------
     8. Error summary links move focus into the field, not just scroll.
     ------------------------------------------------------------------ */
  qsa('[data-error-link]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      var target = doc.getElementById(link.getAttribute('href').slice(1));
      if (!target) { return; }
      event.preventDefault();
      target.focus();
    });
  });

  /* ------------------------------------------------------------------
     9. ?demo= state hooks. Prototype only: they let the owner and the
     verifier reach the error, empty and success states without a server.
     They are never carried into templates/.
     ------------------------------------------------------------------ */
  var demo = null;
  try { demo = new URLSearchParams(window.location.search).get('demo'); } catch (err) { demo = null; }

  if (demo) {
    qsa('[data-demo="' + demo + '"]').forEach(function (el) { el.hidden = false; });
    qsa('[data-demo-hide="' + demo + '"]').forEach(function (el) { el.hidden = true; });
    qsa('[data-demo-fill="' + demo + '"]').forEach(function (field) {
      field.value = field.getAttribute('data-demo-value') || '';
    });
    qsa('[data-demo-check="' + demo + '"]').forEach(function (field) { field.checked = true; });
    qsa('[data-demo-text="' + demo + '"]').forEach(function (el) {
      el.textContent = el.getAttribute('data-demo-value') || '';
    });
    qsa('[data-demo-invalid="' + demo + '"]').forEach(function (field) {
      var extra = field.getAttribute('data-demo-describedby') || '';
      var described = (field.getAttribute('aria-describedby') || '') + ' ' + extra;
      field.setAttribute('aria-invalid', 'true');
      field.setAttribute('aria-describedby', described.trim());
    });
    var focusTarget = qs('[data-demo-focus="' + demo + '"]');
    if (focusTarget) { focusTarget.focus(); }
  }

  syncAll();
})();
