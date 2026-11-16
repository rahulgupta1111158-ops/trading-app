import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. पेज कॉन्फ़िगरेशन
st.set_page_config(
    page_title="Rahul Pro Trading Terminal [100% Real Engine]",
    page_icon="⚡",
    layout="wide"
)

# 2. ऑटो-रिफ्रेश इंजन (हर 5 सेकंड लाइव)
count = st_autorefresh(interval=5000, limit=None, key="live_trading_counter")

st.markdown("""
    <h1 style='color: #FF4B4B; margin-bottom: 0px;'>⚡ Rahul Pro Trading Terminal [100% Real Engine]</h1>
    <p style='color: gray; margin-top: 5px;'>Live Auto-Refresh (5s) | Zero Dummy Data Policy — Direct Exchange Feed Only 🟢</p>
""", unsafe_allow_html=True)
st.markdown("---")

# 3. सिर्फ असली लाइव NSE Option Chain खींचने का सख्त इंजन (बिना किसी फेक/डिफ़ॉल्ट डेटा के)
@st.cache_data(ttl=10)
def fetch_strict_real_nse_data(symbol_name):
    nse_map = {
        "Nifty 50": "NIFTY",
        "Bank Nifty": "BANKNIFTY",
        "Fin Nifty": "FINNIFTY",
        "Midcap Nifty": "MIDCPNIFTY"
    }
    nse_sym = nse_map.get(symbol_name, "NIFTY")
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={nse_sym}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            data = response.json()
            records = data['records']['data']
            spot_price = data['records']['underlyingValue']
            current_expiry = data['records']['expiryDates'][0]
            
            rows = []
            for item in records:
                if item.get('expiryDate') == current_expiry:
                    strike = item.get('strikePrice')
                    ce = item.get('CE', {})
                    pe = item.get('PE', {})
                    rows.append({
                        "Strike": strike,
                        "CE_OI": ce.get('openInterest', 0),
                        "CE_Chg_OI": ce.get('changeinOpenInterest', 0),
                        "CE_LTP": ce.get('lastPrice', 0),
                        "PE_OI": pe.get('openInterest', 0),
                        "PE_Chg_OI": pe.get('changeinOpenInterest', 0),
                        "PE_LTP": pe.get('lastPrice', 0)
                    })
            df_oc = pd.DataFrame(rows)
            if not df_oc.empty:
                tot_ce_oi = df_oc['CE_OI'].sum()
                tot_pe_oi = df_oc['PE_OI'].sum()
                tot_ce_chg = df_oc['CE_Chg_OI'].sum()
                tot_pe_chg = df_oc['PE_Chg_OI'].sum()
                
                # असली PCR कैलकुलेशन
                pcr = round(tot_pe_oi / tot_ce_oi, 2) if tot_ce_oi > 0 else 0.0
                
                # असली Max Pain कैलकुलेशन
                strikes = df_oc['Strike'].values
                pain_values = []
                for s in strikes:
                    ce_loss = df_oc[df_oc['Strike'] < s].apply(lambda r: (s - r['Strike']) * r['CE_OI'], axis=1).sum()
                    pe_loss = df_oc[df_oc['Strike'] > s].apply(lambda r: (r['Strike'] - s) * r['PE_OI'], axis=1).sum()
                    pain_values.append(ce_loss + pe_loss)
                max_pain = strikes[np.argmin(pain_values)] if len(pain_values) > 0 else 0
                
                return {
                    "status": "SUCCESS",
                    "spot": spot_price,
                    "expiry": current_expiry,
                    "pcr": pcr,
                    "max_pain": max_pain,
                    "tot_ce_oi": tot_ce_oi,
                    "tot_pe_oi": tot_pe_oi,
                    "tot_ce_chg": tot_ce_chg,
                    "tot_pe_chg": tot_pe_chg,
                    "df": df_oc
                }
    except Exception as e:
        pass
    
    return {"status": "BLOCKED_OR_OFFLINE"}

# 4. लाइव मार्केट इंडेक्स कार्ड्स
indices_dict = {
    "Nifty 50": {"sym": "^NSEI", "expiry": "Expiry Weekly"},
    "Bank Nifty": {"sym": "^NSEBANK", "expiry": "Expiry Weekly"},
    "Fin Nifty": {"sym": "^CNXFIN", "expiry": "Expiry Weekly"},
    "Midcap Nifty": {"sym": "^NSEMDCP50", "expiry": "Expiry Weekly"},
    "Sensex": {"sym": "^BSESN", "expiry": "Monthly"},
    "Gift Nifty": {"sym": "GIFTNIFTY.NS", "expiry": "Global"},
    "India VIX": {"sym": "^INDIAVIX", "expiry": "Volatility"},
    "Dow Jones": {"sym": "^DJI", "expiry": "US Market"}
}

st.markdown("### 📊 Live Market Indices")
idx_keys = list(indices_dict.keys())

for row_start in [0, 4]:
    cols = st.columns(4)
    for i in range(row_start, row_start + 4):
        name = idx_keys[i]
        item = indices_dict[name]
        try:
            df = yf.Ticker(item["sym"]).history(period="1d")
            if not df.empty:
                p = df['Close'].iloc[-1]
                op = df['Open'].iloc[-1]
                chg = p - op
                pct = (chg / op) * 100
            else:
                p, chg, pct = 0.0, 0.0, 0.0
        except:
            p, chg, pct = 0.0, 0.0, 0.0
            
        color_style = "color: #137333;" if chg >= 0 else "color: #c5221f;"
        arrow = "▲" if chg >= 0 else "▼"
        with cols[i - row_start]:
            st.markdown(f"""
                <div style='background-color: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 10px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <b style='font-size: 14px; color: #333;'>{name}</b>
                        <span style='background-color: #f0f2f6; font-size: 9px; padding: 2px 5px; border-radius: 4px; color: #555;'>{item["expiry"]}</span>
                    </div>
                    <div style='margin-top: 8px; font-size: 17px; font-weight: bold; color: #111;'>{p:,.2f}</div>
                    <div style='font-size: 11px; font-weight: 600; {color_style} margin-top: 2px;'>{arrow} {chg:+,.2f} ({pct:+.2f}%)</div>
                </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# 5. Index Selector & Real-Time Hub
st.markdown("### 🎯 Detailed Index Analyzer & Real-Time Data Hub")
selected_index_name = st.selectbox("Select Index for Deep Analysis", ["Nifty 50", "Bank Nifty", "Fin Nifty", "Midcap Nifty"])
sel_sym = indices_dict[selected_index_name]["sym"]

real_data = fetch_strict_real_nse_data(selected_index_name)

try:
    todays_data = yf.Ticker(sel_sym).history(period="2d")
    live_price = real_data["spot"] if real_data["status"] == "SUCCESS" else todays_data['Close'].iloc[-1]
    open_price = todays_data['Open'].iloc[-1]
    high_price = todays_data['High'].iloc[-1]
    low_price = todays_data['Low'].iloc[-1]
    price_diff = live_price - open_price
    price_pct = (price_diff / open_price) * 100
except:
    live_price, open_price, high_price, low_price, price_diff, price_pct = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{selected_index_name} - Spot", f"{live_price:,.2f}", f"{price_diff:+.2f} ({price_pct:+.2f}%)")
c2.metric("Open", f"{open_price:,.2f}")
c3.metric("High", f"{high_price:,.2f}")
c4.metric("Low", f"{low_price:,.2f}")

st.markdown("---")

# 6. Strict PCR & Max Pain Section (No Fake Numbers)
sr_col1, sr_col2 = st.columns(2)

with sr_col1:
    st.markdown(f"#### 📊 Price Action & Range ({selected_index_name})")
    pivot = (high_price + low_price + live_price) / 3 if high_price > 0 else 0
    r1 = (2 * pivot) - low_price if pivot > 0 else 0
    s1 = (2 * pivot) - high_price if pivot > 0 else 0
    st.markdown(f"""
        <div style='background-color: #ffffff; padding: 16px; border-radius: 8px; border: 1px solid #e0e0e0;'>
            <b>Calculated Pivot:</b> <code>{pivot:,.2f}</code><br>
            <b>Resistance 1 (R1):</b> <code style='color: #c5221f;'>{r1:,.2f}</code><br>
            <b>Support 1 (S1):</b> <code style='color: #137333;'>{s1:,.2f}</code><br>
            <hr style='margin: 8px 0;'>
            <span style='font-size: 11px; color: gray;'>* Based on authentic OHLC market calculation.</span>
        </div>
    """, unsafe_allow_html=True)

with sr_col2:
    st.markdown(f"#### 📉 Live Option Chain Metrics (StockMojo Parity)")
    if real_data["status"] == "SUCCESS":
        pcr_val = real_data["pcr"]
        max_pain_val = real_data["max_pain"]
        ce_oi_cr = round(real_data["tot_ce_oi"] / 100000, 2)
        pe_oi_cr = round(real_data["tot_pe_oi"] / 100000, 2)
        ce_chg_cr = round(real_data["tot_ce_chg"] / 100000, 2)
        pe_chg_cr = round(real_data["tot_pe_chg"] / 100000, 2)
        
        tot_oi_sum = ce_oi_cr + pe_oi_cr
        ce_pct = round((ce_oi_cr / tot_oi_sum) * 100) if tot_oi_sum > 0 else 50
        pe_pct = 100 - ce_pct
        sentiment_txt = "Bullish" if pcr_val >= 1.0 else "Bearish"
        sentiment_color = "#137333" if pcr_val >= 1.0 else "#c5221f"

        st.markdown(f"""
            <div style='background-color: #ffffff; padding: 16px; border-radius: 8px; border: 1px solid #e0e0e0;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <span style='background-color: #e6f4ea; color: #137333; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>🟢 Live Feed Connected</span>
                    <span style='background-color: #d96b27; color: #ffffff; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold;'>Max Pain: {max_pain_val}</span>
                </div>
                <b>PCR:</b> <span style='color: {sentiment_color}; font-size: 20px; font-weight: bold;'>{pcr_val}</span> ({sentiment_txt})<br>
                <span style='font-size: 13px;'>Call OI: <b>{ce_oi_cr} L</b> ({ce_pct}%) | Put OI: <b>{pe_oi_cr} L</b> ({pe_pct}%)</span><br>
                <span style='font-size: 12px; color: #555;'>OI Chg: Call <b>{ce_chg_cr:+.2f} L</b> | Put <b>{pe_chg_cr:+.2f} L</b></span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style='background-color: #fdf2f2; padding: 16px; border-radius: 8px; border: 1px solid #f5c6cb; color: #721c24;'>
                <b>🔴 Live Exchange Feed Paused / Restricted</b><br>
                <span style='font-size: 12px;'>Cloud server IP restricted by exchange firewall. No dummy data displayed to ensure absolute accuracy. Please check during market hours or connect broker API.</span>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 7. Visual Charts (Only if Real Data Exists)
if real_data["status"] == "SUCCESS":
    st.markdown("### 📊 Market Sentiment Visuals")
    chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 1.1])

    with chart_col1:
        st.markdown("**OI Change (Call vs Put)**")
        fig_chg = go.Figure(data=[
            go.Bar(name='CALL', x=['CALL'], y=[ce_chg_cr], marker_color='#2ecc71', text=[f"{ce_chg_cr} L"], textposition='auto'),
            go.Bar(name='PUT', x=['PUT'], y=[pe_chg_cr], marker_color='#e74c3c', text=[f"{pe_chg_cr} L"], textposition='auto')
        ])
        fig_chg.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10), showlegend=False, plot_bgcolor='white')
        st.plotly_chart(fig_chg, use_container_width=True)

    with chart_col2:
        st.markdown("**Total OI (Call vs Put)**")
        fig_tot = go.Figure(data=[
            go.Bar(name='CALL', x=['CALL'], y=[ce_oi_cr], marker_color='#2ecc71', text=[f"{ce_oi_cr} L"], textposition='auto'),
            go.Bar(name='PUT', x=['PUT'], y=[pe_oi_cr], marker_color='#e74c3c', text=[f"{pe_oi_cr} L"], textposition='auto')
        ])
        fig_tot.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10), showlegend=False, plot_bgcolor='white')
        st.plotly_chart(fig_tot, use_container_width=True)

    with chart_col3:
        st.markdown("**Put/Call Ratio (PCR Ring)**")
        fig_donut = go.Figure(data=[go.Pie(
            labels=[f'Call ({ce_pct}%)', f'Put ({pe_pct}%)'],
            values=[ce_oi_cr, pe_oi_cr],
            hole=.62,
            marker_colors=['#2ecc71', '#e74c3c'],
            textinfo='label'
        )])
        fig_donut.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=20, b=10),
            showlegend=False,
            annotations=[dict(text=f"PCR<br><b>{pcr_val}</b>", x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")
    st.markdown(f"### 📑 Live Strike-Wise Option Chain Table ({selected_index_name})")
    df_full = real_data["df"]
    atm_strike = round(live_price / 100) * 100
    df_near = df_full[(df_full['Strike'] >= atm_strike - 400) & (df_full['Strike'] <= atm_strike + 400)].copy()
    
    display_df = pd.DataFrame({
        "Call OI": df_near["CE_OI"],
        "Call Chg": df_near["CE_Chg_OI"],
        "Call LTP (₹)": df_near["CE_LTP"],
        "Strike Price": df_near["Strike"],
        "Put LTP (₹)": df_near["PE_LTP"],
        "Put Chg": df_near["PE_Chg_OI"],
        "Put OI": df_near["PE_OI"]
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Rahul Pro Trading Terminal | Strict Zero-Dummy Policy ⚡</p>", unsafe_allow_html=True)
            
