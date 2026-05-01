import sys
import os
import json
import base64
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.tuning import ziegler_nichols
from core.process import FirstOrderProcess, SecondOrderProcess
from core.controllers import PIDController
from core.simulator import run_simulation
from core.metrics import compute_metrics

# ══════════════════════════════════════════════════════════════════
# 1. PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(page_title="PID Control Studio Pro", layout="wide", page_icon="⚗️")


# ══════════════════════════════════════════════════════════════════
# 2. CANVAS ANIMATED HEADER  (own iframe → zero clip/glitch)
# ══════════════════════════════════════════════════════════════════
# ================= HEADER =================
HEADER_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
body { margin:0; background:#04090f; overflow:hidden; }
canvas { position:absolute; top:0; left:0; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap" rel="stylesheet"/>
</head>
<body>

<canvas id="bg"></canvas>
<canvas id="txt"></canvas>

<script>
const W = window.innerWidth;
const H = 140;

// background
const bg = document.getElementById('bg');
bg.width = W; bg.height = H;
const ctx = bg.getContext('2d');

const nodes = Array.from({length:20}, () => ({
  x:Math.random()*W, y:Math.random()*H,
  vx:(Math.random()-.5)*0.5,
  vy:(Math.random()-.5)*0.5
}));

function animateBG(){
  ctx.clearRect(0,0,W,H);

  nodes.forEach(n=>{
    n.x+=n.vx; n.y+=n.vy;
    if(n.x<0||n.x>W) n.vx*=-1;
    if(n.y<0||n.y>H) n.vy*=-1;

    ctx.beginPath();
    ctx.arc(n.x,n.y,2,0,Math.PI*2);
    ctx.fillStyle='rgba(0,200,150,0.5)';
    ctx.fill();
  });

  requestAnimationFrame(animateBG);
}
animateBG();

// text
const txt = document.getElementById('txt');
txt.width=W; txt.height=H;
const tctx = txt.getContext('2d');

let frame=0;
function animateText(){
  tctx.clearRect(0,0,W,H);

  tctx.font = "900 36px Orbitron";
  tctx.textBaseline = "middle";

  let text = "PID CONTROL SYSTEM DASHBOARD";
  let x=20;
  let y=H*0.55;

  for(let i=0;i<text.length;i++){
    let wave = Math.sin(frame*0.05 + i*0.2);
    tctx.fillStyle = `rgb(0, ${200+wave*40}, ${140+wave*60})`;
    tctx.fillText(text[i], x, y + wave*2);
    x += tctx.measureText(text[i]).width;
  }

  frame++;
  requestAnimationFrame(animateText);
}
animateText();
</script>
</body>
</html>
"""

# ══════════════════════════════════════════════════════════════════
# 3. CSS
# ══════════════════════════════════════════════════════════════════
def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;400;600;800;900&family=Orbitron:wght@400;700;900&display=swap');

    html, body, [class*="css"] {
      font-family: 'Exo 2', sans-serif !important;
      color: #c8e4d8 !important;
    }

    /* Blueprint + glow background */
    .stApp {
      background-color: #040b10 !important;
      background-image:
        linear-gradient(rgba(0,170,120,.055) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,170,120,.055) 1px, transparent 1px),
        linear-gradient(rgba(0,100,180,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,100,180,.035) 1px, transparent 1px),
        radial-gradient(ellipse 65% 40% at 12% 12%, rgba(0,200,130,.07) 0%, transparent 62%),
        radial-gradient(ellipse 50% 38% at 88% 85%, rgba(0,90,200,.08) 0%, transparent 58%),
        radial-gradient(ellipse 35% 28% at 55% 55%, rgba(0,30,60,.55) 0%, transparent 75%) !important;
      background-size:
        80px 80px, 80px 80px,
        20px 20px, 20px 20px,
        100% 100%, 100% 100%, 100% 100% !important;
      background-attachment: fixed !important;
    }

    .block-container {
      padding-top: 1.8rem !important;
      padding-bottom: 2rem !important;
      max-width: 1700px !important;
    }

    /* ── Winner card ── */
    .winner-card {
      background: linear-gradient(135deg, rgba(0,195,135,.07), rgba(0,95,210,.07));
      border: 1px solid rgba(0,210,150,.28);
      border-radius: 10px;
      padding: .85rem 1.15rem;
      position: relative; overflow: hidden;
      animation: wglow 3s ease-in-out infinite;
    }
    @keyframes wglow {
      0%,100%{ box-shadow:0 0 14px rgba(0,210,150,.09); }
      50%    { box-shadow:0 0 32px rgba(0,210,150,.22), 0 0 65px rgba(0,210,150,.05); }
    }
    .winner-card::after {
      content:''; position:absolute; inset:0;
      background:linear-gradient(135deg, transparent 55%, rgba(0,210,150,.05));
      pointer-events:none;
    }
    .winner-label {
      font-family:'Share Tech Mono',monospace;
      font-size:.62rem; letter-spacing:.32em; text-transform:uppercase;
      color:rgba(0,210,150,.48); margin-bottom:.25rem;
    }
    .winner-name {
      font-family:'Orbitron',monospace; font-size:.98rem; font-weight:700;
      color:#00d49a; text-shadow:0 0 12px rgba(0,210,150,.42);
    }

    /* ── Status bar ── */
    .status-bar {
      display:flex; align-items:center; gap:1.4rem;
      padding:.35rem .75rem;
      background:rgba(0,210,150,.03);
      border:1px solid rgba(0,210,150,.09);
      border-radius:6px; margin-bottom:.55rem;
    }
    .status-item {
      display:flex; align-items:center; gap:.35rem;
      font-family:'Share Tech Mono',monospace;
      font-size:.6rem; letter-spacing:.14em; color:rgba(0,195,145,.55); text-transform:uppercase;
    }
    .dot-on {
      width:6px; height:6px; border-radius:50%;
      background:#00d49a; box-shadow:0 0 6px #00d49a;
      animation:dblink 2.2s ease-in-out infinite;
    }
    @keyframes dblink { 0%,100%{opacity:1;} 50%{opacity:.3;} }

    /* ── Pipe divider ── */
    .pipe-div {
      display:flex; align-items:center; gap:0;
      margin:.3rem 0 .7rem 0; height:14px;
    }
    .pipe-h { flex:1; height:2px; background:linear-gradient(90deg,transparent,rgba(0,195,135,.32),rgba(0,160,240,.25),transparent); }
    .pipe-j {
      width:9px; height:9px; border-radius:50%;
      background:rgba(0,195,135,.18);
      border:1px solid rgba(0,195,135,.38);
      box-shadow:0 0 5px rgba(0,195,135,.28);
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
      background:linear-gradient(180deg,#050e18,#040b13) !important;
      border-right:1px solid rgba(0,195,135,.09) !important;
    }
    section[data-testid="stSidebar"] .block-container { padding-top:.35rem !important; }

    .sb-title {
      font-family:'Orbitron',monospace; font-size:.92rem; font-weight:900;
      color:#00d49a; letter-spacing:.1em;
      text-shadow:0 0 14px rgba(0,210,150,.38);
    }
    .sb-sub {
      font-family:'Share Tech Mono',monospace; font-size:.57rem;
      letter-spacing:.2em; color:rgba(0,150,210,.5); text-transform:uppercase; margin-top:.1rem;
    }

    .streamlit-expanderHeader {
      background:rgba(0,195,135,.04) !important;
      border:1px solid rgba(0,195,135,.13) !important;
      border-radius:7px !important;
      font-family:'Exo 2',sans-serif !important; font-weight:700 !important;
      font-size:.82rem !important; color:#7cbfaa !important;
      transition:all .22s !important;
    }
    .streamlit-expanderHeader:hover {
      background:rgba(0,195,135,.09) !important;
      border-color:rgba(0,195,135,.3) !important; color:#00d49a !important;
    }

    /* Sliders */
    .stSlider [role="slider"] {
      background:#00d49a !important; border-color:#00d49a !important;
      box-shadow:0 0 9px rgba(0,210,150,.55) !important;
    }
    .stSlider [data-baseweb="track-fill"] { background:linear-gradient(90deg,#00d49a,#00aaff) !important; }
    .stSlider [data-baseweb="track-background"] { background:rgba(0,195,135,.12) !important; }

    /* Select/number */
    .stSelectbox [data-baseweb="select"] > div {
      background:rgba(0,12,26,.82) !important; border:1px solid rgba(0,195,135,.17) !important;
      border-radius:7px !important; color:#c8e4d8 !important;
    }
    .stSelectbox [data-baseweb="select"] > div:hover { border-color:rgba(0,195,135,.4) !important; }
    .stNumberInput input {
      background:rgba(0,12,26,.82) !important; border:1px solid rgba(0,195,135,.17) !important;
      border-radius:7px !important; color:#c8e4d8 !important;
      font-family:'Share Tech Mono',monospace !important;
    }
    .stNumberInput input:focus {
      border-color:#00d49a !important; box-shadow:0 0 9px rgba(0,210,150,.22) !important;
    }
    .stRadio [role="radio"] { border-color:rgba(0,195,135,.32) !important; }
    .stRadio [aria-checked="true"] { background:rgba(0,195,135,.17) !important; border-color:#00d49a !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
      gap:.35rem !important; background:rgba(0,6,18,.72) !important;
      border-radius:10px !important; padding:.32rem !important;
      border:1px solid rgba(0,195,135,.09) !important;
    }
    .stTabs [data-baseweb="tab"] {
      font-family:'Exo 2',sans-serif !important; font-weight:700 !important;
      font-size:.86rem !important; letter-spacing:.04em !important;
      padding:.58rem 1.25rem !important; border-radius:7px !important;
      color:#3a6050 !important; transition:all .22s !important;
    }
    .stTabs [aria-selected="true"] {
      background:linear-gradient(135deg,rgba(0,195,135,.13),rgba(0,110,215,.13)) !important;
      color:#00d49a !important; box-shadow:0 0 12px rgba(0,195,135,.12) !important;
      border-bottom:2px solid #00d49a !important;
    }
    .stTabs [data-baseweb="tab"]:hover { color:#70bfa0 !important; }

    /* Metrics */
    [data-testid="metric-container"] {
      background:linear-gradient(135deg,rgba(0,195,135,.05),rgba(0,75,170,.05)) !important;
      border:1px solid rgba(0,195,135,.15) !important;
      border-radius:10px !important; padding:.95rem !important;
      transition:all .22s !important;
    }
    [data-testid="metric-container"]:hover {
      border-color:rgba(0,195,135,.38) !important;
      box-shadow:0 0 18px rgba(0,195,135,.09) !important;
      transform:translateY(-2px) !important;
    }
    [data-testid="metric-container"] label {
      font-family:'Share Tech Mono',monospace !important; font-size:.65rem !important;
      letter-spacing:.13em !important; text-transform:uppercase !important;
      color:rgba(0,175,195,.55) !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
      font-family:'Orbitron',monospace !important; font-size:1.42rem !important;
      font-weight:700 !important; color:#00d49a !important;
    }

    /* Buttons */
    .stButton > button, .stDownloadButton > button {
      font-family:'Exo 2',sans-serif !important; font-weight:800 !important;
      letter-spacing:.1em !important; text-transform:uppercase !important;
      background:linear-gradient(135deg,rgba(0,195,135,.1),rgba(0,90,195,.1)) !important;
      border:1px solid rgba(0,195,135,.3) !important; color:#00d49a !important;
      border-radius:7px !important; transition:all .22s !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
      background:linear-gradient(135deg,rgba(0,195,135,.2),rgba(0,90,195,.2)) !important;
      border-color:#00d49a !important; box-shadow:0 0 18px rgba(0,195,135,.26) !important;
      transform:translateY(-2px) !important; color:#fff !important;
    }

    .stInfo {
      background:rgba(0,195,135,.05) !important;
      border:1px solid rgba(0,195,135,.2) !important; border-radius:7px !important;
    }
    hr {
      border:none !important; height:1px !important;
      background:linear-gradient(90deg,transparent,rgba(0,195,135,.22),transparent) !important;
      margin:.65rem 0 !important;
    }
    h3 { font-family:'Exo 2',sans-serif !important; font-weight:800 !important;
         color:#7abfaa !important; letter-spacing:.04em !important; }
    .stJson {
      background:rgba(0,6,18,.82) !important;
      border:1px solid rgba(0,195,135,.1) !important; border-radius:10px !important;
      font-family:'Share Tech Mono',monospace !important;
    }
    .vessel-wrap { opacity:.52; margin-top:1.1rem; }
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# 4. HELPERS
# ══════════════════════════════════════════════════════════════════
def calculate_score(metrics, weights=(1.0, 1.0, 1.0)):
    w_ise, w_os, w_st = weights
    d = 1.0 + w_ise*metrics.get("ISE",0) + w_os*metrics.get("overshoot_%",0) + w_st*metrics.get("settling_time_s",0)
    return 100.0 / max(d, 1e-6)


def decimate(t, *arrays, max_points=1500):
    n = len(t)
    if n <= max_points:
        return (t,) + arrays
    idx = np.linspace(0, n-1, max_points, dtype=int)
    return (t[idx],) + tuple(a[idx] for a in arrays)


_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(4,9,15,0)",
    plot_bgcolor="rgba(4,11,20,.74)",
    font=dict(family="Share Tech Mono, monospace", color="#6aaa90", size=11),
    legend=dict(bgcolor="rgba(4,9,20,.9)", bordercolor="rgba(0,195,135,.16)",
                borderwidth=1, font=dict(family="Share Tech Mono, monospace", size=10)),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="rgba(4,12,28,.97)", bordercolor="rgba(0,195,135,.28)",
                    font=dict(family="Share Tech Mono, monospace", size=11)),
    margin=dict(l=56, r=22, t=42, b=36),
)
_AXIS = dict(
    showgrid=True, gridwidth=1, gridcolor="rgba(0,175,115,.07)",
    zeroline=True, zerolinecolor="rgba(0,175,115,.16)", zerolinewidth=1,
    linecolor="rgba(0,175,115,.13)",
    tickfont=dict(family="Share Tech Mono, monospace", size=10),
    title_font=dict(family="Exo 2, sans-serif", size=11),
)
C = dict(sp="#cce8d8", mpv="#00d49a", mop="#00a87a", mer="#007855",
         apv="#00aaff", aop="#0088cc", aer="#005588")


def make_time_series_fig(res_manual, res_auto=None):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=.062,
        subplot_titles=("Process Variable (PV) & Setpoint","Controller Output (OP)","Tracking Error (e)"),
        row_heights=[.46,.30,.24])

    t,y,u,e,ysp,_ = res_manual.as_arrays()
    t,y,u,e,ysp   = decimate(t,y,u,e,ysp)

    fig.add_trace(go.Scatter(x=t,y=ysp,name="Setpoint",
        line=dict(color=C["sp"],dash="dash",width=1.3),opacity=.45),row=1,col=1)
    fig.add_trace(go.Scatter(x=t,y=y,name="Manual PV",
        line=dict(color=C["mpv"],width=1.8),
        fill="tozeroy",fillcolor="rgba(0,212,154,.04)"),row=1,col=1)
    fig.add_trace(go.Scatter(x=t,y=u,name="Manual OP",
        line=dict(color=C["mop"],width=1.8)),row=2,col=1)
    fig.add_trace(go.Scatter(x=t,y=e,name="Manual Error",
        line=dict(color=C["mer"],width=1.8),
        fill="tozeroy",fillcolor="rgba(0,170,100,.04)"),row=3,col=1)

    if res_auto:
        t2,y2,u2,e2,_,_ = res_auto.as_arrays()
        t2,y2,u2,e2 = decimate(t2,y2,u2,e2)
        fig.add_trace(go.Scatter(x=t2,y=y2,name="Auto PV",
            line=dict(color=C["apv"],width=1.8,dash="dot")),row=1,col=1)
        fig.add_trace(go.Scatter(x=t2,y=u2,name="Auto OP",
            line=dict(color=C["aop"],width=1.8,dash="dot")),row=2,col=1)
        fig.add_trace(go.Scatter(x=t2,y=e2,name="Auto Error",
            line=dict(color=C["aer"],width=1.8,dash="dot")),row=3,col=1)

    fig.update_layout(**_LAYOUT, height=720)
    for r in range(1,4):
        fig.update_xaxes(**_AXIS,row=r,col=1)
        fig.update_yaxes(**_AXIS,row=r,col=1)
    fig.update_xaxes(title_text="Time (s)",row=3,col=1)
    return fig


def plot_performance_comparison(m_manual, m_auto):
    keys   = ["ISE","overshoot_%","settling_time_s","ss_error"]
    labels = ["ISE","Overshoot (%)","Settling Time (s)","SS Error"]
    fig = go.Figure([
        go.Bar(name="Manual",x=labels,y=[m_manual.get(k,0) for k in keys],
               marker=dict(color="rgba(0,210,150,.7)",line=dict(color="#00d49a",width=1.3))),
        go.Bar(name="Auto (Z-N)",x=labels,y=[m_auto.get(k,0) for k in keys],
               marker=dict(color="rgba(0,155,245,.7)",line=dict(color="#00aaff",width=1.3))),
    ])
    fig.update_layout(**_LAYOUT,barmode="group",height=340,
        title=dict(text="KPI Comparison — Lower is Better",
                   font=dict(family="Exo 2, sans-serif",size=13,color="#7abfaa")))
    fig.update_xaxes(**_AXIS); fig.update_yaxes(**_AXIS)
    return fig


def build_print_html(res_manual, res_auto=None):
    import plotly.io as pio
    fig = make_time_series_fig(res_manual, res_auto)
    fig.update_layout(paper_bgcolor="#fff",plot_bgcolor="#f3f8f5",
                      font=dict(color="#111"),template="plotly_white")
    chart = pio.to_html(fig,full_html=False,include_plotlyjs="cdn")
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'/><title>PID Graph Report</title>"
            f"<style>body{{font-family:'Courier New',monospace;margin:2rem;background:#fff;color:#111;}}"
            f"h1{{font-size:1.3rem;border-bottom:2px solid #007755;padding-bottom:.4rem;}}"
            f"@media print{{button{{display:none!important;}}}}</style>"
            f"<script>window.onload=function(){{window.print();}}</script></head>"
            f"<body><h1>⚗ PID Control Studio — Graph Report</h1>{chart}</body></html>")


# CSTR decorative SVG for sidebar
CSTR_SVG = """<div class="vessel-wrap">
<svg width="158" height="138" viewBox="0 0 158 138" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:auto;">
  <rect x="34" y="29" width="90" height="74" rx="5" fill="none" stroke="rgba(0,195,135,.4)" stroke-width="1.4"/>
  <ellipse cx="79" cy="29" rx="45" ry="7.5" fill="rgba(0,195,135,.05)" stroke="rgba(0,195,135,.35)" stroke-width="1.1"/>
  <ellipse cx="79" cy="103" rx="45" ry="7.5" fill="rgba(0,195,135,.05)" stroke="rgba(0,195,135,.35)" stroke-width="1.1"/>
  <line x1="79" y1="21" x2="79" y2="54" stroke="rgba(0,195,135,.48)" stroke-width="1.4"/>
  <line x1="55" y1="54" x2="103" y2="54" stroke="rgba(0,195,135,.55)" stroke-width="1.9"/>
  <line x1="59" y1="47" x2="99" y2="61" stroke="rgba(0,195,135,.28)" stroke-width=".9"/>
  <line x1="0" y1="37" x2="34" y2="37" stroke="rgba(0,170,245,.48)" stroke-width="1.8"/>
  <circle cx="0" cy="37" r="2.8" fill="rgba(0,170,245,.38)"/>
  <text x="2" y="33" font-size="6.5" fill="rgba(0,170,245,.5)" font-family="monospace">Feed</text>
  <line x1="124" y1="94" x2="158" y2="94" stroke="rgba(0,195,135,.48)" stroke-width="1.8"/>
  <circle cx="158" cy="94" r="2.8" fill="rgba(0,195,135,.38)"/>
  <text x="126" y="90" font-size="6.5" fill="rgba(0,195,135,.5)" font-family="monospace">Out</text>
  <rect x="27" y="35" width="5.5" height="62" rx="2" fill="none" stroke="rgba(0,130,245,.22)" stroke-width=".9" stroke-dasharray="3,3"/>
  <rect x="125.5" y="35" width="5.5" height="62" rx="2" fill="none" stroke="rgba(0,130,245,.22)" stroke-width=".9" stroke-dasharray="3,3"/>
  <circle cx="64" cy="87" r="2.8" fill="rgba(0,195,135,.11)" stroke="rgba(0,195,135,.28)" stroke-width=".7"/>
  <circle cx="79" cy="77" r="3.8" fill="rgba(0,195,135,.09)" stroke="rgba(0,195,135,.22)" stroke-width=".7"/>
  <circle cx="95" cy="84" r="2.3" fill="rgba(0,195,135,.11)" stroke="rgba(0,195,135,.26)" stroke-width=".7"/>
  <text x="61" y="65" font-size="7.5" fill="rgba(0,195,135,.38)" font-family="monospace">CSTR</text>
  <text x="50" y="121" font-size="6" fill="rgba(0,155,200,.32)" font-family="monospace">Continuous Stirred</text>
  <text x="57" y="131" font-size="6" fill="rgba(0,155,200,.32)" font-family="monospace">Tank Reactor</text>
</svg></div>"""


# ══════════════════════════════════════════════════════════════════
# 5. MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    apply_custom_css()

    # ── Sidebar ─────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sb-title">⚗ PID STUDIO</div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-sub">Chemical Process Control</div>', unsafe_allow_html=True)
        st.markdown("""<div class="status-bar">
          <div class="status-item"><div class="dot-on"></div>Solver Online</div>
          <div class="status-item"><div class="dot-on"></div>Sim Ready</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("---")

        with st.expander("🧪 Process Dynamics", expanded=True):
            process_type = st.selectbox("Process Type", ["First-order", "Second-order"])
            K_p   = st.slider("Process Gain (Kp)",     0.1, 5.0,  1.0, 0.1)
            tau_p = st.slider("Time Constant (τ)",     0.5, 30.0, 5.0, 0.5)
            theta = st.slider("Dead Time (θ)",          0.0, 5.0,  0.0, 0.1)
            K_d   = st.slider("Disturbance Gain (Kd)", 0.0, 3.0,  0.5, 0.1)
            zeta  = 0.5
            if "Second" in process_type:
                zeta = st.slider("Damping Ratio (ζ)", 0.1, 2.0, 0.5, 0.1)

        with st.expander("⚙️ Controller Tuning", expanded=True):
            mode = st.radio("Tuning Mode", ["Manual PID", "Compare with Auto (Z-N)"])
            st.markdown("**Manual Parameters**")
            Kc    = st.slider("Proportional Gain (Kc)", 0.1, 20.0, 2.0, 0.1)
            tau_I = st.slider("Integral Time (τI)",      0.1, 50.0, 5.0, 0.1)
            tau_D = st.slider("Derivative Time (τD)",    0.0, 10.0, 0.0, 0.1)

            Kc_auto = tau_I_auto = tau_D_auto = None
            if mode == "Compare with Auto (Z-N)":
                st.markdown("---")
                st.markdown("**Ziegler-Nichols Parameters**")
                Ku = st.number_input("Ultimate Gain (Ku)",      0.1, 50.0,  5.0,  step=0.5)
                Pu = st.number_input("Oscillation Period (Pu)", 1.0, 100.0, 20.0, step=1.0)
                Kc_auto, tau_I_auto, tau_D_auto = ziegler_nichols(Ku, Pu)
                st.info(f"**Calculated Z-N:**\n\nKc: `{Kc_auto:.2f}` | τI: `{tau_I_auto:.2f}` | τD: `{tau_D_auto:.2f}`")

        with st.expander("⚡ Scenario & Simulation", expanded=False):
            scenario = st.selectbox("Test Scenario",
                ["Servo (Setpoint Tracking)", "Regulator (Disturbance Rejection)", "Combined"])
            sp_value = st.number_input("Setpoint Step",       0.1, 10.0, 1.0)
            sp_time  = st.slider("Setpoint Step Time",        0.0, 100.0, 20.0)
            d_value  = st.number_input("Disturbance Step",    0.0, 10.0, 1.0)
            d_time   = st.slider("Disturbance Step Time",     0.0, 200.0, 60.0)
            st.markdown("---")
            t_end = st.slider("Simulation Time (s)", 50, 500, 200, step=10)
            dt    = st.select_slider("Time Step (dt)", [0.01, 0.05, 0.1, 0.5], 0.1)

        st.markdown(CSTR_SVG, unsafe_allow_html=True)

    # ── Process & scenario ───────────────────────────────────────
    if "Second" in process_type:
        p1 = SecondOrderProcess(K_p=K_p, tau=tau_p, zeta=zeta, K_d=K_d)
        p2 = SecondOrderProcess(K_p=K_p, tau=tau_p, zeta=zeta, K_d=K_d)
    else:
        p1 = FirstOrderProcess(K_p=K_p, tau_p=tau_p, K_d=K_d, theta=theta)
        p2 = FirstOrderProcess(K_p=K_p, tau_p=tau_p, K_d=K_d, theta=theta)

    if "Servo" in scenario:
        sp = lambda t: sp_value if t >= sp_time else 0.0
        d  = lambda t: 0.0
    elif "Regulator" in scenario:
        sp = lambda t: 0.0
        d  = lambda t: d_value if t >= d_time else 0.0
    else:
        sp = lambda t: sp_value if t >= sp_time else 0.0
        d  = lambda t: d_value if t >= d_time else 0.0

    ctrl_manual  = PIDController(Kc=Kc, tau_I=tau_I, tau_D=tau_D)
    res_manual   = run_simulation(p1, ctrl_manual, sp, d, t_end, dt)
    m_manual     = compute_metrics(res_manual)
    score_manual = calculate_score(m_manual)

    res_auto = m_auto = score_auto = None
    if Kc_auto is not None:
        ctrl_auto  = PIDController(Kc=Kc_auto, tau_I=tau_I_auto, tau_D=tau_D_auto)
        res_auto   = run_simulation(p2, ctrl_auto, sp, d, t_end, dt)
        m_auto     = compute_metrics(res_auto)
        score_auto = calculate_score(m_auto)

    best = "Manual Tuning"
    if res_auto and score_auto > score_manual:
        best = "Auto (Ziegler-Nichols)"

    # ── Canvas header (own iframe — no clip glitch ever) ─────────
    components.html(HEADER_HTML, height=140, scrolling=False)

    # ── Pipe divider + winner ─────────────────────────────────────
    col_p, col_w = st.columns([5, 2])
    with col_p:
        st.markdown("""<div class="pipe-div">
          <div class="pipe-h"></div><div class="pipe-j"></div>
          <div class="pipe-h"></div><div class="pipe-j"></div>
          <div class="pipe-h"></div><div class="pipe-j"></div>
          <div class="pipe-h"></div>
        </div>""", unsafe_allow_html=True)
    with col_w:
        st.markdown(f"""<div class="winner-card">
          <div class="winner-label">🏆 Top Performer</div>
          <div class="winner-name">{best}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────
    tab_plots, tab_metrics, tab_export = st.tabs([
        "📈 Time Series Analysis", "📊 Performance Metrics", "📥 Data & Export"])

    with tab_plots:
        fig = make_time_series_fig(res_manual, res_auto)
        st.plotly_chart(fig, use_container_width=True)

        ph  = build_print_html(res_manual, res_auto)
        b64 = base64.b64encode(ph.encode()).decode()
        st.markdown(
            f"""<div style="display:flex;justify-content:flex-end;margin-top:-.4rem;">
              <a href="data:text/html;base64,{b64}" download="pid_graphs.html" target="_blank"
                 style="font-family:'Exo 2',sans-serif;font-weight:800;font-size:.77rem;
                 letter-spacing:.1em;text-transform:uppercase;text-decoration:none;
                 background:linear-gradient(135deg,rgba(0,90,195,.14),rgba(0,45,155,.1));
                 border:1px solid rgba(0,150,245,.38);color:#00aaff;
                 border-radius:7px;padding:.42rem 1.05rem;display:inline-block;"
                 onmouseover="this.style.boxShadow='0 0 18px rgba(0,140,245,.32)';this.style.color='#fff';"
                 onmouseout="this.style.boxShadow='none';this.style.color='#00aaff';">
                🖨 Export &amp; Print Graphs
              </a></div>""",
            unsafe_allow_html=True)

    with tab_metrics:
        if res_auto:
            st.markdown("### Metric Comparison — Auto vs Manual")
            mc4 = st.columns(4)
            for i,(key,label) in enumerate([
                ("ISE","Integral Square Error"),("overshoot_%","Overshoot (%)"),
                ("settling_time_s","Settling Time (s)"),("ss_error","Steady State Error")]):
                man_v  = m_manual.get(key,0)
                auto_v = m_auto.get(key,0)
                with mc4[i]:
                    st.metric(label=f"Auto {label}", value=f"{auto_v:.3f}",
                              delta=f"{auto_v-man_v:.3f} vs Man", delta_color="inverse")
            st.markdown("")
            st.plotly_chart(plot_performance_comparison(m_manual, m_auto), use_container_width=True)
        else:
            st.markdown("### Manual Controller Performance")
            mc4 = st.columns(4)
            mc4[0].metric("ISE",               f"{m_manual.get('ISE',0):.3f}")
            mc4[1].metric("Overshoot (%)",     f"{m_manual.get('overshoot_%',0):.3f}")
            mc4[2].metric("Settling Time (s)", f"{m_manual.get('settling_time_s',0):.3f}")
            mc4[3].metric("SS Error",           f"{m_manual.get('ss_error',0):.3f}")

    with tab_export:
        st.markdown("### JSON Engineering Report")
        report = {
            "setup": {"process_type":process_type,"scenario":scenario,"dt":dt,"t_end":t_end},
            "results_manual": m_manual,
            "results_auto":   m_auto if res_auto else None,
            "overall_best":   best,
        }
        st.json(report)
        st.download_button(
            label="📥 Download Engineering Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name="pid_control_report.json",
            mime="application/json",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()