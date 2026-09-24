/*
  Applies the saved layout settings before the first paint.

  Why a separate, blocking file: the page must not flash light and then turn
  dark, or show a wide sidebar and then shrink it. This runs in <head> before
  style.css, so it does one thing only: read "tmd-layout" and copy the four
  allowed values onto <html>. Everything else is in app.js.
*/
(function () {
  /* Keep these values in step with SETTINGS in app.js (block 2). */
  var allowed = {
    theme: ['data-theme', ['light', 'dark']],
    width: ['data-width', ['full', 'boxed']],
    navSize: ['data-nav-size', ['standard', 'compact', 'icons']],
    navTone: ['data-nav-tone', ['light', 'dark', 'purple']]
  };
  try {
    var saved = JSON.parse(window.localStorage.getItem('tmd-layout') || '{}');
    var root = document.documentElement;
    Object.keys(allowed).forEach(function (key) {
      var rule = allowed[key];
      if (saved && rule[1].indexOf(saved[key]) !== -1) {
        root.setAttribute(rule[0], saved[key]);
      }
    });
  } catch (err) {
    /* Storage blocked or the value is not JSON: keep the defaults. */
  }
})();
