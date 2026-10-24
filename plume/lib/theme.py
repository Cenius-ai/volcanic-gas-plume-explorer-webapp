"""The committed design system for the Plume Explorer.

One token block, one stylesheet, one Plotly template. Every screen consumes
these tokens; no component carries a colour of its own.
"""

from __future__ import annotations

import streamlit as st

CHART_SERIES = ("#9884f3", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")

# Chart series 1 is the accent's hex twin: charting libraries cannot read oklch().

STYLE = """<style>
@font-face{font-family:'Inter';font-style:normal;font-weight:400;font-display:swap;src:url('/app/static/fonts/inter-latin-400-normal.woff2') format('woff2');}
@font-face{font-family:'Inter';font-style:normal;font-weight:500;font-display:swap;src:url('/app/static/fonts/inter-latin-500-normal.woff2') format('woff2');}
@font-face{font-family:'Inter';font-style:normal;font-weight:700;font-display:swap;src:url('/app/static/fonts/inter-latin-700-normal.woff2') format('woff2');}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:400;font-display:swap;src:url('/app/static/fonts/jetbrains-mono-latin-400-normal.woff2') format('woff2');}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:600;font-display:swap;src:url('/app/static/fonts/jetbrains-mono-latin-600-normal.woff2') format('woff2');}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:700;font-display:swap;src:url('/app/static/fonts/jetbrains-mono-latin-700-normal.woff2') format('woff2');}

:root{
  --background:#0c0c11;
  --foreground:#efeff5;
  --card:#16161d;
  --card-foreground:#efeff5;
  --muted:#212127;
  --muted-foreground:#9d9da6;
  --border:#2d2d34;
  --accent:#9884f3;
  --accent-strong:#c3b6f9;
  --accent-soft:rgba(152,132,243,0.14);
  --accent-line:rgba(152,132,243,0.35);
  --on-accent:#111111;
  --primary:#9884f3;
  --on-primary:#111111;
  --ring:#9884f3;
  --destructive:#c9302d;
  --on-destructive:#ffffff;
  --radius:14px;
  --radius-sm:10px;
  --shadow:0 1px 3px rgba(0,0,0,0.06);
  --font-body:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  --font-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  --chart-1:#9884f3;
  --chart-2:#0072B2;
  --chart-3:#D55E00;
  --chart-4:#009E73;
  --chart-5:#CC79A7;
  --chart-6:#E69F00;
}

html,body,.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp textarea,.stApp button{
  font-family:var(--font-body);
}
.stApp{background:var(--background);color:var(--foreground);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stDecoration"]{display:none;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}
[data-testid="stMainBlockContainer"],.block-container{
  padding:1.5rem 2.25rem 4rem;max-width:1200px;
}
[data-testid="stSidebar"]{background:#0a0a0e;border-right:1px solid var(--border);}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:0.55rem;}
[data-testid="stSidebarNav"]{padding-top:0.35rem;}
[data-testid="stSidebarNav"] ul{gap:2px;}
[data-testid="stSidebarNav"] a{
  border-radius:var(--radius-sm);padding:7px 10px;color:var(--muted-foreground);
  font-family:var(--font-body);font-size:0.9rem;
}
[data-testid="stSidebarNav"] a:hover{background:var(--muted);color:var(--foreground);}
[data-testid="stSidebarNav"] a[aria-current="page"]{
  background:var(--accent-soft);color:var(--accent-strong);font-weight:600;
  box-shadow:inset 2px 0 0 var(--accent);
}
/* the entry script is the workspace landing: give it a product name in the rail */
[data-testid="stSidebarNavItems"] > li:first-child [data-testid="stSidebarNavLink"] > span{
  font-size:0;line-height:0;
}
[data-testid="stSidebarNavItems"] > li:first-child [data-testid="stSidebarNavLink"]::after{
  content:"Shift handover";font-size:0.9rem;font-weight:600;letter-spacing:0;line-height:1.3;
}

h1,h2,h3,h4,h5{font-family:var(--font-mono);color:var(--foreground);letter-spacing:-0.01em;}
h1{font-size:1.65rem;font-weight:700;line-height:1.2;margin:0 0 0.25rem;}
h2{font-size:1.1rem;font-weight:600;margin:1.4rem 0 0.5rem;}
h3{font-size:0.95rem;font-weight:600;margin:0 0 0.35rem;}
a{color:var(--accent-strong);}
p,li{line-height:1.55;}

*:focus-visible{outline:2px solid var(--ring);outline-offset:2px;border-radius:4px;}

/* ---------------------------------------------------------------- top bar */
.plume-topbar{
  display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
  border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:18px;
}
.plume-crumbs{
  font-family:var(--font-mono);font-size:11px;letter-spacing:0.09em;text-transform:uppercase;
  color:var(--muted-foreground);min-width:0;
}
.plume-crumbs b{color:var(--accent-strong);font-weight:600;}
.plume-status{
  display:inline-flex;align-items:center;gap:7px;border:1px solid var(--border);
  background:var(--card);border-radius:999px;padding:4px 11px;
  font-family:var(--font-mono);font-size:11px;letter-spacing:0.06em;color:var(--muted-foreground);
}
.plume-dot{width:6px;height:6px;border-radius:50%;background:var(--accent);display:inline-block;}
.plume-dot.live{background:#009E73;}

/* ---------------------------------------------------------------- cards */
.plume-card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:14px 16px;box-shadow:var(--shadow);animation:plume-rise 300ms ease-out both;
}
.plume-grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));}
.plume-grid.two{grid-template-columns:repeat(auto-fit,minmax(280px,1fr));}
@keyframes plume-rise{from{opacity:0.35;transform:translateY(12px);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion: reduce){
  .plume-card,.plume-kpi{animation:none;}
}

/* ---------------------------------------------------------------- signature flag */
.plume-kpi{display:flex;flex-direction:column;gap:6px;min-width:0;}
.plume-kpi-label{
  font-family:var(--font-mono);font-size:10px;font-weight:600;letter-spacing:0.1em;
  text-transform:uppercase;color:var(--muted-foreground);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.plume-kpi-value{
  font-family:var(--font-mono);font-size:1.6rem;font-weight:700;line-height:1.1;
  font-variant-numeric:tabular-nums;color:var(--foreground);overflow-wrap:anywhere;
}
.plume-kpi-value small{font-size:0.72rem;font-weight:400;color:var(--muted-foreground);margin-left:4px;}
.plume-flag{display:flex;align-items:center;gap:5px;min-width:0;}
.plume-leader{width:16px;height:1px;background:var(--accent-line);flex:none;}
.plume-chip{
  font-family:var(--font-mono);font-size:10px;font-weight:600;letter-spacing:0.07em;
  text-transform:uppercase;color:var(--accent-strong);background:var(--accent-soft);
  border:1px solid var(--accent-line);border-radius:5px;padding:2px 6px;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;
}
.plume-chip.neutral{color:var(--muted-foreground);background:var(--muted);border-color:var(--border);}
.plume-chip.down{color:#7fd4b4;background:rgba(0,158,115,0.14);border-color:rgba(0,158,115,0.4);}
.plume-meta{font-size:12.5px;color:var(--muted-foreground);line-height:1.45;}

/* ---------------------------------------------------------------- section head */
.plume-section{
  display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;
  margin:22px 0 10px;
}
.plume-section h2{margin:0;font-size:1rem;}
.plume-section .plume-meta{font-size:12px;}
.plume-eyebrow{
  font-family:var(--font-mono);font-size:10px;font-weight:600;letter-spacing:0.12em;
  text-transform:uppercase;color:var(--muted-foreground);
}

/* ---------------------------------------------------------------- badges */
.plume-badge{
  display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 9px;
  font-family:var(--font-mono);font-size:11px;font-weight:600;letter-spacing:0.06em;
  text-transform:uppercase;border:1px solid var(--border);background:var(--muted);
  color:var(--foreground);white-space:nowrap;
}
.plume-badge .plume-dot{background:currentColor;}
.badge-normal{color:#b9b9c2;border-color:#3a3a44;}
.badge-advisory{color:#6fb7e8;border-color:rgba(0,114,178,0.55);background:rgba(0,114,178,0.12);}
.badge-watch{color:#f0bb54;border-color:rgba(230,159,0,0.55);background:rgba(230,159,0,0.12);}
.badge-warning{color:#f08a7f;border-color:rgba(213,94,0,0.6);background:rgba(213,94,0,0.14);}

/* ---------------------------------------------------------------- alert banner */
.plume-banner{
  display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
  background:linear-gradient(180deg,var(--accent-soft),rgba(22,22,29,0));
  border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:var(--radius);padding:16px 18px;margin-bottom:6px;
}
.plume-banner h2{margin:2px 0 4px;font-size:1.35rem;}
.plume-banner .plume-meta{font-size:13px;}

/* ---------------------------------------------------------------- table */
.plume-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius);background:var(--card);}
table.plume-table{width:100%;border-collapse:collapse;font-size:13.5px;}
.plume-table thead th{
  text-align:left;padding:9px 12px;background:var(--muted);color:var(--muted-foreground);
  font-family:var(--font-mono);font-size:10px;font-weight:600;letter-spacing:0.09em;
  text-transform:uppercase;white-space:nowrap;position:sticky;top:0;
}
.plume-table tbody td{padding:9px 12px;border-top:1px solid var(--border);vertical-align:top;}
.plume-table tbody tr:hover td{background:rgba(152,132,243,0.06);}
.plume-table .num{text-align:right;font-family:var(--font-mono);font-variant-numeric:tabular-nums;}
.plume-table .dim{color:var(--muted-foreground);}

/* ---------------------------------------------------------------- notes */
.plume-note{
  border:1px solid var(--border);border-radius:var(--radius);padding:13px 15px;
  background:var(--card);margin-bottom:10px;
}
.plume-note-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}
.plume-note-temp{
  font-family:var(--font-mono);font-size:1.25rem;font-weight:700;font-variant-numeric:tabular-nums;
}
.plume-note-temp small{font-size:0.7rem;color:var(--muted-foreground);font-weight:400;margin-left:2px;}
.plume-note-body{margin-top:8px;color:#dcdce6;font-size:13.5px;overflow-wrap:anywhere;}

/* ---------------------------------------------------------------- empty / error */
.plume-empty{
  border:1px dashed var(--border);border-radius:var(--radius);padding:22px 20px;
  background:rgba(22,22,29,0.6);text-align:left;
}
.plume-empty strong{display:block;font-family:var(--font-mono);font-size:0.95rem;margin-bottom:4px;}
.plume-error{
  border:1px solid rgba(201,48,45,0.45);background:rgba(201,48,45,0.1);
  border-radius:var(--radius-sm);padding:12px 14px;color:#f3b0ad;font-size:13.5px;
}

/* ---------------------------------------------------------------- streamlit widgets */
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="base-input"]{
  background:var(--muted) !important;border:1px solid var(--border) !important;
  border-radius:var(--radius-sm) !important;color:var(--foreground) !important;
}
[data-baseweb="input"] input,[data-baseweb="textarea"] textarea,[data-baseweb="base-input"] input{
  color:var(--foreground) !important;font-size:0.92rem !important;
}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{
  border-color:var(--ring) !important;box-shadow:0 0 0 2px rgba(152,132,243,0.28) !important;
}
[data-baseweb="select"] > div{
  background:var(--muted) !important;border:1px solid var(--border) !important;
  border-radius:var(--radius-sm) !important;color:var(--foreground) !important;
}
[data-baseweb="select"] > div:hover{border-color:var(--accent) !important;}
[data-baseweb="tag"]{background:var(--accent-soft) !important;color:var(--accent-strong) !important;}
[data-baseweb="popover"] li:hover,[data-baseweb="menu"] li:hover{background:var(--muted) !important;}

.stButton button,[data-testid="stFormSubmitButton"] button,[data-testid="stBaseButton-secondary"]{
  border-radius:var(--radius-sm) !important;border:1px solid var(--border) !important;
  background:var(--muted) !important;color:var(--foreground) !important;
  font-weight:500 !important;transition:background 150ms ease,border-color 150ms ease;
}
.stButton button:hover,[data-testid="stFormSubmitButton"] button:hover{
  border-color:var(--accent) !important;color:var(--accent-strong) !important;
}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{
  background:var(--accent) !important;border-color:var(--accent) !important;
  color:var(--on-accent) !important;font-weight:600 !important;
}
[data-testid="stBaseButton-primary"]:hover,[data-testid="stBaseButton-primaryFormSubmit"]:hover{
  background:var(--accent-strong) !important;border-color:var(--accent-strong) !important;
  color:var(--on-accent) !important;
}
.stButton button:disabled,[data-testid="stFormSubmitButton"] button:disabled{
  opacity:0.45 !important;cursor:not-allowed !important;
}

[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--card) !important;border:1px solid var(--border) !important;
  border-radius:var(--radius) !important;
}
[data-testid="stForm"]{border:none;padding:0;}
[data-testid="stExpander"] details{
  border:1px solid var(--border) !important;border-radius:var(--radius-sm) !important;
  background:var(--card) !important;
}
[data-testid="stExpander"] summary:hover{color:var(--accent-strong);}
[data-testid="stCheckbox"] label p{font-size:0.9rem;}
[data-testid="stRadio"] label p,[data-testid="stMultiSelect"] label p{font-size:0.88rem;}
.stSelectbox [data-testid="stWidgetLabel"],.stMultiSelect [data-testid="stWidgetLabel"],
.stTextInput [data-testid="stWidgetLabel"],.stNumberInput [data-testid="stWidgetLabel"],
.stDateInput [data-testid="stWidgetLabel"],.stTimeInput [data-testid="stWidgetLabel"],
.stTextArea [data-testid="stWidgetLabel"]{
  font-family:var(--font-mono);font-size:10px;font-weight:600;letter-spacing:0.09em;
  text-transform:uppercase;color:var(--muted-foreground);
}
[data-testid="stAlert"]{border-radius:var(--radius-sm);}
[data-testid="stCaptionContainer"],.stCaption{color:var(--muted-foreground);}
[data-testid="stSidebar"] .stButton button{width:100%;}

/* ---------------------------------------------------------------- small screens */
@media (max-width: 640px){
  [data-testid="stMainBlockContainer"],.block-container{padding:1rem 1rem 3rem;}
  .plume-grid,.plume-grid.two{grid-template-columns:1fr;}
  .plume-kpi-value{font-size:1.35rem;}
  .plume-banner{flex-direction:column;align-items:flex-start;}
  .plume-topbar{gap:6px;}
  .plume-table thead th,.plume-table tbody td{padding:8px 10px;}
}
@media (prefers-reduced-motion: reduce){
  *{animation-duration:0.01ms !important;animation-iteration-count:1 !important;transition-duration:0.01ms !important;}
}</style>"""


def inject() -> None:
    """Write the token sheet into the page once per run."""
    st.markdown(STYLE, unsafe_allow_html=True)
