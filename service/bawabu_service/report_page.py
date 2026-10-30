"""The report page (Step 10): one self-contained HTML page that shows an investigation as it happens.

Served at /r/{id} (one investigation) and /live (follows whichever investigation starts next, for watching a
check live). The page polls GET /investigations/{id} and draws the verdict, Spark's steps, the evidence with the
cited code, the sandbox runs and what changed since the previous version.

Package-derived text (code, Spark's words, hostnames) is untrusted: the script only ever inserts it with
textContent, never as HTML, and the response's Content-Security-Policy only runs this page's own script (by nonce).
Kept as a Python string so it ships with the package (Modal's add_local_python_source copies .py files only).
"""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bawabu report</title>
<style>
:root {
  color-scheme: dark;
  --bg: #0b0f17; --panel: #121826; --panel-2: #172033; --line: #24304a; --text: #e6ebf5; --muted: #8b97b0;
  --teal: #2dd4bf; --red: #f87171; --red-bg: #2a1215; --amber: #fbbf24; --amber-bg: #2a2110; --green: #4ade80;
  --green-bg: #0f2418; --violet: #a78bfa; --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
header.bar { display: flex; align-items: center; justify-content: space-between; padding: 14px 24px; border-bottom: 1px solid var(--line); }
.brand { font-weight: 800; letter-spacing: .14em; }
.brand small { font-weight: 400; letter-spacing: 0; color: var(--muted); margin-left: 10px; }
.live { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
.dot.on { background: var(--teal); animation: pulse 1.2s infinite; }
@keyframes pulse { 50% { opacity: .25; } }
main { max-width: 1240px; margin: 0 auto; padding: 24px; }
.hero { display: flex; flex-wrap: wrap; align-items: baseline; gap: 12px 18px; margin-bottom: 18px; }
.pkg { font: 700 26px/1.2 var(--mono); word-break: break-all; min-width: 0; max-width: 100%; }
@media (max-width: 600px) { .pkg { font-size: 20px; } }
.where { color: var(--muted); font-size: 13px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; font-weight: 700; font-size: 13px; letter-spacing: .06em; }
.pill.running { background: #10283a; color: var(--teal); }
.pill.block { background: var(--red-bg); color: var(--red); }
.pill.allow { background: var(--green-bg); color: var(--green); }
.pill.ask, .pill.failed { background: var(--amber-bg); color: var(--amber); }
.verdict { background: var(--panel); border: 1px solid var(--line); border-left: 5px solid var(--muted); border-radius: 12px; padding: 18px 22px; margin-bottom: 22px; }
.verdict.block { border-left-color: var(--red); } .verdict.allow { border-left-color: var(--green); } .verdict.ask { border-left-color: var(--amber); }
.verdict h1 { margin: 0 0 6px; font-size: 22px; }
.verdict p { margin: 0 0 12px; font-size: 16px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 2px 10px; font-size: 13px; color: var(--muted); }
.chip b { color: var(--text); font-weight: 600; }
.grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 22px; align-items: start; }
@media (max-width: 960px) { .grid { grid-template-columns: minmax(0, 1fr); } main { padding: 16px; } header.bar { padding: 12px 16px; } }
section.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; margin-bottom: 22px; }
section.card h2 { margin: 0 0 12px; font-size: 13px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.empty { color: var(--muted); font-size: 14px; }
.timeline { list-style: none; margin: 0; padding: 0; }
.ev { display: grid; grid-template-columns: 54px 14px minmax(0, 1fr); gap: 8px; padding: 5px 0; animation: in .35s ease-out; }
@keyframes in { from { opacity: 0; transform: translateY(4px); } }
.ev .t { color: var(--muted); font: 12px/1.9 var(--mono); text-align: right; }
.ev .mark { width: 10px; height: 10px; margin-top: 7px; border-radius: 50%; background: var(--line); }
.ev .body { min-width: 0; overflow-wrap: anywhere; }
.ev.tool .mark { background: var(--teal); } .ev.tool .body { font-weight: 600; }
.ev.result .body { color: var(--muted); font: 13px/1.6 var(--mono); }
.ev.result .mark { background: transparent; }
.ev.thinking .mark { background: var(--violet); } .ev.thinking .body { color: #cfc4ff; font-style: italic; }
.ev.stage .mark { background: var(--muted); }
.ev.start .mark { background: var(--teal); } .ev.start .body { color: var(--teal); font-weight: 600; }
.ev.rerun .body { background: var(--amber-bg); color: var(--amber); border-radius: 8px; padding: 6px 10px; font-weight: 600; }
.ev.rerun .mark { background: var(--amber); }
.ev.rule .body { background: var(--red-bg); color: var(--red); border-radius: 8px; padding: 6px 10px; font-weight: 600; }
.ev.rule .mark, .ev.error .mark { background: var(--red); } .ev.error .body { color: var(--red); }
.ev.rejected .body { color: var(--muted); text-decoration: line-through; }
.ev.final .body { font-weight: 800; font-size: 16px; }
.ev.final.block .body { color: var(--red); } .ev.final.allow .body { color: var(--green); } .ev.final.ask .body { color: var(--amber); }
.ev.final .mark { background: var(--text); }
.evidence { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; margin-bottom: 12px; background: var(--panel-2); }
.evidence .top { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 6px; }
.tag { font: 700 11px/1.8 var(--mono); padding: 0 8px; border-radius: 6px; background: var(--line); color: var(--text); letter-spacing: .06em; }
.tag.sandbox { background: var(--red-bg); color: var(--red); } .tag.code { background: #10283a; color: var(--teal); }
.tag.decoded { background: #1f1838; color: var(--violet); } .tag.diff { background: var(--amber-bg); color: var(--amber); }
.loc { font: 13px var(--mono); color: var(--muted); }
.ok { color: var(--green); font-size: 13px; margin-left: auto; }
.quote { font: 13px/1.5 var(--mono); color: var(--muted); margin-top: 6px; overflow-wrap: anywhere; }
pre.code { margin: 8px 0 0; padding: 8px 0; background: #0a0e15; border-radius: 8px; overflow-x: auto; font: 12.5px/1.6 var(--mono); }
pre.code div { padding: 0 12px; white-space: pre; }
pre.code div.hit { background: #3a1a1d; box-shadow: inset 3px 0 var(--red); }
pre.code span.n { display: inline-block; width: 3.2em; color: #4b5874; user-select: none; }
.run { border-top: 1px solid var(--line); padding: 12px 0 4px; }
.run:first-of-type { border-top: 0; padding-top: 0; }
.run h3 { margin: 0 0 4px; font-size: 15px; }
.run .sum { color: var(--muted); margin-bottom: 8px; }
.row { font: 13px/1.6 var(--mono); padding: 2px 0; overflow-wrap: anywhere; }
.row.leak { color: var(--red); font-weight: 700; }
.row.benign { color: var(--muted); }
ul.plain { margin: 0; padding-left: 18px; } ul.plain li { margin: 3px 0; }
details summary { cursor: pointer; color: var(--muted); }
.recent { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
.recent a { color: var(--text); text-decoration: none; font: 12px var(--mono); background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 4px 10px; }
.recent a.current { border-color: var(--teal); }
.notice { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
.waiting { text-align: center; padding: 72px 24px; background: var(--panel); border: 1px dashed var(--line); border-radius: 12px; }
.waiting h1 { margin: 0 0 8px; font-size: 22px; } .waiting p { margin: 0; color: var(--muted); }
</style>
</head>
<body>
<header class="bar"><div class="brand">BAWABU<small>the gatekeeper between AI coding agents and the packages they install</small></div>
<div class="live"><span class="dot" id="dot"></span><span id="livetext">connecting…</span></div></header>
<main>
  <div class="notice" id="notice" hidden></div>
  <nav class="recent" id="recent" hidden></nav>
  <div class="waiting" id="waiting" hidden><h1>Watching for the next check</h1>
    <p>When an AI agent tries to install a suspicious package, its investigation appears here as it happens.</p></div>
  <div id="content">
  <div class="hero"><span class="pkg" id="pkg">…</span><span class="pill running" id="pill">LOADING</span><span class="where" id="where"></span></div>
  <div class="verdict" id="verdict"><h1 id="vtitle">Investigating…</h1><p id="vreason">Waiting for the first results.</p><div class="chips" id="chips"></div></div>
  <div class="grid">
    <div><section class="card"><h2>The investigation, step by step</h2><ol class="timeline" id="timeline"></ol><div class="empty" id="tlempty">Waiting for the investigation to start…</div></section></div>
    <div>
      <section class="card"><h2>Evidence (every item checked against what the tools saw)</h2><div id="evidence"><div class="empty">Appears when the verdict is in.</div></div></section>
      <section class="card"><h2>The sandbox</h2><div id="sandbox"><div class="empty">The package runs in a locked sandbox with fake secrets planted.</div></div></section>
      <section class="card"><h2>What changed since the previous version</h2><div id="diff"><div class="empty">Comparing with the previous version…</div></div></section>
      <section class="card" id="rulescard" hidden><h2>Hard rules (override the model)</h2><ul class="plain" id="rules"></ul></section>
      <section class="card" id="rejectedcard" hidden><details><summary id="rejsum">Claims the investigator couldn't back up (discarded)</summary><ul class="plain" id="rejected"></ul></details></section>
    </div>
  </div>
  </div>
</main>
<script nonce="__NONCE__">
(() => {
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = String(text); return n; };
  const MODELS = { "muse-spark-1.3": "Muse Spark (Meta Model API)", "meta-models/muse-spark-open-1026": "Muse Spark Open (open weights, Baseten)" };
  const QUIET = new Set(["read_file", "list_files", "get_metadata", "get_diff"]);
  const follow = location.pathname.replace(/\/+$/, "") === "/live";
  const pageOpened = Date.now() / 1000;
  let currentId = follow ? null : decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  let shown = 0, t0 = null, lastStatus = null;

  function reset() {
    shown = 0; t0 = null; lastStatus = null;
    $("waiting").hidden = true; $("content").hidden = false;
    $("timeline").replaceChildren(); $("tlempty").hidden = false;
    $("evidence").replaceChildren(el("div", "empty", "Appears when the verdict is in."));
    $("sandbox").replaceChildren(el("div", "empty", "The package runs in a locked sandbox with fake secrets planted."));
    $("diff").replaceChildren(el("div", "empty", "Comparing with the previous version…"));
    $("rulescard").hidden = true; $("rejectedcard").hidden = true;
  }

  function setLive(on, text) { $("dot").className = "dot" + (on ? " on" : ""); $("livetext").textContent = text; }

  function header(d) {
    const p = d.package || {};
    $("pkg").textContent = `${p.name || "?"}@${p.version || "?"}`;
    $("where").textContent = !d.private_registry ? "public npm" : d.code_hidden ? "private registry (code excerpts hidden)" : "private registry";
    document.title = `Bawabu: ${p.name || "report"}`;
    const r = d.result || {};
    const v = d.status === "running" ? "running" : d.status === "failed" ? "failed" : (r.verdict || "ask");
    $("pill").className = "pill " + v;
    $("pill").textContent = { running: "INVESTIGATING", failed: "FAILED", block: "BLOCKED", allow: "ALLOWED", ask: "NEEDS A HUMAN" }[v] || v.toUpperCase();
    $("verdict").className = "verdict " + v;
    if (d.status === "running") {
      $("vtitle").textContent = "Investigating…";
      $("vreason").textContent = "Bawabu is reading the code, running the package in a locked sandbox, and Muse Spark is following the clues.";
      $("chips").replaceChildren();
      return;
    }
    if (d.status === "failed") { $("vtitle").textContent = "The investigation failed"; $("vreason").textContent = (r.error || "Unknown error") + " A human should decide."; return; }
    $("vtitle").textContent = { block: "Blocked: this package is not safe to install", allow: "Allowed: no evidence of harm", ask: "A human should decide" }[r.verdict] || r.verdict;
    $("vreason").textContent = r.reason || "";
    const chips = [["confidence", r.confidence], ["investigator", MODELS[r.model] || r.model], ["tool calls", r.steps],
                   ["sandbox re-runs", (r.reruns || []).length], ["investigator time", r.duration_s != null ? r.duration_s + " s" : null]];
    $("chips").replaceChildren(...chips.filter(([, v]) => v != null && v !== "").map(([k, v]) => { const c = el("span", "chip", k + ": "); c.append(el("b", null, v)); return c; }));
    if (r.safe_alternative) { const c = el("span", "chip", "safer choice: "); c.append(el("b", null, r.safe_alternative)); $("chips").append(c); }
  }

  function timeline(events) {
    for (const e of events.slice(shown)) {
      if (t0 == null) t0 = e.t || null;
      // Keep the story readable: the re-run tool call is shown as the highlighted step itself, and results of
      // routine reads (file lists, file names, registry JSON) say nothing a viewer needs.
      if (e.kind === "rerun") continue;
      if (e.kind === "result" && QUIET.has(e.tool)) continue;
      const kind = e.kind === "verdict" ? "final " + (e.verdict || "") : e.kind === "tool" && e.tool === "rerun_sandbox" ? "rerun" : e.kind || "";
      const li = el("li", "ev " + kind);
      li.append(el("span", "t", e.t && t0 ? "+" + (e.t - t0).toFixed(1) + "s" : ""), el("span", "mark"));
      const body = el("div", "body");
      let text = e.title || e.kind;
      if (e.kind === "thinking") text = "Spark: " + text;
      if (e.kind === "rule") text = "Hard rule: " + text;
      if (e.kind === "start") text = "Muse Spark takes over: " + text;
      body.append(el("span", null, text));
      if (e.kind === "stage" && Array.isArray(e.signals) && e.signals.length) {
        const ul = el("ul", "plain"); for (const s of e.signals.slice(0, 4)) ul.append(el("li", null, s)); body.append(ul);
      }
      if (e.kind === "rejected" && e.detail) body.append(el("div", null, "(" + e.detail + ")"));
      li.append(body);
      $("timeline").append(li);
      $("tlempty").hidden = true;
    }
    shown = Math.max(shown, events.length);
  }

  function evidence(r) {
    const box = $("evidence");
    const items = r.evidence || [];
    if (!items.length) { box.replaceChildren(el("div", "empty", r.verdict === "allow" ? "Nothing harmful was found." : "No verified evidence.")); return; }
    box.replaceChildren(...items.map((e) => {
      const card = el("div", "evidence"); const top = el("div", "top");
      top.append(el("span", "tag " + e.type, (e.type || "").toUpperCase()));
      if (e.file) top.append(el("span", "loc", e.line ? `${e.file}:${e.line}` : e.file));
      top.append(el("span", "ok", e.verified ? "✓ verified" : "unverified"));
      card.append(top, el("div", null, e.detail));
      const snip = (r.snippets || {})[`${e.file}:${e.line}`];
      if (snip) {
        const pre = el("pre", "code");
        snip.lines.forEach((line, i) => { const n = snip.start + i; const row = el("div", n === e.line ? "hit" : null); row.append(el("span", "n", n), document.createTextNode(line)); pre.append(row); });
        card.append(pre);
      } else if (e.quote) card.append(el("div", "quote", "“" + e.quote + "”"));
      return card;
    }));
  }

  function run(title, rep) {
    const div = el("div", "run"); div.append(el("h3", null, title), el("div", "sum", rep.summary || ""));
    for (const leak of rep.canaries_leaked || []) div.append(el("div", "row leak", "STOLEN: " + leak));
    for (const f of rep.secret_reads || []) div.append(el("div", "row", "read secret file: " + f));
    for (const n of rep.network || []) {
      const line = `${(n.method || "").toUpperCase()} ${n.scheme || ""}://${n.host || "?"}${n.path || ""}` + (n.benign_destination ? "  (its own registry: fine)" : "");
      div.append(el("div", "row" + ((n.canaries || []).length ? " leak" : n.benign_destination ? " benign" : ""), line.trim()));
    }
    if (!(rep.network || []).length && !(rep.secret_reads || []).length) div.append(el("div", "row benign", "no secret files read, no network contact"));
    return div;
  }

  function sandbox(r) {
    const runs = [];
    if (r.sandbox) runs.push(run("Run 1: a normal developer laptop", r.sandbox));
    (r.reruns || []).forEach((rep, i) => {
      const c = rep.conditions || {}; const parts = Object.entries(c.env || {}).map(([k, v]) => `${k}=${v}`);
      if (c.fake_date) parts.push("clock set to " + c.fake_date);
      runs.push(run(`Run ${i + 2}: re-run by Spark with ${parts.join(", ") || "the same conditions"}`, rep));
    });
    $("sandbox").replaceChildren(...(runs.length ? runs : [el("div", "empty", "The sandbox didn't run for this package.")]));
  }

  function diff(r) {
    const d = r.diff; if (!d) return;
    const box = el("div"); const head = el("div", "chips");
    const risk = el("span", "chip", "static risk: "); risk.append(el("b", null, d.risk)); head.append(risk);
    head.append(el("span", "chip", d.previous ? `compared with ${d.previous}` : "first release: nothing to compare with"));
    if ((d.added || []).length) head.append(el("span", "chip", `${d.added.length} new file(s)`));
    box.append(head);
    if ((d.signals || []).length) { const ul = el("ul", "plain"); ul.style.marginTop = "10px"; for (const s of d.signals) ul.append(el("li", null, s)); box.append(ul); }
    $("diff").replaceChildren(box);
  }

  function finals(r) {
    $("rulescard").hidden = !(r.rules || []).length;
    $("rules").replaceChildren(...(r.rules || []).map((x) => el("li", null, x)));
    $("rejectedcard").hidden = !(r.rejected || []).length;
    $("rejsum").textContent = `Claims the investigator couldn't back up: ${(r.rejected || []).length} discarded`;
    $("rejected").replaceChildren(...(r.rejected || []).map((e) => el("li", null, `${e.detail} (${e.why_rejected || "unverified"})`)));
  }

  async function load() {
    if (!currentId) { setLive(true, "watching for the next check"); return; }
    const res = await fetch(`/investigations/${encodeURIComponent(currentId)}`, { cache: "no-store" });
    if (res.status === 404) { $("pkg").textContent = "No such investigation"; $("pill").textContent = "NOT FOUND"; setLive(false, "not found"); return "done"; }
    const d = await res.json();
    header(d); timeline(d.events || []);
    if (d.status !== "running") {
      if (lastStatus !== d.status && d.result) { evidence(d.result); sandbox(d.result); diff(d.result); finals(d.result); }
      setLive(follow, follow ? "watching for the next check" : "finished");
    } else setLive(true, "live");
    lastStatus = d.status;
    return d.status;
  }

  async function followLatest() {
    const res = await fetch("/investigations?limit=8", { cache: "no-store" });
    if (!res.ok) { $("notice").hidden = false; $("notice").textContent = "The live feed is turned off on this service. Open a report link (/r/<id>) instead."; return; }
    const rows = await res.json();
    const nav = $("recent"); nav.hidden = !rows.length;
    nav.replaceChildren(...rows.map((r) => { const a = el("a", r.id === currentId ? "current" : null, `${r.name}@${r.version}  ${(r.verdict || r.status).toUpperCase()}`); a.href = "/r/" + encodeURIComponent(r.id); return a; }));
    const newest = rows[0];
    const fresh = newest && (newest.status === "running" || Date.parse(newest.created_at) / 1000 > pageOpened - 5);
    if (newest && newest.id !== currentId && fresh) { currentId = newest.id; reset(); }
    $("notice").hidden = false;
    $("notice").textContent = "Live mode: this page follows each new check as it starts.";
  }

  async function tick() {
    try {
      if (follow) await followLatest();
      const status = await load();
      if (!follow && status && status !== "running") return;  // a finished report doesn't change
    } catch (e) { setLive(false, "reconnecting…"); }
    setTimeout(tick, 1500);
  }
  if (follow) { $("waiting").hidden = false; $("content").hidden = true; }
  tick();
})();
</script>
</body>
</html>
"""
