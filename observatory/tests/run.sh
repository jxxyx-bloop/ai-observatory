#!/usr/bin/env bash
# Every check in the repo. No dependencies beyond python3; the dashboard smoke
# test is skipped when node is absent rather than failing the run.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== engine =="
python3 tests/test_engine.py

echo
echo "== collector specs =="
python3 tests/test_specs.py

echo
echo "== provider collectors =="
for t in tests/test_*_code.py; do
  [ -e "$t" ] || continue
  echo "-- $t"; python3 "$t"
done

echo
echo "== dashboard =="
if command -v node >/dev/null 2>&1; then
  tmp="$(mktemp -d)"
  python3 - "$tmp" <<'PY'
import sys, pathlib
sys.path.insert(0, ".")
import analyze, demo, insights, normalize, pricing, render
data = pathlib.Path(sys.argv[1])
normalize.write_events(data, demo.generate(days=30))
p = pricing.load_pricing()
d = analyze.build_digest(normalize.read_events(data), p)
d["findings"] = insights.generate(d, p)
d["settings"] = {"tz_label": "UTC+8", "symbol": "$", "per_usd": 1, "decimals": 2,
                 "currency": "USD", "plan": "none"}
(data / "report.html").write_text(render.render(d), encoding="utf-8")
PY
  node tests/dashboard_smoke.js "$tmp/report.html" assets/app.js
  rm -rf "$tmp"
else
  echo "  (skipped — node not installed)"
fi

echo
echo "all suites passed"
