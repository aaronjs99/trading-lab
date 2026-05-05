from __future__ import annotations


CSS = """
    :root {
      color-scheme: dark;
      --bg: #0b0711;
      --panel: #16101f;
      --panel-2: #1f1730;
      --line: #35284c;
      --text: #f4efff;
      --muted: #b9abc9;
      --accent: #b48cff;
      --danger: #ff8fa3;
      --ok: #7ee7b8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at top left, #211333 0, var(--bg) 36%);
      color: var(--text);
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      line-height: 1.4;
    }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    .topbar {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }
    h1, h2, h3 { margin: 0; }
    h1 { font-size: 28px; }
    h2 { font-size: 18px; margin-bottom: 12px; }
    h3 { font-size: 14px; margin-bottom: 8px; color: var(--muted); }
    .muted { color: var(--muted); }
    .grid { display: grid; grid-template-columns: 1.2fr .8fr; gap: 12px; }
    .card {
      background: color-mix(in srgb, var(--panel) 94%, #6f42c1 6%);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      box-shadow: 0 16px 50px rgba(0,0,0,.28);
      margin-bottom: 12px;
    }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 8px; }
    .metric { background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 9px; }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 2px; font-size: 15px; }
    .action { font-size: 34px; color: var(--accent); letter-spacing: 0; line-height: 1; }
    .tight p { margin: 8px 0; }
    .order-actions-card { margin-top: 14px; }
    .compact-list { margin: 8px 0 0; padding-left: 20px; }
    .compact-list li { margin: 4px 0; }
    .danger { color: var(--danger); }
    .ok { color: var(--ok); }
    .review { color: #e5c07b; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; overflow: hidden; }
    th, td { border-bottom: 1px solid var(--line); padding: 9px 8px; text-align: left; }
    th {
      color: var(--muted);
      font-weight: 600;
      background: #171123;
      position: sticky;
      top: 0;
      z-index: 1;
    }
    .table-scroll {
      max-height: 360px;
      overflow: auto;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 230px;
    }
    .mini-scroll {
      max-height: 138px;
      min-height: 118px;
    }
    .table-scroll table { margin-top: 0; }
    .tabs { display: flex; flex-wrap: wrap; gap: 8px; }
    .tab-button {
      width: auto;
      margin: 0;
      padding: 9px 14px;
      background: #120c1c;
      color: var(--muted);
    }
    .tab-button.active { background: #6f42c1; color: var(--text); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .global-controls {
      display: grid;
      grid-template-columns: minmax(340px, 1.35fr) repeat(5, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .risk-control {
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px;
      min-width: 320px;
      max-width: 420px;
    }
    .risk-control span { display: block; color: var(--muted); font-size: 12px; }
    .risk-segmented {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 6px;
      padding: 3px;
      border: 1px solid #46335f;
      border-radius: 999px;
      background: #0f0a17;
    }
    .risk-pill {
      width: auto;
      flex: 1 1 auto;
      margin: 0;
      padding: 7px 10px;
      border-radius: 999px;
      border: 0;
      background: transparent;
      color: var(--muted);
      font-weight: 700;
      text-align: center;
      white-space: nowrap;
    }
    .risk-pill.active { background: #6f42c1; color: var(--text); }
    .open-orders-table {
      min-width: 1500px;
      table-layout: fixed;
    }
    .open-orders-table th,
    .open-orders-table td {
      vertical-align: top;
    }
    .open-orders-table .col-recommendation { width: 120px; }
    .open-orders-table .col-symbol { width: 80px; }
    .open-orders-table .col-side { width: 72px; }
    .open-orders-table .col-type { width: 72px; }
    .open-orders-table .col-quantity { width: 86px; }
    .open-orders-table .col-money { width: 105px; }
    .open-orders-table .col-status { width: 90px; }
    .open-orders-table .col-submitted { width: 112px; }
    .open-orders-table .col-relation { width: 150px; }
    .open-orders-table .col-projected { width: 132px; }
    .open-orders-table .col-reason { width: 420px; }
    .open-orders-table .reason-cell {
      min-width: 420px;
      white-space: normal;
      line-height: 1.35;
    }
    .action-CANCEL, .action-REDUCE { color: var(--danger); font-weight: 700; }
    .action-KEEP { color: var(--ok); font-weight: 700; }
    .action-REVIEW, .action-MOVE_LOWER { color: #e5c07b; font-weight: 700; }
    form {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 8px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
      margin-top: 12px;
    }
    label { color: var(--muted); font-size: 12px; }
    input, select, button {
      width: 100%;
      margin-top: 4px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #0f0a17;
      color: var(--text);
      padding: 8px;
    }
    button { background: #6f42c1; border-color: #8e62df; cursor: pointer; font-weight: 700; }
    .warning { border-color: #704155; color: #ffd3dc; background: #27121e; }
    .span-2 { grid-column: span 2; }
    .span-5 { grid-column: 1 / -1; }
    @media (max-width: 860px) {
      .topbar { align-items: start; flex-direction: column; }
      .global-controls, .grid, .metric-grid, form { grid-template-columns: 1fr; }
      .risk-control { max-width: none; width: 100%; }
      .span-2, .span-5 { grid-column: auto; }
    }
"""


def dashboard_script(active_tab: str, risk_mode: str) -> str:
    return f"""
  function pad(n) {{ return String(n).padStart(2, '0'); }}
  function formatLocalTime(d) {{
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
      ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }}
  function updateLocalClock() {{
    var node = document.getElementById('local-clock');
    if (node) {{ node.textContent = formatLocalTime(new Date()); }}
  }}
  updateLocalClock();
  setInterval(updateLocalClock, 1000);
  setTimeout(function () {{ window.location.reload(); }}, 60 * 60 * 1000);
  var dashboardState = {{
    tab: {active_tab!r},
    riskMode: {risk_mode!r}
  }};
  function params() {{ return new URLSearchParams(window.location.search); }}
  function storeState() {{
    try {{
      localStorage.setItem('tlPortfolioTab', dashboardState.tab);
      localStorage.setItem('tlPortfolioRiskMode', dashboardState.riskMode);
    }} catch (error) {{}}
  }}
  function updateUrl(replace) {{
    var search = params();
    search.set('tab', dashboardState.tab);
    search.set('risk_mode', dashboardState.riskMode);
    var next = window.location.pathname + '?' + search.toString();
    if (replace) {{ history.replaceState(null, '', next); }}
    else {{ window.location.assign(next); }}
  }}
  function activateTab(tab) {{
    dashboardState.tab = tab;
    document.querySelectorAll('.tab-button').forEach(function (node) {{
      node.classList.toggle('active', node.dataset.tab === tab);
    }});
    document.querySelectorAll('.tab-panel').forEach(function (node) {{
      node.classList.toggle('active', node.id === 'tab-' + tab);
    }});
    storeState();
    updateUrl(true);
  }}
  function hydrateState() {{
    var search = params();
    var urlRiskMode = search.get('risk_mode');
    try {{
      dashboardState.tab = search.get('tab') || localStorage.getItem('tlPortfolioTab') || dashboardState.tab;
      dashboardState.riskMode = urlRiskMode || localStorage.getItem('tlPortfolioRiskMode') || dashboardState.riskMode;
    }} catch (error) {{
      dashboardState.tab = search.get('tab') || dashboardState.tab;
      dashboardState.riskMode = urlRiskMode || dashboardState.riskMode;
    }}
    if (!document.getElementById('tab-' + dashboardState.tab)) {{ dashboardState.tab = 'daily'; }}
    if (!document.querySelector('[data-risk-mode="' + dashboardState.riskMode + '"]')) {{
      dashboardState.riskMode = {risk_mode!r};
    }}
    if (!urlRiskMode && dashboardState.riskMode !== {risk_mode!r}) {{
      storeState();
      updateUrl(false);
      return;
    }}
    document.querySelectorAll('.risk-pill').forEach(function (node) {{
      var isActive = node.dataset.riskMode === dashboardState.riskMode;
      node.classList.toggle('active', isActive);
      node.setAttribute('aria-checked', isActive ? 'true' : 'false');
    }});
    activateTab(dashboardState.tab);
  }}
  document.querySelectorAll('.tab-button').forEach(function (button) {{
    button.addEventListener('click', function () {{
      activateTab(button.dataset.tab);
    }});
  }});
  document.querySelectorAll('.risk-pill').forEach(function (button) {{
    button.addEventListener('click', function () {{
      dashboardState.riskMode = button.dataset.riskMode;
      storeState();
      updateUrl(false);
    }});
  }});
  hydrateState();
"""
