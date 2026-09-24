/*
  Polymath TMD: apply the saved layout settings before the first paint.

  Why a separate, blocking file: the page must not flash light and then turn
  dark, or show a wide sidebar and then shrink it. base.html loads it in
  <head> before style.css, without defer or async, so it does one thing only:
  read "tmd-layout" from localStorage and copy the four allowed values onto
  <html>. With nothing saved, the server's attributes (the client-approved
  look: light, full width, standard sidebar, purple sidebar) are what you
  get; the device's colour scheme is never followed.

  Why it also publishes window.tmdLayout: the allowed values and defaults
  must live in one place (brief 004, criterion 5). app.js reads them from
  here instead of keeping its own copy.
*/
(function () {
  'use strict';

  /* Each setting: the <html> attribute, the allowed values, the default. */
  var settings = {
    theme: { attr: 'data-theme', values: ['light', 'dark'], fallback: 'light' },
    width: { attr: 'data-width', values: ['full', 'boxed'], fallback: 'full' },
    navSize: { attr: 'data-nav-size', values: ['standard', 'compact', 'icons'], fallback: 'standard' },
    navTone: { attr: 'data-nav-tone', values: ['light', 'dark', 'purple'], fallback: 'purple' }
  };
  var key = 'tmd-layout';

  window.tmdLayout = { key: key, settings: settings };

  try {
    var saved = JSON.parse(window.localStorage.getItem(key) || '{}') || {};
    var root = document.documentElement;
    Object.keys(settings).forEach(function (name) {
      var rule = settings[name];
      var value = rule.values.indexOf(saved[name]) !== -1 ? saved[name] : rule.fallback;
      root.setAttribute(rule.attr, value);
    });
  } catch (err) {
    /* Storage blocked or the value is not JSON: keep the server's defaults. */
  }
})();
