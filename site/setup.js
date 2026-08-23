/* Setup page: one confirmation, and copy buttons that behave.
 *
 * There used to be a three-step checklist here. There is one command now, so
 * tracking "which step are you on" would be tracking nothing — the only state
 * worth keeping is whether the reader got their dashboard open, because that is
 * what unlocks the "what happens tomorrow" card. Everything a first-timer needs
 * to *read* is visible without JavaScript; this only reveals what is relevant
 * once they are through.
 *
 * Remembered in localStorage: someone who set this up last week and came back
 * for the Dock instructions should land on them, not on the install again.
 *
 * Degrades completely. Without this file the command is selectable, the phases
 * read top to bottom, and the after-care card is simply always shown. */
(function () {
"use strict";

var doc = document;
var btn = doc.getElementById("setupdone");
var card = doc.getElementById("donecard");
if (!card) return;

/* Hide it up front, now that we know the script is running to reveal it. */
if (btn) card.hidden = true;

var KEY = "observatory-setup-done";
function read() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
function write() { try { localStorage.setItem(KEY, "1"); } catch (e) {} }

function reveal(scroll) {
  card.hidden = false;
  if (btn) btn.hidden = true;
  if (scroll && card.scrollIntoView) {
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

if (read()) {
  reveal(false);
} else if (btn) {
  btn.addEventListener("click", function () { write(); reveal(true); });
}

/* Copy buttons: a brief "working" beat before "Copied".
 *
 * The copy itself is instant, so the pause is honest about something else —
 * it is the moment the reader's attention moves from this page to their
 * terminal, and a button that changes under them without a transition reads as
 * a glitch rather than a confirmation. */
var btns = doc.querySelectorAll(".setuppage [data-copy]");
[].forEach.call(btns, function (btn) {
  btn.addEventListener("click", function () {
    var box = btn.parentNode.querySelector("code");
    if (!box || btn.classList.contains("busy")) return;
    var text = box.textContent;
    var label = btn.getAttribute("data-label") || btn.textContent;
    btn.setAttribute("data-label", label);

    var settle = function (okText, cls) {
      btn.classList.remove("busy");
      btn.classList.add(cls);
      btn.textContent = okText;
      setTimeout(function () {
        btn.classList.remove(cls);
        btn.textContent = label;
      }, 2200);
    };

    btn.classList.add("busy");
    btn.textContent = "…";

    var copied = false;
    try {
      var ta = doc.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", "");
      ta.style.cssText = "position:absolute;left:-9999px";
      doc.body.appendChild(ta); ta.select();
      copied = doc.execCommand("copy");
      doc.body.removeChild(ta);
    } catch (e) { copied = false; }

    if (copied) {
      setTimeout(function () { settle(btn.getAttribute("data-done") || "Copied", "ok"); }, 260);
      return;
    }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(
        function () { settle(btn.getAttribute("data-done") || "Copied", "ok"); },
        function () { settle("Select and copy", "warn"); }
      );
      return;
    }
    /* Never leave the button spinning. If the clipboard is unavailable — some
       browsers block it outright on http:// — say so and select the text, so
       the fallback is one keystroke rather than a dead end. */
    settle("Select and copy", "warn");
    try {
      var r = doc.createRange(); r.selectNodeContents(box);
      var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
    } catch (e) { /* selection is a nicety, not a requirement */ }
  });
});

})();
