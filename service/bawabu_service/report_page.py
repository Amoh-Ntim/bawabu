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
<link rel="icon" type="image/png" href="/mascot.png">
<script nonce="__NONCE__">
(() => {
  let theme;
  try { theme = localStorage.getItem("bawabu-theme"); } catch (_) {}
  document.documentElement.dataset.theme = theme === "light" || theme === "dark" ? theme :
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
})();
</script>
<style>
:root, :root[data-theme="light"] {
  color-scheme: light;
  --bg: #F6F7F9; --card: #FFFFFF; --surface: #F9FAFB; --text: #101828; --muted: #5E687B;
  --line: #EAECF0; --card-border: transparent; --code: #F2F4F7; --code-hit: #FEE4E2;
  --danger: #B42318; --danger-bg: #FEE4E2; --caution: #B54708; --caution-bg: #FEF0C7;
  --low: #175CD3; --low-bg: #D1E9FF; --safe: #067647; --safe-bg: #DCFAE6;
  --brand: #08786C; --brand-bg: #E4F7F3; --spark: #6941C6; --spark-bg: #F0EAFC;
  --shadow: 0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.06);
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0B0F17; --card: #121826; --surface: #172033; --text: #E6EBF5; --muted: #8B97B0;
  --line: #24304A; --card-border: #1F2940; --code: #0A0E15; --code-hit: #3A1A1D;
  --danger: #F87171; --danger-bg: #2A1215; --caution: #FBBF24; --caution-bg: #2A2110;
  --low: #60A5FA; --low-bg: #0F1D33; --safe: #4ADE80; --safe-bg: #0F2418;
  --brand: #2DD4BF; --brand-bg: #102B2A; --spark: #A78BFA; --spark-bg: #221B39;
  --shadow: none;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; -webkit-font-smoothing: antialiased; }
button, a { -webkit-tap-highlight-color: transparent; }
button { font: inherit; }
:focus-visible { outline: 3px solid var(--brand); outline-offset: 4px; }
svg { width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex-shrink: 0; }
header.bar { background: var(--card); border-bottom: 1px solid var(--line); }
.bar-inner { max-width: 1440px; margin: auto; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 18px 36px; }
.brand { display: flex; align-items: center; gap: 12px; font-weight: 750; font-size: 23px; letter-spacing: -.8px; }
/* The mascot's dark outlines need a light tile, in both themes. */
.brand-mark { display: block; width: 48px; height: 48px; padding: 3px; background: #E4F7F3; border-radius: 12px; }
.brand small { display: block; margin-left: 10px; padding-left: 22px; border-left: 1px solid var(--line); color: var(--muted); font-size: 12px; font-weight: 450; letter-spacing: 0; }
.header-actions { display: flex; align-items: center; gap: 24px; }
.live { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; }
.dot { display: inline-block; flex: 0 0 7px; width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
.dot.on { background: var(--brand); box-shadow: 0 0 0 4px var(--brand-bg); animation: pulse 2s infinite; }
@keyframes pulse { 50% { opacity: .4; } }
.theme-toggle { display: inline-flex; justify-content: center; align-items: center; gap: 8px; min-height: 40px; padding: 8px 12px; color: var(--text); background: var(--surface); border: 1px solid var(--line); border-radius: 12px; cursor: pointer; }
.theme-toggle:hover { border-color: var(--brand); }
.theme-toggle svg { width: 17px; height: 17px; }
[data-theme="dark"] .moon, [data-theme="light"] .sun { display: none; }
main { max-width: 1440px; margin: 0 auto; padding: 36px; }
.eyebrow { color: var(--muted); font-size: 11px; font-weight: 650; text-transform: uppercase; letter-spacing: .14em; margin-bottom: 12px; }
.hero { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 16px; margin-bottom: 12px; }
.pkg { font: 650 28px/1.3 var(--mono); letter-spacing: -1.1px; overflow-wrap: anywhere; min-width: 0; max-width: 100%; }
.meta { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 24px; }
.where { color: var(--muted); font-size: 12px; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-weight: 650; font-size: 11px; line-height: 1.6; letter-spacing: .025em; }
.running { --tone: var(--brand); --tint: var(--brand-bg); }
.block, .risk-high { --tone: var(--danger); --tint: var(--danger-bg); }
.ask, .failed, .risk-medium { --tone: var(--caution); --tint: var(--caution-bg); }
.allow, .risk-none { --tone: var(--safe); --tint: var(--safe-bg); }
.risk-low { --tone: var(--low); --tint: var(--low-bg); }
.pill.running, .pill.block, .pill.allow, .pill.ask, .pill.failed, .risk { color: var(--tone); background: var(--tint); }
.verdict { display: flex; gap: 18px; align-items: flex-start; border: 1px solid var(--card-border); border-radius: 16px; padding: 24px; margin-bottom: 22px; background: var(--tint, var(--card)); color: var(--tone, var(--text)); }
.verdict-symbol { flex: 0 0 44px; display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid currentColor; border-radius: 13px; font-size: 25px; font-weight: 500; }
.verdict-copy { min-width: 0; }
.verdict h1 { margin: 0 0 5px; font-size: 19px; font-weight: 680; letter-spacing: -.35px; }
.verdict p { margin: 0; font-size: 14px; line-height: 1.75; overflow-wrap: anywhere; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center; background: var(--surface); border: 1px solid var(--line); border-radius: 7px; padding: 3px 9px; font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.chip b { color: var(--text); font-weight: 550; }
.chip.model { background: var(--spark-bg); color: var(--spark); border: 0; }
.chip.model b { color: inherit; }
.stats { display: grid; grid-template-columns: 1.35fr repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }
.stat { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; padding: 19px 22px; background: var(--card); border: 1px solid var(--card-border); border-radius: 16px; box-shadow: var(--shadow); }
.stat-label { font-size: 11px; color: var(--muted); font-weight: 550; margin-bottom: 6px; }
.stat-value { font-size: 28px; line-height: 1.3; font-weight: 650; letter-spacing: -.9px; font-variant-numeric: tabular-nums; }
.stat-value small { font-size: 15px; color: var(--muted); font-weight: 450; letter-spacing: 0; }
.stat-note { display: block; color: var(--muted); font-size: 10px; margin-top: 5px; }
.ring { --progress: 0%; --ring-tone: var(--safe); width: 55px; height: 55px; border-radius: 50%; display: grid; place-items: center; background: conic-gradient(var(--ring-tone) var(--progress), var(--line) 0); flex-shrink: 0; }
.ring-center { background: var(--card); color: var(--ring-tone); border-radius: 50%; width: 43px; height: 43px; display: grid; place-items: center; font-size: 16px; }
.confidence-meter { display: flex; align-items: flex-end; gap: 4px; height: 20px; margin-top: 5px; }
.confidence-meter span { width: 17px; border-radius: 3px; background: var(--line); height: 8px; }
.confidence-meter span:nth-child(2) { height: 13px; } .confidence-meter span:nth-child(3) { height: 18px; }
.confidence-meter span.filled { background: var(--tone); }
.grid { display: grid; grid-template-columns: minmax(0, .95fr) minmax(0, 1.2fr); gap: 24px; align-items: start; }
section.card { background: var(--card); border: 1px solid var(--card-border); border-radius: 16px; padding: 24px; margin-bottom: 24px; box-shadow: var(--shadow); min-width: 0; }
.card-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
.icon-square { display: grid; place-items: center; flex: 0 0 38px; width: 38px; height: 38px; color: var(--brand); background: var(--brand-bg); border-radius: 11px; }
.icon-square.spark { color: var(--spark); background: var(--spark-bg); }
.icon-square.neutral { color: var(--muted); background: var(--surface); }
.icon-square.danger { color: var(--danger); background: var(--danger-bg); }
section.card h2 { margin: 0; font-size: 15px; font-weight: 650; letter-spacing: -.2px; }
.card-subtitle { margin: 1px 0 0; font-size: 11px; color: var(--muted); }
.empty { color: var(--muted); font-size: 13px; padding: 14px 0; }
.timeline { list-style: none; margin: 0; padding: 0; }
.ev { display: grid; grid-template-columns: 42px 14px minmax(0, 1fr); gap: 10px; padding: 0 0 22px; position: relative; animation: enter .3s ease-out; }
.ev:last-child { padding-bottom: 0; }
.ev:not(:last-child)::before { content: ""; position: absolute; width: 1px; background: var(--line); left: 58px; top: 15px; bottom: -5px; }
@keyframes enter { from { opacity: 0; transform: translateY(4px); } }
.ev .t { color: var(--muted); font: 10px/2.2 var(--mono); text-align: right; }
.ev .mark { width: 9px; height: 9px; margin: 7px 0 0 2px; border-radius: 50%; background: var(--line); z-index: 1; box-shadow: 0 0 0 4px var(--card); }
.ev .body { min-width: 0; overflow-wrap: anywhere; font-size: 12px; }
.ev .risk { margin: 6px 0; }
.ev.tool .mark { background: var(--brand); } .ev.tool .body { font-weight: 550; }
.ev.result .body { color: var(--muted); font: 11px/1.75 var(--mono); }
.ev.thinking .mark { background: var(--spark); } .ev.thinking .body { color: var(--spark); padding: 10px 12px; background: var(--spark-bg); border-radius: 9px; }
.ev.stage .mark { background: var(--muted); }
.ev.start .mark { background: var(--brand); } .ev.start .body { color: var(--brand); font-weight: 600; }
.ev.rerun .body { background: var(--caution-bg); color: var(--caution); border-radius: 10px; padding: 10px 12px; font-weight: 600; }
.ev.rerun .mark { background: var(--caution); }
.ev.rule .body { background: var(--danger-bg); color: var(--danger); border-radius: 10px; padding: 10px 12px; font-weight: 600; }
.ev.rule .mark, .ev.error .mark { background: var(--danger); } .ev.error .body { color: var(--danger); }
.ev.rejected .body { color: var(--muted); text-decoration: line-through; }
.ev.final .body { font-weight: 700; font-size: 13px; color: var(--tone); }
.ev.final .mark { background: var(--tone, var(--text)); }
.evidence { border: 1px solid var(--line); border-radius: 12px; padding: 16px; margin-top: 12px; background: var(--card); font-size: 12px; overflow-wrap: anywhere; }
.evidence:first-child { margin-top: 0; }
.evidence .top { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }
.tag { font: 650 10px/1.7 var(--mono); padding: 2px 7px; border-radius: 5px; background: var(--surface); color: var(--muted); letter-spacing: .025em; }
.tag.sandbox { background: var(--danger-bg); color: var(--danger); } .tag.code { background: var(--brand-bg); color: var(--brand); }
.tag.decoded { background: var(--spark-bg); color: var(--spark); } .tag.diff { background: var(--caution-bg); color: var(--caution); }
.loc { font: 10px var(--mono); color: var(--muted); overflow-wrap: anywhere; }
.verification { margin-left: auto; font-size: 10px; padding: 2px 7px; }
.verified { color: var(--safe); background: var(--safe-bg); }
.unverified { color: var(--caution); background: var(--caution-bg); }
.quote { font: 11px/1.7 var(--mono); color: var(--muted); margin-top: 10px; overflow-wrap: anywhere; }
pre.code { margin: 12px 0 0; padding: 12px 0; background: var(--code); border-radius: 8px; overflow-x: auto; font: 11px/1.8 var(--mono); }
pre.code div { padding: 0 12px; white-space: pre; }
pre.code div.hit { background: var(--code-hit); box-shadow: inset 3px 0 var(--danger); }
pre.code span.n { display: inline-block; width: 3em; color: var(--muted); user-select: none; }
.run { border-top: 1px solid var(--line); padding: 20px 0 0; margin-top: 20px; }
.run:first-child { border: 0; padding: 0; margin: 0; }
.run h3 { margin: 0 0 7px; font-size: 12px; font-weight: 650; overflow-wrap: anywhere; }
.run .sum { color: var(--muted); margin-bottom: 12px; font-size: 12px; overflow-wrap: anywhere; }
.run .rerun-label { color: var(--caution); }
.row { font: 11px/1.8 var(--mono); margin: 6px 0; overflow-wrap: anywhere; }
.row.leak { display: table; color: var(--danger); background: var(--danger-bg); border-radius: 7px; padding: 5px 9px; font-weight: 650; }
.row.secret { color: var(--caution); background: var(--caution-bg); border-radius: 7px; padding: 5px 9px; }
.row.benign { color: var(--muted); } .safe-check { color: var(--safe); font-weight: 650; }
.network-wrap { max-width: 100%; overflow-x: auto; margin-top: 16px; border: 1px solid var(--line); border-radius: 9px; }
.network { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }
.network caption { text-align: left; padding: 10px 12px; font-weight: 600; color: var(--muted); }
.network th { background: var(--surface); color: var(--muted); font-size: 10px; font-weight: 550; text-align: left; }
.network th, .network td { padding: 9px 10px; border-top: 1px solid var(--line); vertical-align: top; overflow-wrap: anywhere; }
.network td { font-family: var(--mono); }
.network th:first-child { width: 15%; } .network th:last-child { width: 29%; }
.network .pill { font: 600 9px/1.5 system-ui, sans-serif; padding: 3px 6px; }
.network .registry { background: var(--surface); color: var(--muted); }
.signals { list-style: none; padding: 0; margin: 18px 0 0; }
.signal { display: flex; align-items: baseline; gap: 10px; padding: 10px 0; font-size: 12px; border-top: 1px solid var(--line); overflow-wrap: anywhere; }
.signal .severity { display: inline-flex; align-items: center; gap: 5px; flex: 0 0 61px; font-size: 9px; font-weight: 700; color: var(--tone); }
.severity .dot { background: var(--tone); width: 5px; height: 5px; flex-basis: 5px; }
.signal.old { color: var(--muted); }
.signal.old .severity { color: var(--muted); } .signal.old .dot { background: var(--muted); }
.severity-summary { margin: 20px 0 12px; }
.severity-title { font-size: 11px; color: var(--muted); margin-bottom: 9px; }
.severity-bar { display: flex; gap: 3px; height: 7px; border-radius: 9px; overflow: hidden; background: var(--line); }
.severity-bar span { background: var(--tone); }
.severity-legend { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 9px; font-size: 10px; color: var(--muted); }
.severity-legend .dot { background: var(--tone); width: 5px; height: 5px; margin-right: 5px; }
ul.plain { margin: 8px 0 0; padding-left: 17px; font-size: 12px; overflow-wrap: anywhere; } ul.plain li { margin: 7px 0; }
#rules { color: var(--danger); } #rules li { padding: 6px 4px; }
details summary { cursor: pointer; color: var(--muted); font-size: 12px; }
.recent { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 22px; }
.recent a { display: inline-flex; align-items: center; gap: 7px; color: var(--text); text-decoration: none; font: 10px/1.6 var(--mono); background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; overflow-wrap: anywhere; max-width: 100%; }
.recent a .dot { background: var(--tone, var(--muted)); }
.recent a.current { border-color: var(--brand); background: var(--brand-bg); }
.notice { color: var(--muted); font-size: 12px; margin-bottom: 16px; }
.waiting { text-align: center; padding: 80px 24px; background: var(--card); border: 1px solid var(--card-border); box-shadow: var(--shadow); border-radius: 16px; }
.waiting h1 { margin: 0 0 10px; font-size: 24px; letter-spacing: -.7px; } .waiting p { max-width: 500px; margin: auto; color: var(--muted); }
footer { display: flex; justify-content: space-between; color: var(--muted); font-size: 11px; padding: 8px 0 20px; }
@media (min-width: 1500px) { main { padding-top: 44px; } }
@media (max-width: 1100px) { .stats { gap: 10px; } .stat { padding: 16px; } .ring { width: 45px; height: 45px; } .ring-center { width: 35px; height: 35px; } .brand small { max-width: 240px; } }
@media (max-width: 960px) { .grid { grid-template-columns: minmax(0, 1fr); } .stats { grid-template-columns: repeat(3, minmax(0, 1fr)); } .brand small { display: none; } }
@media (max-width: 600px) {
  main { padding: 24px 16px; } .bar-inner { padding: 14px 16px; gap: 12px; } .brand { font-size: 20px; gap: 8px; }
  .header-actions { gap: 12px; } .live { font-size: 10px; max-width: 112px; } .theme-toggle { padding: 9px; } #theme-label { display: none; }
  .pkg { font-size: 21px; letter-spacing: -.7px; } .meta { gap: 8px; } .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .stat { padding: 16px; min-height: 110px; } .stat-value { font-size: 25px; } .stat-label { font-size: 10px; } .ring { width: 36px; height: 36px; } .ring-center { width: 28px; height: 28px; font-size: 13px; }
  .verdict { padding: 18px; gap: 12px; } .verdict-symbol { width: 32px; height: 32px; flex-basis: 32px; font-size: 20px; border-radius: 10px; } .verdict h1 { font-size: 17px; } .verdict p { font-size: 12px; }
  section.card { padding: 20px 16px; } .card-heading { gap: 10px; } .card-subtitle { font-size: 10px; } section.card h2 { font-size: 14px; }
  .ev { grid-template-columns: 34px 12px minmax(0, 1fr); gap: 8px; } .ev:not(:last-child)::before { left: 48px; } .ev .t { font-size: 9px; }
  .evidence { padding: 12px; } .network th, .network td { padding: 8px 5px; } footer { gap: 20px; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
</head>
<body>
<header class="bar"><div class="bar-inner">
<div class="brand"><img class="brand-mark" src="/mascot.png" alt="" width="48" height="48">Bawabu<small>The gatekeeper between AI coding agents<br>and the packages they install</small></div>
<div class="header-actions"><div class="live" role="status"><span class="dot" id="dot"></span><span id="livetext">connecting…</span></div>
<button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch color theme">
<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15A8 8 0 0 1 9 4 8 8 0 1 0 20 15Z"/></svg>
<svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/></svg>
<span id="theme-label">Theme</span></button></div></div></header>
<main>
  <div class="notice" id="notice" hidden></div>
  <nav class="recent" id="recent" aria-label="Recent package checks" hidden></nav>
  <div class="waiting" id="waiting" hidden><h1>Watching for the next check</h1>
    <p>When an AI agent tries to install a suspicious package, its investigation appears here as it happens.</p></div>
  <div id="content">
  <div class="eyebrow">Package security &nbsp; / &nbsp; Investigation report</div>
  <div class="hero"><span class="pkg" id="pkg">…</span><span class="pill running" id="pill">LOADING</span></div>
  <div class="meta"><span class="where" id="where"></span><div class="chips" id="chips"></div></div>
  <div class="verdict running" id="verdict" role="status"><span class="verdict-symbol" id="vsymbol" aria-hidden="true">⋯</span><div class="verdict-copy"><h1 id="vtitle">Investigating…</h1><p id="vreason">Waiting for the first results.</p></div></div>
  <div class="stats" id="stats" aria-label="Investigation metrics"></div>
  <div class="grid">
    <div><section class="card"><div class="card-heading"><span class="icon-square spark"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h14M5 12h9M5 19h14"/><circle cx="17" cy="12" r="2"/></svg></span><div><h2>The investigation</h2><p class="card-subtitle">Step by step, from first check to verdict</p></div></div><ol class="timeline" id="timeline"></ol><div class="empty" id="tlempty">Waiting for the investigation to start…</div></section></div>
    <div>
      <section class="card"><div class="card-heading"><span class="icon-square "><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6Z"/><path d="m8 12 3 3 5-6"/></svg></span><div><h2>Evidence</h2><p class="card-subtitle">Checked against what the tools saw</p></div></div><div id="evidence"><div class="empty">Appears when the verdict is in.</div></div></section>
      <section class="card"><div class="card-heading"><span class="icon-square neutral"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 9 5-9 5-9-5Zm-9 5v10l9 5 9-5V8M12 13v10"/></svg></span><div><h2>The sandbox</h2><p class="card-subtitle">Locked, with fake secrets planted</p></div></div><div id="sandbox"><div class="empty">The package runs in a locked sandbox with fake secrets planted.</div></div></section>
      <section class="card"><div class="card-heading"><span class="icon-square neutral"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3v12a4 4 0 0 0 4 4h8M18 3v8a4 4 0 0 1-4 4H6"/><circle cx="6" cy="3" r="2"/><circle cx="18" cy="3" r="2"/><circle cx="18" cy="19" r="2"/></svg></span><div><h2>What changed</h2><p class="card-subtitle">Since the previous version</p></div></div><div id="diff"><div class="empty">Comparing with the previous version…</div></div></section>
      <section class="card" id="rulescard" hidden><div class="card-heading"><span class="icon-square danger"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 10 18H2Z M12 9v5M12 17h.01"/></svg></span><div><h2>Hard rules</h2><p class="card-subtitle">Override the model</p></div></div><ul class="plain" id="rules"></ul></section>
      <section class="card" id="rejectedcard" hidden><details><summary id="rejsum">Claims the investigator couldn't back up (discarded)</summary><ul class="plain" id="rejected"></ul></details></section>
    </div>
  </div>
  </div>
  <footer><span>Bawabu · Package security</span><span>Nothing gets in without a check.</span></footer>
</main>
<script nonce="__NONCE__">
(() => {
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = String(text); return n; };
  const RISK_CLASSES = { none: "risk-none", low: "risk-low", medium: "risk-medium", high: "risk-high" };
  const SYMBOLS = { running: "⋯", failed: "!", block: "✕", allow: "✓", ask: "?" };
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  let themeOverride = false;
  try { themeOverride = ["light", "dark"].includes(localStorage.getItem("bawabu-theme")); } catch (_) {}
  function themeLabel() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    $("theme-toggle").setAttribute("aria-label", `Switch to ${next} theme`);
    $("theme-toggle").title = `Switch to ${next} theme`;
    $("theme-label").textContent = next === "dark" ? "Dark" : "Light";
  }
  $("theme-toggle").addEventListener("click", () => {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    themeOverride = true;
    try { localStorage.setItem("bawabu-theme", theme); } catch (_) {}
    themeLabel();
  });
  systemTheme.addEventListener("change", e => {
    if (!themeOverride) { document.documentElement.dataset.theme = e.matches ? "dark" : "light"; themeLabel(); }
  });
  themeLabel();
  function riskPill(level) {
    return el("span", "pill risk " + (RISK_CLASSES[level] || ""), "Static risk: " + (RISK_CLASSES[level] ? level.toUpperCase() : "UNKNOWN"));
  }
  function metrics(r, status, verdict) {
    const complete = status === "done";
    const items = Array.isArray(r.evidence) ? r.evidence : [];
    const verified = items.filter(e => e.verified).length;
    const runs = (r.sandbox ? 1 : 0) + (r.reruns || []).length;
    const availableRuns = complete && ("sandbox" in r || "reruns" in r);
    const confidence = ["low", "medium", "high"].includes(r.confidence) ? r.confidence : null;
    const pending = status === "running" ? "In progress" : "Not recorded";
    const specs = [
      ["Evidence verified", complete ? verified : "—", complete ? (items.length ? "Checked against tool output" : "No evidence claims") : pending],
      ["Tool calls", complete && r.steps != null ? r.steps : "—", "Investigator actions"],
      ["Sandbox runs", availableRuns ? runs : "—", availableRuns ? `${(r.reruns || []).length} re-run${(r.reruns || []).length === 1 ? "" : "s"} by Spark` : pending],
      ["Investigator time", complete && r.duration_s != null ? r.duration_s : "—", "Time spent investigating"],
      ["Confidence", complete && confidence ? confidence[0].toUpperCase() + confidence.slice(1) : "—", "Investigator certainty"]
    ];
    $("stats").replaceChildren(...specs.map(([label, value, note], i) => {
      const tile = el("div", "stat " + verdict), copy = el("div");
      const num = el("div", "stat-value", value);
      if (i === 0 && complete) num.append(el("small", null, " / " + items.length));
      if (i === 3 && complete && r.duration_s != null) num.append(el("small", null, " s"));
      copy.append(el("div", "stat-label", label), num);
      if (i === 4 && complete && confidence) {
        const meter = el("div", "confidence-meter"); meter.setAttribute("aria-hidden", "true");
        for (let n=0; n<3; n++) meter.append(el("span", n < {low:1, medium:2, high:3}[confidence] ? "filled" : null));
        copy.append(meter);
      } else copy.append(el("span", "stat-note", note));
      tile.append(copy);
      if (i === 0) {
        const ring = el("div", "ring");
        ring.setAttribute("aria-hidden", "true");
        ring.style.setProperty("--progress", (complete && items.length ? 100 * verified / items.length : 0) + "%");
        ring.style.setProperty("--ring-tone", !complete || !items.length ? "var(--muted)" : verified === items.length ? "var(--safe)" : "var(--caution)");
        ring.append(el("span", "ring-center", complete && items.length && verified === items.length ? "✓" : "·"));
        tile.append(ring);
      }
      return tile;
    }));
  }
  const MODELS = { "muse-spark-1.3": "Muse Spark (Meta Model API)", "meta-models/muse-spark-open-1026": "Muse Spark Open (open weights, Baseten)" };
  const QUIET = new Set(["read_file", "list_files", "get_metadata", "get_diff"]);
  const follow = location.pathname.replace(/\/+$/, "") === "/live";
  // /live?fresh (for recording a demo): leave out the checks from before the page was opened.
  const onlyNew = new URLSearchParams(location.search).has("fresh");
  const pageOpened = Date.now() / 1000;
  let currentId = follow ? null : decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
  let shown = 0, t0 = null, lastStatus = null;

  function reset() {
    shown = 0; t0 = null; lastStatus = null;
    $("waiting").hidden = true; $("content").hidden = false;
    $("timeline").replaceChildren(); $("tlempty").hidden = false;
    $("tlempty").textContent = "Waiting for the investigation to start…";
    $("evidence").replaceChildren(el("div", "empty", "Appears when the verdict is in."));
    $("sandbox").replaceChildren(el("div", "empty", "The package runs in a locked sandbox with fake secrets planted."));
    $("diff").replaceChildren(el("div", "empty", "Comparing with the previous version…"));
    $("rulescard").hidden = true; $("rejectedcard").hidden = true;
    $("chips").replaceChildren(); $("stats").replaceChildren();
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
    $("vsymbol").textContent = SYMBOLS[v] || "?";
    $("pill").textContent = (SYMBOLS[v] || "?") + " " + $("pill").textContent;
    $("chips").replaceChildren();
    metrics(r, d.status, v);
    if (d.status === "running") {
      $("vtitle").textContent = "Investigating…";
      $("vreason").textContent = "Bawabu is reading the code, running the package in a locked sandbox, and Muse Spark is following the clues.";
      $("chips").replaceChildren();
      return;
    }
    if (d.status === "failed") { $("vtitle").textContent = "The investigation failed"; $("vreason").textContent = (r.error || "Unknown error") + " A human should decide."; return; }
    $("vtitle").textContent = { block: "Blocked: this package is not safe to install", allow: "Allowed: no evidence of harm", ask: "A human should decide" }[r.verdict] || r.verdict;
    $("vreason").textContent = r.reason || "";
    if (r.model) {
      const model = el("span", "chip model", "investigator: ");
      model.append(el("b", null, MODELS[r.model] || r.model));
      $("chips").append(model);
    }
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
      if (e.kind === "rule") text = "⚠ Hard rule: " + text;
      if (kind === "rerun") text = "↻ " + text;
      if (e.kind === "start") text = "Muse Spark takes over: " + text;
      const staticRisk = e.kind === "stage" && /^Static analysis: risk (none|low|medium|high)\b/.exec(text);
      if (staticRisk) {
        body.append(riskPill(staticRisk[1]), el("span", null, text.slice(staticRisk[0].length)));
      } else body.append(el("span", null, text));
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
      top.append(el("span", "pill verification " + (e.verified ? "verified" : "unverified"), e.verified ? "✓ verified" : "! unverified"));
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

  function run(title, rep, rerun = false) {
    const div = el("div", "run"); div.append(el("h3", rerun ? "rerun-label" : null, (rerun ? "↻ " : "") + title), el("div", "sum", rep.summary || ""));
    for (const leak of rep.canaries_leaked || []) div.append(el("div", "row leak", "STOLEN: " + leak));
    for (const f of rep.secret_reads || []) div.append(el("div", "row secret", "Read secret file: " + f));
    if ((rep.network || []).length) {
      const wrap = el("div", "network-wrap"), table = el("table", "network");
      table.append(el("caption", null, "Network contacts in the sandbox"));
      const head = el("thead"), labels = el("tr");
      for (const label of ["Method", "Host", "Path", "Status"]) { const th = el("th", null, label); th.scope = "col"; labels.append(th); }
      head.append(labels); table.append(head);
      const body = el("tbody");
      for (const n of rep.network) {
        const stolen = (n.canaries || []).length > 0;
        const row = el("tr");
        row.append(el("td", null, (n.method || "—").toUpperCase()), el("td", null, (n.scheme ? n.scheme + "://" : "") + (n.host || "?")), el("td", null, n.path || "/"));
        const status = el("td");
        const pill = el("span", "pill " + (stolen ? "block" : n.benign_destination ? "registry" : "ask"), stolen ? "STOLEN" : n.benign_destination ? "Own registry" : "Unknown host");
        if (n.benign_destination && !stolen) pill.prepend(el("span", "safe-check", "✓"));
        status.append(pill); row.append(status); body.append(row);
      }
      table.append(body); wrap.append(table); div.append(wrap);
    }
    // A failed run observed nothing, which isn't the same as observing nothing bad.
    if (!rep.error && !(rep.network || []).length && !(rep.secret_reads || []).length && !(rep.canaries_leaked || []).length) {
      const row = el("div", "row benign"); row.append(el("span", "safe-check", "✓ "), document.createTextNode("No secret files read, no network contact")); div.append(row);
    }
    return div;
  }

  function sandbox(r) {
    const runs = [];
    if (r.sandbox) runs.push(run("Run 1: a normal developer laptop", r.sandbox));
    (r.reruns || []).forEach((rep, i) => {
      const c = rep.conditions || {}; const parts = Object.entries(c.env || {}).map(([k, v]) => `${k}=${v}`);
      if (c.fake_date) parts.push("clock set to " + c.fake_date);
      runs.push(run(`Run ${i + 2}: re-run by Spark with ${parts.join(", ") || "the same conditions"}`, rep, true));
    });
    $("sandbox").replaceChildren(...(runs.length ? runs : [el("div", "empty", "The sandbox didn't run for this package.")]));
  }

  function diff(r) {
    const d = r.diff;
    if (!d) { $("diff").replaceChildren(el("div", "empty", "No version comparison was recorded.")); return; }
    const box = el("div"); const head = el("div", "chips");
    head.append(riskPill(d.risk));
    head.append(el("span", "chip", d.previous ? `compared with ${d.previous}` : "first release: nothing to compare with"));
    if ((d.added || []).length) head.append(el("span", "chip", `${d.added.length} new file(s)`));
    box.append(head);
    if (Array.isArray(d.signal_items) && d.signal_items.length) {
      const ranks = {high:3, medium:2, low:1};
      const items = [...d.signal_items].sort((a,b) => (ranks[b.severity] || 0) - (ranks[a.severity] || 0));
      const counts = {high:0, medium:0, low:0};
      for (const item of items) if (item.severity in counts) counts[item.severity]++;
      const summary = el("div", "severity-summary"), bar = el("div", "severity-bar"), legend = el("div", "severity-legend");
      summary.append(el("div", "severity-title", "Signals by severity · shown below"));
      bar.setAttribute("aria-hidden", "true");
      for (const level of ["high", "medium", "low"]) {
        if (counts[level]) { const segment = el("span", RISK_CLASSES[level]); segment.style.flexGrow = counts[level]; bar.append(segment); }
        const label = el("span", RISK_CLASSES[level]); label.append(el("span", "dot"), document.createTextNode(`${counts[level]} ${level}`)); legend.append(label);
      }
      summary.append(bar, legend); box.append(summary);
      const ul = el("ul", "signals");
      for (const item of items) {
        const li = el("li", "signal " + (RISK_CLASSES[item.severity] || "") + (item.new === false ? " old" : ""));
        const severity = el("span", "severity");
        severity.append(el("span", "dot"), document.createTextNode(({high:"HIGH",medium:"MED",low:"LOW"})[item.severity] || "INFO"));
        li.append(severity, el("span", null, item.text)); ul.append(li);
      }
      box.append(ul);
    } else if ((d.signals || []).length) {
      const ul = el("ul", "plain");
      for (const text of d.signals) ul.append(el("li", null, text));
      box.append(ul);
    }
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
      if (!(d.events || []).length) $("tlempty").textContent = "No timeline events were recorded.";
      if (lastStatus !== d.status && d.result) { evidence(d.result); sandbox(d.result); diff(d.result); finals(d.result); }
      setLive(follow, follow ? "watching for the next check" : "finished");
    } else setLive(true, "live");
    lastStatus = d.status;
    return d.status;
  }

  async function followLatest() {
    const res = await fetch("/investigations?limit=8", { cache: "no-store" });
    if (!res.ok) { $("notice").hidden = false; $("notice").textContent = "The live feed is turned off on this service. Open a report link (/r/<id>) instead."; return; }
    const all = await res.json();
    const rows = onlyNew ? all.filter((r) => Date.parse(r.created_at) / 1000 > pageOpened - 5) : all;
    const nav = $("recent"); nav.hidden = !rows.length;
    nav.replaceChildren(...rows.map((r) => { const state = r.status === "running" ? "running" : (r.verdict || r.status); const a = el("a", (r.id === currentId ? "current " : "") + state); a.append(el("span", "dot"), el("span", null, `${r.name}@${r.version}  ${({block:"BLOCKED",allow:"ALLOWED",ask:"NEEDS A HUMAN",running:"RUNNING",failed:"FAILED"})[state] || state.toUpperCase()}`)); a.href = "/r/" + encodeURIComponent(r.id); return a; }));
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
