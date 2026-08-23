/* Setup page: a checklist that remembers where you got to.
 *
 * The funnel here is not lost to difficulty, it is lost to uncertainty — people
 * stop because they cannot tell whether the last command worked, or how much is
 * left, or what they are supposed to be looking at. So the page tracks three
 * things and nothing else: which step is open, which are done, and how far
 * along the bar is.
 *
 * Progress lives in localStorage. Setup spans a browser and a terminal, and
 * people switch windows, close tabs and come back tomorrow; starting them over
 * because of that would be the rudest possible response to an interruption.
 *
 * Degrades completely. Without this file every step is expanded, every command
 * is selectable, and the page reads top to bottom as ordinary instructions. */
(function () {
"use strict";

var doc = document;
var steps = doc.getElementById("steps");
if (!steps) return;

var KEY = "observatory-setup-done";
var TOTAL = 3;
var TITLES = ["Get it running", "See your own numbers", "Keep it one click away"];

var fill = doc.getElementById("stepfill");
var now = doc.getElementById("stepnow");
var reset = doc.getElementById("stepreset");
var donecard = doc.getElementById("donecard");

function read() {
  try {
    var n = parseInt(localStorage.getItem(KEY), 10);
    return isFinite(n) && n >= 0 && n <= TOTAL ? n : 0;
  } catch (e) { return 0; }
}
function write(n) {
  try { localStorage.setItem(KEY, String(n)); } catch (e) { /* private mode */ }
}

var done = read();

function paint(opts) {
  var cards = steps.querySelectorAll(".step");
  for (var k = 0; k < cards.length; k++) {
    var n = parseInt(cards[k].getAttribute("data-step"), 10);
    /* Exactly one step is open: the first unfinished one. Collapsing the rest
       is not decoration — an open accordion of three terminal blocks is how
       somebody pastes step 3 into step 1's window. */
    cards[k].classList.toggle("is-done", n <= done);
    cards[k].classList.toggle("is-open", n === done + 1);
  }

  var pct = Math.round((done / TOTAL) * 100);
  if (fill) fill.style.width = pct + "%";
  if (now) {
    now.textContent = done >= TOTAL
      ? "All three done — you're set up"
      : "Step " + (done + 1) + " of " + TOTAL + " · " + TITLES[done];
  }
  if (reset) reset.hidden = done === 0;
  if (donecard) donecard.hidden = done < TOTAL;

  /* Only scroll when the reader just finished something. Doing it on load
     would yank a returning visitor past the context they came back to re-read. */
  if (opts && opts.advance) {
    var next = done >= TOTAL ? donecard : doc.getElementById("step" + (done + 1));
    if (next && next.scrollIntoView) {
      next.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }
}

steps.addEventListener("click", function (e) {
  var btn = e.target.closest ? e.target.closest("[data-done-step]") : null;
  if (btn) {
    var n = parseInt(btn.getAttribute("data-done-step"), 10);
    /* Highest completed step wins, so re-confirming step 1 cannot silently
       undo steps 2 and 3 for somebody scrolling back over their own work. */
    done = Math.max(done, n);
    write(done);
    paint({ advance: true });
    return;
  }
  /* A finished step's header reopens it — the commands are still there, and
     somebody who wants to re-run one should not have to start over to see it. */
  var head = e.target.closest ? e.target.closest(".stephead") : null;
  if (head && head.parentNode.classList.contains("is-done")) {
    head.parentNode.classList.toggle("is-open");
  }
});

if (reset) {
  reset.addEventListener("click", function () {
    done = 0; write(0); paint({ advance: false });
    steps.scrollIntoView({ behavior: "smooth", block: "start" });
  });
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

paint({ advance: false });
})();
