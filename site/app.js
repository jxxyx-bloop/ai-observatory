/* Landing page behaviour. Four small things, no dependencies, no network —
   the same constraints the dashboard runs under. Everything degrades: without
   this file the page is still readable, navigable and translated. */
(function () {
"use strict";
var doc = document, root = doc.documentElement;
var $ = function (id) { return doc.getElementById(id); };

/* ---- theme -------------------------------------------------------------
   The stamp already happened in <head> so there is no flash; this only wires
   the toggle and remembers the choice. The key is shared with the dashboard,
   so choosing dark here carries into the demo. */
var theme = $("theme");
if (theme) {
  theme.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("observatory-theme", next); } catch (e) {}
  });
}

/* ---- language ----------------------------------------------------------
   Each locale is its own page, so the switch is a plain link — good for
   search engines and for anyone with scripting off. The click is recorded
   only so the dashboard, which is one page for every locale, can open in the
   language you were just reading. */
/* Reading a page IS choosing its language. Someone who arrives at /th/ from a
   search result never touches the switcher, so without this the demo would open
   in English for them — which is exactly the reader this whole effort is for. */
try { localStorage.setItem("observatory-lang", root.lang || "en"); } catch (e) {}

var menu = $("langmenu");
if (menu) {
  menu.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a[data-lang]") : null;
    if (!a) return;
    try { localStorage.setItem("observatory-lang", a.getAttribute("data-lang")); } catch (err) {}
  });
  doc.addEventListener("click", function (e) {
    if (menu.open && !menu.contains(e.target)) menu.open = false;
  });
  doc.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
  });
}

/* ---- finding deck ------------------------------------------------------
   One finding is the product's whole pitch; three of them make the point that
   it is a ranked list rather than a lucky example, so it cycles on its own —
   nobody should have to click just to see the other two. It pauses the
   instant a pointer or keyboard focus lands anywhere on the deck or its
   controls, because a card that moves out from under someone reading it is
   worse than no motion, and resumes the moment they leave rather than
   staying stopped for the rest of the page view. Skipped entirely for
   prefers-reduced-motion, same as every other animation on this page. */
var deck = $("deck");
if (deck) {
  var cards = [].slice.call(deck.querySelectorAll(".find"));
  var dots = $("dots"), i = 0, timer = null;
  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (cards.length > 1 && dots) {
    cards.forEach(function (card, n) {
      var b = doc.createElement("button");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-label", String(n + 1));
      b.addEventListener("click", function () { show(n); });
      dots.appendChild(b);
    });

    show(0);
    if (!reduceMotion) start();

    var prev = $("prev"), next = $("next");
    if (prev) prev.addEventListener("click", function () { show(i - 1); });
    if (next) next.addEventListener("click", function () { show(i + 1); });

    if (!reduceMotion) {
      // The whole act — card plus its arrows and dots — pauses as one region;
      // a reader aiming for the "next" arrow should not have the card change
      // under their cursor first.
      var act = $("finding") || deck;
      act.addEventListener("mouseenter", stop);
      act.addEventListener("mouseleave", start);
      act.addEventListener("focusin", stop);
      act.addEventListener("focusout", function (e) {
        if (!act.contains(e.relatedTarget)) start();
      });
    }
  } else {
    cards.forEach(function (c) { c.classList.add("on"); });
  }

  function show(n) {
    i = (n + cards.length) % cards.length;
    cards.forEach(function (c, k) {
      c.classList.toggle("on", k === i);
      c.setAttribute("aria-hidden", k === i ? "false" : "true");
    });
    if (!dots) return;
    [].forEach.call(dots.children, function (b, k) {
      b.setAttribute("aria-selected", k === i ? "true" : "false");
    });
  }
  function start() { if (!timer) timer = setInterval(function () { show(i + 1); }, 7000); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
}

/* ---- reveal on scroll --------------------------------------------------
   A short rise as each section arrives. IntersectionObserver only — no scroll
   listener — and skipped entirely where it is unsupported or unwanted, in
   which case everything is simply already visible. */
var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!reduce && "IntersectionObserver" in window) {
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      en.target.style.transition = "opacity .5s var(--ease), transform .5s var(--ease)";
      en.target.style.opacity = "1";
      en.target.style.transform = "none";
      io.unobserve(en.target);
    });
  }, {rootMargin: "0px 0px -12% 0px"});

  [].forEach.call(doc.querySelectorAll("main section:not(.hero)"), function (s) {
    s.style.opacity = "0";
    s.style.transform = "translateY(14px)";
    io.observe(s);
  });
}
})();
