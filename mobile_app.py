import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- Page Setup ---
st.set_page_config(
    page_title="Rahul Pro Index Terminal",
    page_icon="⚡",
    layout="wide"
)

# --- Clean Mobile-Friendly Angel One Style CSS ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .header-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: white;
        padding: 16px 18px;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .header-title {
        font-size: 20px;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
    }
    .header-sub {
        font-size: 12px;
        color: #cbd5e1;
        margin-top: 4px;
    }
    .idx-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
    }
    .idx-name {
        font-size: 13px;
        font-weight: 700;
        color: #475569;
        margin-bottom: 4px;
    }
    .idx-val {
        font-size: 19px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 3px;
    }
    .pos {
        color: #059669;
        font-size: 13px;
        font-weight: 700;
    }
    .neg {
        color: #dc2626;
        font-size: 13px;
        font-weight: 700;
    }
    .na-txt {
        color: #64748b;
        font-size: 12px;
        font-weight: 600;
    }
    .level-card {
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
        background-color: #f8fafc;
    }
    .res-card {
        border-left: 5px solid #dc2626;
        background-color: #fef2f2;
    }
    .sup-card {
        border-left: 5px solid #059669;
        background-color: #ecfdf5;
    }
    .piv-card {
        border-left: 5px solid #2563eb;
        background-color: #eff6ff;
    }
    .lvl-label {
        font-size: 12px;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
    }
    .lvl-num {
        font-size: 18px;
        font-weight: 800;
        color: #0f172a;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# --- 8 Indices List ---
INDICES = {
    "Nifty 50": ["^NSEI"],
    "Bank Nifty": ["^NSEBANK"],
    "Fin Nifty": ["NIFTY_FIN_SERVICE.NS", "^CNXFIN"],
    "Midcap Nifty": ["^NSEMDCP50", "NIFTY_MID_SELECT.NS"],
    "Sensex": ["^BSESN"],
    "Gift Nifty": ["GIFTY.NS"],
    "India VIX": ["^INDIAVIX"],
    "Dow Jones": ["^DJI"]
}

@st.cache_data(ttl=30)
def get_real_data(tickers):
    for t in tickers:
        try:
            df = yf.download(t, period="2mo", interval="1d", progress=False)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna(subset=["Open", "High", "Low", "Close"])
                if len(df) >= 2:
                    today = df.iloc[-1]
                    prev = df.iloc[-2]

                    cmp = float(today["Close"])
                    open_p = float(today["Open"])
                    d_high = float(today["High"])
                    d_low = float(today["Low"])

                    p_high = float(prev["High"])
                    p_low = float(prev["Low"])
                    p_close = float(prev["Close"])

                    chg = cmp - p_close
                    pct = (chg / p_close) * 100 if p_close != 0 else 0.0
                    gap = open_p - p_close

                    # Classic Pivot Points (Real Formula from Prev High, Low, Close)
                    piv = (p_high + p_low + p_close) / 3
                    r1 = (2 * piv) - p_low
                    s1 = (2 * piv) - p_high
                    r2 = piv + (p_high - p_low)
                    s2 = piv - (p_high - p_low)

                    return {
                        "ok": True,
                        "ticker": t,
                        "cmp": cmp,
                        "open": open_p,
                        "d_high": d_high,
                        "d_low": d_low,
                        "p_high": p_high,
                        "p_low": p_low,
                        "p_close": p_close,
                        "chg": chg,
                        "pct": pct,
                        "gap": gap,
                        "piv": piv,
                        "r1": r1,
                        "r2": r2,
                        "s1": s1,
                        "s2": s2,
                        "df": df.tail(30)
                    }
        except Exception:
            continue
    return {"ok": False}

# --- Header ---
ist = pytz.timezone("Asia/Kolkata")
now_str = datetime.now(ist).strftime("%d %b %Y | %I:%M %p IST")

st.markdown(f"""
<div class="header-box">
    <div class="header-title">⚡ Rahul Pro Index Terminal</div>
    <div class="header-sub">100% Real Market Data • Zero Fake/Sample Numbers • {now_str}</div>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh Live Prices", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- Fetch Data for All 8 Indices ---
data_map = {name: get_real_data(syms) for name, syms in INDICES.items()}

# --- Section 1: 8 Index Cards (Clean Grid) ---
st.markdown("### 📊 Live Market Indices")

names = list(INDICES.keys())
for i in range(0, len(names), 2):
    c1, c2 = st.columns(2)
    for idx, col in enumerate([c1, c2]):
        if i + idx < len(names):
            nm = names[i + idx]
            item = data_map[nm]
            with col:
                if item["ok"]:
                    is_up = item["chg"] >= 0
                    arr = "▲" if is_up else "▼"
                    cls = "pos" if is_up else "neg"
                    sgn = "+" if is_up else ""
                    st.markdown(f"""
                    <div class="idx-card">
                        <div class="idx-name">{nm}</div>
                        <div class="idx-val">{item['cmp']:,.2f}</div>
                        <div class="{cls}">{arr} {sgn}{item['chg']:,.2f} ({sgn}{item['pct']:.2f}%)</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="idx-card">
                        <div class="idx-name">{nm}</div>
                        <div class="idx-val">N/A</div>
                        <div class="na-txt">Feed Unavailable</div>
                    </div>
                    """, unsafe_allow_html=True)

st.markdown("---")

# --- Section 2: Single Index Deep Analyzer ---
st.markdown("### 🎯 Index Levels & Support / Resistance")

valid_names = [k for k, v in data_map.items() if v["ok"]]
chosen = st.selectbox("Select Index to View Full Levels", valid_names, index=0)

if chosen:
    d = data_map[chosen]

    # Row 1: Current & Today Range
    a1, a2 = st.columns(2)
    with a1:
        st.markdown(f"""
        <div class="level-card">
            <div class="lvl-label">{chosen} Price</div>
            <div class="lvl-num">{d['cmp']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with a2:
        gap_txt = f"Gap Up +{d['gap']:,.2f}" if d["gap"] >= 0 else f"Gap Down {d['gap']:,.2f}"
        st.markdown(f"""
        <div class="level-card">
            <div class="lvl-label">Today Open ({gap_txt})</div>
            <div class="lvl-num">{d['open']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(f"""
        <div class="level-card">
            <div class="lvl-label">Today Day High</div>
            <div class="lvl-num">{d['d_high']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with b2:
        st.markdown(f"""
        <div class="level-card">
            <div class="lvl-label">Today Day Low</div>
            <div class="lvl-num">{d['d_low']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 2: Previous Day High & Low
    p1, p2 = st.columns(2)
    with p1:
        st.markdown(f"""
        <div class="level-card res-card">
            <div class="lvl-label">Previous Day High</div>
            <div class="lvl-num">{d['p_high']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        st.markdown(f"""
        <div class="level-card sup-card">
            <div class="lvl-label">Previous Day Low</div>
            <div class="lvl-num">{d['p_low']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 3: Real Support & Resistance Levels
    st.markdown("#### 🛡️ Real Support & Resistance Levels")

    r1_col, r2_col = st.columns(2)
    with r1_col:
        st.markdown(f"""
        <div class="level-card res-card">
            <div class="lvl-label">Resistance 1 (R1)</div>
            <div class="lvl-num">{d['r1']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with r2_col:
        st.markdown(f"""
        <div class="level-card res-card">
            <div class="lvl-label">Resistance 2 (R2)</div>
            <div class="lvl-num">{d['r2']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="level-card piv-card">
        <div class="lvl-label">Central Pivot Level</div>
        <div class="lvl-num">{d['piv']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    s1_col, s2_col = st.columns(2)
    with s1_col:
        st.markdown(f"""
        <div class="level-card sup-card">
            <div class="lvl-label">Support 1 (S1)</div>
            <div class="lvl-num">{d['s1']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with s2_col:
        st.markdown(f"""
        <div class="level-card sup-card">
            <div class="lvl-label">Support 2 (S2)</div>
            <div class="lvl-num">{d['s2']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 4: Clean 30-Day Real Candlestick Chart
    st.markdown(f"#### 📈 {chosen} Daily Candlestick Chart (Last 30 Sessions)")
    cdf = d["df"]
    x_dates = [idx.strftime("%d %b") for idx in cdf.index]

    fig = go.Figure(data=[go.Candlestick(
        x=x_dates,
        open=cdf["Open"],
        high=cdf["High"],
        low=cdf["Low"],
        close=cdf["Close"],
        increasing_line_color="#059669",
        decreasing_line_color="#dc2626",
        name=chosen
    )])

    fig.add_hline(y=d["p_high"], line_dash="dash", line_color="#dc2626", annotation_text="Prev High")
    fig.add_hline(y=d["p_low"], line_dash="dash", line_color="#059669", annotation_text="Prev Low")

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=380,
        margin=dict(l=5, r=5, t=25, b=20),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff"
    )
    st.plotly_chart(fig, use_container_width=True)
    
