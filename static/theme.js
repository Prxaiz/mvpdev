(function () {
  var KEY = "ui-theme";
  var root = document.documentElement;

  function getStored() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null;
    }
  }

  function setStored(v) {
    try {
      localStorage.setItem(KEY, v);
    } catch (e) {}
  }

  function syncButton() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var dark = root.dataset.theme === "dark";
    btn.textContent = dark ? "Light" : "Dark";
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    btn.setAttribute("aria-pressed", dark ? "true" : "false");
  }

  function onReady() {
    syncButton();

    document.getElementById("theme-toggle")?.addEventListener("click", function () {
      var next = root.dataset.theme === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      setStored(next);
      syncButton();
    });

    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", function (e) {
        if (getStored() === "light" || getStored() === "dark") return;
        root.dataset.theme = e.matches ? "dark" : "light";
        syncButton();
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }
})();
