import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- Page Config ---
st.set_page_config(
    page_title="Rahul Pro Index Terminal (100% Real Data)",
    page_icon="⚡",
    layout="wide"
)

# --- Custom CSS (Angel One Style Clean Cards) ---
st.markdown("""
<style>
    .index-card {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .index-title {
        font-size: 13px;
        font-weight: 600;
        color: #4a5568;
        margin-bottom: 4px;
    }
    .index-price {
        font-size: 18px;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 2px;
    }
    .up-text {
        color: #00a878;
        font-size: 12px;
        font-weight: 600;
    }
    .down-text {
        color: #e53e3e;
        font-size: 12px;
        font-weight: 600;
    }
    .neutral-text {
        color: #718096;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 8 Indices List (Exact Same as Your App) ---
INDICES = {
    "Nifty 50": ["^NSEI"],
    "Bank Nifty": ["^NSEBANK"],
    "Fin Nifty": ["NIFTY_FIN_SERVICE.NS", "^CNXFIN"],
    "Midcap Nifty": ["^NSEMDCP50", "NIFTY_MID_SELECT.NS"],
    "Sensex": ["^BSESN"],
    "Gift Nifty": ["GIFTY.NS", "^NSEI"],
    "India VIX": ["^INDIAVIX"],
    "Dow Jones": ["^DJI"]
}

@st.cache_data(ttl=30)
def fetch_real_index_data(tickers):
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="5d", interval="1d", progress=False)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna(subset=["Close"])
                if len(df) >= 2:
                    today = df.iloc[-1]
                    prev = df.iloc[-2]

                    cmp = float(today["Close"])
                    open_p = float(today["Open"])
                    day_high = float(today["High"])
                    day_low = float(today["Low"])

                    prev_high = float(prev["High"])
                    prev_low = float(prev["Low"])
                    prev_close = float(prev["Close"])

                    change = cmp - prev_close
                    pct_change = (change / prev_close) * 100 if prev_close != 0 else 0.0

                    # Classic Pivot Points (100% Real Mathematical Formula from Prev H/L/C)
                    pivot = (prev_high + prev_low + prev_close) / 3
                    r1 = (2 * pivot) - prev_low
                    s1 = (2 * pivot) - prev_high
                    r2 = pivot + (prev_high - prev_low)
                    s2 = pivot - (prev_high - prev_low)

                    return {
                        "available": True,
                        "ticker": ticker,
                        "cmp": cmp,
                        "open": open_p,
                        "day_high": day_high,
                        "day_low": day_low,
                        "prev_high": prev_high,
                        "prev_low": prev_low,
                        "prev_close": prev_close,
                        "change": change,
                        "pct_change": pct_change,
                        "pivot": pivot,
                        "r1": r1,
                        "r2": r2,
                        "s1": s1,
                        "s2": s2,
                        "history": df
                    }
        except Exception:
            continue
    return {"available": False}

# --- Header ---
ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist).strftime("%d %b %Y, %I:%M:%S %p IST")

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("## ⚡ Rahul Pro Index Terminal (100% Real Data)")
    st.caption(f"Last Updated: {now_ist} | Only Real Market Price, Prev High/Low & Pivot Levels (Zero Sample Data)")
with col_h2:
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

# --- Fetch All 8 Indices ---
all_data = {}
for name, symbols in INDICES.items():
    if name == "Gift Nifty":
        # Only use genuine Gift Nifty symbol; never fake with spot Nifty
        all_data[name] = fetch_real_index_data(["GIFTY.NS"])
    else:
        all_data[name] = fetch_real_index_data(symbols)

# --- Section 1: 8 Index Cards (Angel One Style) ---
st.subheader("📊 Live Market Indices (Angel One Style)")

index_names = list(INDICES.keys())
for row_start in range(0, len(index_names), 4):
    cols = st.columns(4)
    for idx, col in enumerate(cols):
        if row_start + idx < len(index_names):
            name = index_names[row_start + idx]
            d = all_data[name]
            with col:
                if d["available"]:
                    arrow = "▲" if d["change"] >= 0 else "▼"
                    css_cls = "up-text" if d["change"] >= 0 else "down-text"
                    sign = "+" if d["change"] >= 0 else ""
                    st.markdown(f"""
                    <div class="index-card">
                        <div class="index-title">{name}</div>
                        <div class="index-price">{d['cmp']:,.2f}</div>
                        <div class="{css_cls}">{arrow} {sign}{d['change']:,.2f} ({sign}{d['pct_change']:.2f}%)</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="index-card">
                        <div class="index-title">{name}</div>
                        <div class="index-price">N/A</div>
                        <div class="neutral-text">Real Feed Unavailable</div>
                    </div>
                    """, unsafe_allow_html=True)

st.markdown("---")

# --- Section 2: All 8 Indices Real Levels Summary Table ---
st.subheader("📋 All Indices: Day High/Low, Prev High/Low & Real Support/Resistance")

table_rows = []
for name in index_names:
    d = all_data[name]
    if d["available"]:
        table_rows.append({
            "Index": name,
            "Current Price": round(d["cmp"], 2),
            "Day Low": round(d["day_low"], 2),
            "Day High": round(d["day_high"], 2),
            "Prev Day Low": round(d["prev_low"], 2),
            "Prev Day High": round(d["prev_high"], 2),
            "Support 2 (S2)": round(d["s2"], 2),
            "Support 1 (S1)": round(d["s1"], 2),
            "Pivot": round(d["pivot"], 2),
            "Resistance 1 (R1)": round(d["r1"], 2),
            "Resistance 2 (R2)": round(d["r2"], 2),
        })
    else:
        table_rows.append({
            "Index": name,
            "Current Price": "Feed Unavailable",
            "Day Low": "-",
            "Day High": "-",
            "Prev Day Low": "-",
            "Prev Day High": "-",
            "Support 2 (S2)": "-",
            "Support 1 (S1)": "-",
            "Pivot": "-",
            "Resistance 1 (R1)": "-",
            "Resistance 2 (R2)": "-",
        })

st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# --- Section 3: Detailed Index Analyzer (100% Real Levels & Intraday Chart) ---
st.subheader("🎯 Detailed Index Analyzer & Real Support/Resistance Hub")

available_indices = [k for k, v in all_data.items() if v["available"]]
selected_index = st.selectbox("Select Index for Deep Analysis", available_indices)

if selected_index:
    sel = all_data[selected_index]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"{selected_index} - Price", f"{sel['cmp']:,.2f}", f"{sel['change']:+.2f} ({sel['pct_change']:+.2f}%)")
    m2.metric("Today Open", f"{sel['open']:,.2f}")
    m3.metric("Today Day High", f"{sel['day_high']:,.2f}")
    m4.metric("Today Day Low", f"{sel['day_low']:,.2f}")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Prev Day High", f"{sel['prev_high']:,.2f}")
    p2.metric("Prev Day Low", f"{sel['prev_low']:,.2f}")
    p3.metric("Resistance 1 (R1)", f"{sel['r1']:,.2f}")
    p4.metric("Support 1 (S1)", f"{sel['s1']:,.2f}")

    # Intraday 5m Chart with Real Levels
    st.markdown(f"#### 📈 {selected_index} Intraday Candlestick Chart (with Prev High/Low & S1/R1)")
    intra = yf.download(sel["ticker"], period="2d", interval="5m", progress=False)
    if intra is not None and not intra.empty:
        if isinstance(intra.columns, pd.MultiIndex):
            intra.columns = intra.columns.get_level_values(0)
        intra = intra.tail(75)

        fig = go.Figure(data=[go.Candlestick(
            x=intra.index,
            open=intra["Open"],
            high=intra["High"],
            low=intra["Low"],
            close=intra["Close"],
            name=selected_index
        )])

        fig.add_hline(y=sel["prev_high"], line_dash="dash", line_color="red", annotation_text=f"Prev High ({sel['prev_high']:.2f})")
        fig.add_hline(y=sel["prev_low"], line_dash="dash", line_color="green", annotation_text=f"Prev Low ({sel['prev_low']:.2f})")
        fig.add_hline(y=sel["r1"], line_dash="dot", line_color="orange", annotation_text=f"R1 ({sel['r1']:.2f})")
        fig.add_hline(y=sel["s1"], line_dash="dot", line_color="blue", annotation_text=f"S1 ({sel['s1']:.2f})")

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=450,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Intraday candlestick data is currently unavailable from the feed for this index.")
    
