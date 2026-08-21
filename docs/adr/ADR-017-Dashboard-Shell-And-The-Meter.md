# ADR-017 — A side rail, one grid instead of two, and no third dimension

**Status:** accepted · **Date:** 2026-08-20

## Context

Three problems, found by using the thing rather than by reading it.

1. **The page is long and had no landmarks.** Getting from the KPI strip to
   "what to change" was a scroll with nothing to aim at and no way back. The
   two page-level settings — theme, language — had nowhere to live except
   floating over the data.
2. **Two charts answered the same question.** "Working hours" plotted weekday ×
   hour. The product's central claim is that *the hour decides the price*. The
   chart that showed the hours and the argument about what they cost were in
   different panels, so the reader had to hold one in their head while looking
   at the other.
3. **The daily chart cannot show a year.** It is a bar per day; a range wide
   enough to show a habit forming compresses each bar below a pixel. "Am I
   busier than I was in March" was unanswerable on a page about behaviour over
   time.

## Decision

### 1. A persistent side rail

Eight sections, icon plus a short caption, lit by a scroll spy. It carries the
brand mark (which is also the link home), the language switcher and the theme
toggle. On a phone it becomes a horizontally scrolling strip in the same order
— nothing moves into a hidden menu.

Borrowed deliberately from an existing internal dashboard that had already
proved the pattern on a page of this depth: same shape at every scroll
position, so it becomes muscle memory rather than a thing to re-read.

### 2. The meter replaces the working-hours heatmap

One grid, not two. The weekday × hour heatmap now has each vendor's peak
window drawn behind it as a tinted column, and every busy cell inside one of
those columns carries a red ring.

Volume stays encoded by opacity and *only* by opacity; "expensive" is a ring.
Two facts, two channels — if price also changed the fill, the reader could no
longer tell a busy cheap hour from a quiet expensive one.

Underneath, two sentences the picture cannot say on its own: what share of
turns land at peak, and which off-peak hours the reader *already* works in.
The second is the actionable half. "Move your batch work" is advice; "you
already work at 12:00, 18:00 and 19:00, and those are half price" is a plan.

**The overlay is a mask over (weekday, hour), not over hour.** GLM peaks
14:00–18:00 UTC+8 on weekdays *only*; weekends are entirely off-peak. A window
treated as a flat set of hours ringed Saturday and Sunday cells that were never
charged a premium — a false positive, which is the one class of error this
product cannot afford. The timezone shift moves the weekday as well as the
hour: 23:00 UTC Monday is 07:00 Tuesday at UTC+8.

**And it only appears if the reader uses a time-priced vendor.** Most people
use none. Drawing DeepSeek's window over their week invents a problem they
cannot have. When no vendor in the current filter prices by the hour the panel
becomes plain "Working hours" — no bands, no rings, no phase in the tooltips —
and says so: *"None of the vendors you used price by the hour, so no hour here
cost more than another."* That is a useful finding in its own right, and it is
one the reader can act on the day they add a vendor that does. The two states
swap on any filter change, so narrowing to a single provider answers "does this
apply to me" directly.

This required the peak schedules to travel inside the digest, and the engine to
record which *providers* bill on each window — a window is keyed by vendor
(`zhipu`) and an event carries a provider (`glm`), and nothing downstream could
bridge those two names.

### 3. A calendar heatmap, in the rhythm section

One square per day, GitHub-style, under the daily bars. It answers the
year-scale question the bar chart structurally cannot, and clicking a week
filters the page to it — the same drill-down grammar the daily bars already
teach.

It sits with the daily chart rather than in a section of its own because it is
the same question at a different zoom, and splitting them would make the reader
choose between two answers to "when do I work" before knowing they differ.

**All seven weekdays are labelled.** GitHub labels only Mon/Wed/Fri, because at
10px squares seven labels collide. That trade buys tidiness and charges the
reader for it: they count rows to decide whether a dark square is a Tuesday or
a Thursday, which is the question the chart exists to answer. We spend three
more pixels of pitch and label all seven.

**Month boundaries get a hairline, which GitHub does not have.** GitHub relies
on the label row alone — fine at a glance, poor when you are trying to say
"that spike was in July". Label and rule anchor to the same week column, so
they cannot disagree; both mark the first column containing a day of the new
month, which is an approximation, since a month starts mid-week six times in
seven, and is the same approximation the label was already making.

### 4. Not 3D

The well-known version of this chart extrudes each day into a block whose
height is the volume. Rejected, for reasons this repo already wrote down: a
quantitative chart gains nothing from a third dimension it does not have data
for, and loses the property the grid exists to provide — that any two days can
be compared at a glance. In an oblique projection the back rows are occluded by
the front ones, the perspective makes equal values look unequal, and rotating
to see the hidden rows costs the reader an interaction to recover information a
flat grid never hid.

The same reasoning killed a 3D option for the meter. Volume × hour × weekday is
three variables, which sounds like a case for three axes; but the comparison
that matters is *between adjacent cells*, and that is exactly what depth
destroys.

## Consequences

**Good.** The rail makes the page navigable and gives the settings a home. The
meter makes the product's core argument in one picture using the reader's own
data. The calendar adds a time scale the page did not have. The filter bar
holds one line at realistic widths, having dropped a caption column that cost
~240px and bought nothing a screen reader wanted.

**Costs.** The dashboard now carries a scroll spy and an extra chart, and the
digest carries the window table. Both are small; the page is still one
self-contained file with no network calls.

**A limit worth stating.** The meter marks a cell as peak if *any* time-priced
vendor in the current filter charges peak then. With two such vendors whose
windows differ, a ringed cell means "somebody charged you extra here", not
"everything in this cell was expensive". The tooltip names which vendors, which
is the honest resolution; a per-vendor grid would be four charts nobody reads.
Filtering to one provider collapses the ambiguity entirely.

## Revisit when

- A reader has more than two time-priced vendors and the merged peak band stops
  being legible — that is when the per-vendor split earns its complexity.
- The calendar covers more than about two years and the squares need a smaller
  cell or a year selector.
