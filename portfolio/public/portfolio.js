// dnesting.com portfolio — light interactions, no framework.
(function () {
  "use strict";

  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Flag the document as JS-capable so CSS can opt into the hidden reveal
  // state. Without this, content stays fully visible if JS never runs.
  document.body.classList.add("js");

  // Theme toggle. The saved theme is applied pre-paint by an inline head
  // script; here we just let the button flip and persist it.
  var toggle = document.querySelector("[data-theme-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var light = document.documentElement.classList.toggle("theme-light");
      try { localStorage.setItem("theme", light ? "light" : "dark"); } catch (e) {}
    });
  }

  // Scroll-reveal via IntersectionObserver.
  var revealables = document.querySelectorAll("[data-reveal]");
  if (reduce || !("IntersectionObserver" in window)) {
    revealables.forEach(function (el) { el.classList.add("in-view"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    revealables.forEach(function (el) { io.observe(el); });
  }

  // Nav gains a border/background once the page scrolls.
  var nav = document.querySelector("[data-nav]");
  if (nav) {
    var onScroll = function () {
      nav.classList.toggle("scrolled", window.scrollY > 12);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }
})();
