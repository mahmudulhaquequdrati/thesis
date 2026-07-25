"""Render the dataset to a single self-contained HTML file.

    uv run python scripts/make_viewer.py && open data/viewer.html

Everything is inlined -- data as JSON, CSS and JS in the page. No CDN, no
server, no network request of any kind, so the page works offline and can be
opened straight off disk.

It reads through carr/db.py's helpers, the same ones scripts/view.py uses,
so the terminal and the browser can never disagree about what the data says.
The page is regenerated, never hand-edited; data/viewer.html is gitignored.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carr import db  # noqa: E402

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARR dataset inspector</title>
<style>
:root {
  --bg:#fbfbfa; --panel:#fff; --line:#e3e3e0; --fg:#1a1a18; --dim:#6b6b66;
  --accent:#2f6f4f; --bad:#a33; --warn:#a6791f; --code:#f4f4f2;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#16171a; --panel:#1d1f23; --line:#2e3137; --fg:#e6e6e3;
          --dim:#9a9a94; --accent:#6fbf90; --bad:#e0817d; --warn:#d8b25e;
          --code:#131417; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5
  ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif; }
code, pre, .mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
header { padding:14px 20px; border-bottom:1px solid var(--line);
  background:var(--panel); display:flex; gap:16px; align-items:center;
  flex-wrap:wrap; position:sticky; top:0; z-index:5; }
header h1 { font-size:15px; margin:0; font-weight:600; }
.badge { font-size:11px; padding:2px 8px; border-radius:10px;
  border:1px solid var(--warn); color:var(--warn); font-weight:600;
  letter-spacing:.04em; }
.stats { color:var(--dim); font-size:12px; margin-left:auto; }
.wrap { display:flex; align-items:flex-start; }
aside { width:270px; flex:none; border-right:1px solid var(--line);
  height:calc(100vh - 55px); overflow-y:auto; position:sticky; top:55px;
  background:var(--panel); }
aside .filters { padding:10px; border-bottom:1px solid var(--line);
  display:flex; flex-direction:column; gap:6px; }
aside input:not([type=checkbox]), aside select { width:100%; padding:5px 7px;
  font-size:12px; background:var(--bg); color:var(--fg);
  border:1px solid var(--line); border-radius:4px; }
aside label { font-size:12px; color:var(--dim); display:flex; gap:6px;
  align-items:center; cursor:pointer; }
aside input[type=checkbox] { width:auto; margin:0; flex:none; }
.pitem { padding:7px 11px; border-bottom:1px solid var(--line); cursor:pointer;
  display:flex; justify-content:space-between; gap:8px; align-items:baseline; }
.pitem:hover { background:var(--bg); }
.pitem.on { background:var(--bg); box-shadow:inset 3px 0 0 var(--accent); }
.pitem .id { font-size:12.5px; }
.pitem .sub { font-size:11px; color:var(--dim); }
main { flex:1; padding:18px 22px; min-width:0; max-width:1100px; }
h2 { font-size:17px; margin:0 0 3px; }
.meta { color:var(--dim); font-size:12.5px; margin-bottom:16px; }
.sec { font-size:11px; text-transform:uppercase; letter-spacing:.07em;
  color:var(--dim); margin:20px 0 7px; font-weight:600; }
pre { background:var(--code); border:1px solid var(--line); border-radius:6px;
  padding:11px 13px; overflow-x:auto; font-size:12.5px; margin:0;
  white-space:pre-wrap; word-break:break-word; }
table { width:100%; border-collapse:collapse; font-size:12.5px; }
th { text-align:left; color:var(--dim); font-weight:600; padding:5px 7px;
  border-bottom:1px solid var(--line); white-space:nowrap; font-size:11px;
  text-transform:uppercase; letter-spacing:.04em; }
td { padding:5px 7px; border-bottom:1px solid var(--line); white-space:nowrap; }
tbody tr { cursor:pointer; }
tbody tr:hover { background:var(--panel); }
tbody tr.on { background:var(--panel); box-shadow:inset 3px 0 0 var(--accent); }
.num { text-align:right; }
.pass { color:var(--accent); font-weight:600; }
.fail { color:var(--bad); font-weight:600; }
.skip { color:var(--warn); font-weight:600; }
.tag { font-size:10.5px; color:var(--dim); border:1px solid var(--line);
  padding:0 5px; border-radius:8px; }
.target { margin-top:13px; padding:10px 13px; border-radius:6px;
  border:1px solid var(--accent); background:var(--panel); font-size:13px; }
.detail { margin-top:26px; border-top:2px solid var(--line); padding-top:16px; }
details { margin:0; } summary { cursor:pointer; color:var(--dim);
  font-size:12px; padding:4px 0; }
.kv { display:grid; grid-template-columns:auto 1fr; gap:2px 16px;
  font-size:12.5px; }
.kv dt { color:var(--dim); } .kv dd { margin:0; }
.note { color:var(--dim); font-size:12px; font-style:italic; }
.scroll { overflow-x:auto; }
</style></head><body>
<header>
  <h1>CARR dataset inspector</h1>
  <span class="badge" id="mockBadge"></span>
  <span class="stats" id="stats"></span>
</header>
<div class="wrap">
  <aside>
    <div class="filters">
      <input id="q" placeholder="filter problems...">
      <select id="bench"><option value="">all benchmarks</option></select>
      <label><input type="checkbox" id="unsolved"> only unsolved</label>
    </div>
    <div id="plist"></div>
  </aside>
  <main id="main"></main>
</div>
<script id="payload" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const esc = s => (s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const usd = v => v == null ? '-' : '$' + v.toFixed(6);
const num = v => v == null ? '-' : v.toLocaleString();
let selected = DATA.problems[0]?.problem_id, selectedRow = 0;

const m = DATA.meta;
document.getElementById('stats').textContent =
  `${m.n_problems} problems | ${m.n_configs} configs | ${m.n_generations} generations `
  + `| ${m.n_passed} passed | real spend $${m.real_spend_usd.toFixed(4)} | ${m.generated_at}`;
const badge = document.getElementById('mockBadge');
if (m.mock_generations > 0) {
  badge.textContent = `MOCK DATA - ${m.mock_generations}/${m.n_generations} rows generated offline, not purchased`;
} else { badge.remove(); }

const benchSel = document.getElementById('bench');
[...new Set(DATA.problems.map(p => p.benchmark))].sort().forEach(b => {
  const o = document.createElement('option'); o.value = o.textContent = b;
  benchSel.appendChild(o);
});

function visible() {
  const q = document.getElementById('q').value.toLowerCase();
  const b = benchSel.value;
  const un = document.getElementById('unsolved').checked;
  return DATA.problems.filter(p =>
    (!q || p.problem_id.toLowerCase().includes(q) || p.entry_point.toLowerCase().includes(q))
    && (!b || p.benchmark === b) && (!un || p.n_passed === 0));
}

function renderList() {
  const el = document.getElementById('plist');
  el.innerHTML = visible().map(p => `
    <div class="pitem ${p.problem_id === selected ? 'on' : ''}" data-id="${esc(p.problem_id)}">
      <div><div class="id mono">${esc(p.problem_id)}</div>
           <div class="sub">${esc(p.entry_point)}() &middot; ${num(p.n_tests)} tests</div></div>
      <div class="sub ${p.n_passed ? 'pass' : 'fail'}">${p.n_passed}/${p.n_gens}</div>
    </div>`).join('') || '<div class="pitem sub">no matches</div>';
  el.querySelectorAll('.pitem[data-id]').forEach(d => d.onclick = () => {
    selected = d.dataset.id; selectedRow = 0; renderList(); renderMain();
  });
}

function grade(r) {
  if (r.passed === null) return '<span class="skip">SKIP</span>';
  return r.passed ? '<span class="pass">PASS</span>' : '<span class="fail">FAIL</span>';
}

function renderMain() {
  const p = DATA.problems.find(x => x.problem_id === selected);
  const el = document.getElementById('main');
  if (!p) { el.innerHTML = '<p class="note">Select a problem.</p>'; return; }

  const rows = p.rows.map((r, i) => `
    <tr data-i="${i}" class="${i === selectedRow ? 'on' : ''}">
      <td class="mono">${esc(r.model_slug)}</td>
      <td>${esc(r.effort_label)}</td>
      <td class="num">${num(r.completion_tokens)}</td>
      <td class="num">${num(r.reasoning_tokens)}</td>
      <td class="num mono">${usd(r.cost_computed_usd)}</td>
      <td class="num">${num(r.latency_ms)}</td>
      <td>${grade(r)}</td>
      <td class="num">${r.passed === null ? esc(r.error || 'no code')
          : r.n_tests_passed + '/' + r.n_tests_total}</td>
      <td>${r.mock_mode ? `<span class="tag">${esc(r.mock_mode)}</span>` : ''}</td>
    </tr>`).join('');

  const t = p.cheapest
    ? `<div class="target"><strong>Routing target</strong> &mdash; cheapest config that
       solved this: <span class="pass mono">${esc(t_label(p.cheapest))}</span>
       at <span class="mono">${usd(p.cheapest.cost_computed_usd)}</span>.
       <span class="note">This is the label CARR learns to predict.</span></div>`
    : `<div class="target" style="border-color:var(--warn)">
       <strong>No config solved this problem</strong> &mdash; it carries no routing
       label and is excluded from the router's training set.</div>`;

  el.innerHTML = `
    <h2 class="mono">${esc(p.problem_id)} &middot; ${esc(p.entry_point)}()</h2>
    <div class="meta">${esc(p.benchmark)} &middot; ${num(p.n_base_tests)} base +
      ${num(p.n_plus_tests)} plus = ${num(p.n_tests)} test inputs &middot;
      prompt ${num(p.prompt_chars)} chars
      <span class="note">&mdash; test inputs are never sent to the model</span></div>

    <div class="sec">Prompt sent to the model (verbatim)</div>
    <pre>${esc(p.prompt)}</pre>

    <div class="sec">Configs</div>
    <div class="scroll"><table><thead><tr>
      <th>model</th><th>effort</th><th class="num">out tok</th>
      <th class="num">reasoning</th><th class="num">cost</th><th class="num">ms</th>
      <th>grade</th><th class="num">tests</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table></div>
    ${t}
    <div class="detail" id="detail"></div>`;

  el.querySelectorAll('tbody tr').forEach(tr => tr.onclick = () => {
    selectedRow = +tr.dataset.i; renderMain();
  });
  renderDetail(p);
}

function t_label(c) { return c.model_slug + ' | ' + c.effort_label; }

function renderDetail(p) {
  const r = p.rows[selectedRow];
  const el = document.getElementById('detail');
  if (!r) { el.innerHTML = ''; return; }
  const pct = r.completion_tokens
    ? Math.round(100 * (r.reasoning_tokens || 0) / r.completion_tokens) : 0;

  el.innerHTML = `
    <h2 class="mono">${esc(r.model_slug)} | ${esc(r.effort_label)}</h2>
    <div class="meta">${r.is_mock
      ? '<span class="skip">MOCK ROW &mdash; generated offline, not purchased'
        + (r.mock_mode ? ' (mode: ' + esc(r.mock_mode) + ')' : '') + '</span>'
      : 'real generation'}</div>

    <div class="sec">Raw response <span class="note">(stored verbatim, so re-grading is free)</span></div>
    ${r.error ? `<pre class="fail">error: ${esc(r.error)}</pre>`
              : `<pre>${esc(r.raw_response)}</pre>`}

    <div class="sec">Extracted code <span class="note">(what actually gets executed)</span></div>
    ${r.extracted_code ? `<pre>${esc(r.extracted_code)}</pre>`
      : '<pre class="skip">nothing extractable from the response</pre>'}

    <div class="sec">Usage, cost and grade</div>
    <dl class="kv">
      <dt>prompt tokens</dt><dd class="mono">${num(r.prompt_tokens)}</dd>
      <dt>completion tokens</dt><dd class="mono">${num(r.completion_tokens)}</dd>
      <dt>&nbsp;&nbsp;of which reasoning</dt>
        <dd class="mono">${num(r.reasoning_tokens)} <span class="note">&mdash; ${pct}%
        of completion, billed but absent from the text above</span></dd>
      <dt>finish_reason</dt><dd class="mono">${esc(r.finish_reason)}${
        r.finish_reason === 'length'
          ? ' <span class="skip">&mdash; truncated at max_tokens</span>' : ''}</dd>
      <dt>cost (computed)</dt><dd class="mono">${usd(r.cost_computed_usd)}
        <span class="note">@ $${r.price_in_per_m}/$${r.price_out_per_m} per M</span></dd>
      <dt>cost (actual)</dt><dd class="mono">${usd(r.cost_actual_usd)}
        <span class="note">ground truth from /generation; null until reconciled</span></dd>
      <dt>latency</dt><dd class="mono">${num(r.latency_ms)} ms</dd>
      <dt>verdict</dt><dd>${grade(r)}</dd>
      <dt>base tests</dt><dd>${r.base_passed === null ? '-'
        : (r.base_passed ? 'pass' : 'fail')} <span class="note">(original benchmark only)</span></dd>
      <dt>tests passed</dt><dd class="mono">${r.passed === null ? '-'
        : r.n_tests_passed + '/' + r.n_tests_total}
        <span class="note">diagnostic &mdash; pass@1 is binary</span></dd>
      <dt>error_type</dt><dd class="mono">${esc(r.error_type) || '-'}</dd>
      <dt>exec</dt><dd class="mono">${num(r.exec_ms)} ms</dd>
    </dl>`;
}

['q', 'bench', 'unsolved'].forEach(id =>
  document.getElementById(id).addEventListener('input', renderList));
renderList(); renderMain();
</script></body></html>
"""


def build_payload(conn) -> dict:
    configs = [dict(c) for c in db.list_configs(conn)]
    problems = []
    for p in db.list_problems(conn):
        rows = [dict(r) for r in db.rows_for_problem(conn, p["problem_id"])]
        best = db.cheapest_passing(conn, p["problem_id"])
        item = dict(p)
        item["rows"] = rows
        item["cheapest"] = dict(best) if best else None
        problems.append(item)

    s = db.summary(conn)
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "n_problems": s["problems"],
            "n_configs": s["configs"],
            "n_generations": s["generations"],
            "mock_generations": s["mock_generations"],
            "n_passed": s["passed"],
            "real_spend_usd": s["real_spend_usd"],
        },
        "configs": configs,
        "problems": problems,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else db.DEFAULT_DB
    if not db_path.exists():
        sys.exit(f"no database at {db_path}\n"
                 f"run:  uv run python scripts/seed_mock.py")

    conn = db.connect(db_path)
    payload = build_payload(conn)
    conn.close()

    blob = json.dumps(payload, ensure_ascii=False)
    # The payload lives in a <script> tag, so any literal "</script>" inside a
    # stored model response would close it early and break the page. Escaping
    # every "</" is the standard fix and stays valid JSON.
    blob = blob.replace("</", "<\\/")
    page = TEMPLATE.replace("__DATA__", blob)

    out = Path(args.out) if args.out else db_path.parent / "viewer.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")

    kb = out.stat().st_size / 1024
    print(f"  wrote {out}  ({kb:.0f} KB, fully self-contained)")
    print(f"  {payload['meta']['n_problems']} problems, "
          f"{payload['meta']['n_generations']} generations "
          f"({payload['meta']['mock_generations']} mock)")
    print(f"\n  open {out}")


if __name__ == "__main__":
    main()
