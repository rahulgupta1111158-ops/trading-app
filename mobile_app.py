import datetime
import math
import time
import numpy as np
import pandas as pd
import pyotp
import streamlit as st
from SmartApi import SmartConnect

st.set_page_config(
    page_title="Rahul Pro Index Terminal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 9 Indices Configuration (6 F&O + 3 Global/Volatility)
INDEX_CONFIG = [
    {"name": "Nifty", "exch": "NSE", "symbol": "Nifty 50", "token": "99926000", "step": 50, "has_oc": True},
    {"name": "Bank Nifty", "exch": "NSE", "symbol": "Nifty Bank", "token": "99926009", "step": 100, "has_oc": True},
    {"name": "Sensex", "exch": "BSE", "symbol": "SENSEX", "token": "99919000", "step": 100, "has_oc": True},
    {"name": "FinNifty", "exch": "NSE", "symbol": "Nifty Fin Service", "token": "99926037", "step": 50, "has_oc": True},
    {"name": "Midcap Nifty", "exch": "NSE", "symbol": "NIFTY MID SELECT", "token": "99926074", "step": 25, "has_oc": True},
    {"name": "Bankex", "exch": "BSE", "symbol": "BANKEX", "token": "99919012", "step": 100, "has_oc": False},
    {"name": "GIFT Nifty", "exch": "NSE", "symbol": "GIFT NIFTY", "token": None, "step": 50, "has_oc": False},
    {"name": "Dow Jones", "exch": "US", "symbol": "DOW JONES", "token": None, "step": 100, "has_oc": False},
    {"name": "India VIX", "exch": "NSE", "symbol": "India VIX", "token": "99926017", "step": 1, "has_oc": False},
]


@st.cache_resource(ttl=300)
def get_smartapi_client():
    secrets = st.secrets
    api_key = secrets.get("ANGEL_API_KEY")
    client_code = secrets.get("ANGEL_CLIENT_CODE")
    mpin = secrets.get("ANGEL_MPIN")
    totp_secret = secrets.get("ANGEL_TOTP_SECRET")

    if not all([api_key, client_code, mpin, totp_secret]):
        return None, "Missing Secrets"

    try:
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret).now()
        session = smart_api.generateSession(client_code, mpin, totp)
        if session and session.get("status"):
            return smart_api, "Connected"
        return None, session.get("message", "Login Failed") if session else "Login Failed"
    except Exception as e:
        return None, f"Error: {e}"


def safe_float(val):
    try:
        if val is None or val == "":
            return None
        num = float(val)
        return None if math.isnan(num) or math.isinf(num) else num
    except Exception:
        return None


def get_prev_day_ohlc(smart_api, exch, token):
    """Fetch previous trading session High and Low from historical candle data."""
    if not smart_api or not token:
        return None, None
    try:
        now = datetime.datetime.now()
        to_dt = now.strftime("%Y-%m-%d %H:%M")
        from_dt = (now - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
        params = {
            "exchange": exch,
            "symboltoken": str(token),
            "interval": "ONE_DAY",
            "fromdate": from_dt,
            "todate": to_dt,
        }
        resp = smart_api.getCandleData(params)
        candles = resp.get("data") if isinstance(resp, dict) else None
        if candles and len(candles) >= 2:
            today_str = now.strftime("%Y-%m-%d")
            last_candle = candles[-1]
            prev_candle = candles[-2] if str(last_candle[0]).startswith(today_str) else last_candle
            prev_high = safe_float(prev_candle[2])
            prev_low = safe_float(prev_candle[3])
            return prev_high, prev_low
        elif candles and len(candles) == 1:
            return safe_float(candles[0][2]), safe_float(candles[0][3])
    except Exception:
        pass
    return None, None


def get_index_quote(smart_api, cfg):
    """Fetch real quote data without using mock/sample numbers."""
    ltp = None
    open_p = None
    high_p = None
    low_p = None
    prev_close = None
    oi = None

    if smart_api and cfg["token"]:
        try:
            quote = smart_api.ltpData(cfg["exch"], cfg["symbol"], str(cfg["token"]))
            if isinstance(quote, dict) and quote.get("status") and quote.get("data"):
                d = quote["data"]
                ltp = safe_float(d.get("ltp"))
                open_p = safe_float(d.get("open"))
                high_p = safe_float(d.get("high"))
                low_p = safe_float(d.get("low"))
                prev_close = safe_float(d.get("close"))
                oi = safe_float(d.get("oi"))
        except Exception:
            pass

    prev_high, prev_low = get_prev_day_ohlc(smart_api, cfg["exch"], cfg["token"])

    chg_pct = None
    if ltp is not None and prev_close not in (None, 0):
        chg_pct = round(((ltp - prev_close) / prev_close) * 100, 2)

    # Classic pivot support & resistance if high/low/close are available
    support_str = "N/A"
    resistance_str = "N/A"
    ref_h = prev_high if prev_high is not None else high_p
    ref_l = prev_low if prev_low is not None else low_p
    ref_c = prev_close if prev_close is not None else ltp
    if None not in (ref_h, ref_l, ref_c):
        pivot = (ref_h + ref_l + ref_c) / 3.0
        s1 = round((2 * pivot) - ref_h, 2)
        r1 = round((2 * pivot) - ref_l, 2)
        support_str = f"{s1}"
        resistance_str = f"{r1}"

    return {
        "Index": cfg["name"],
        "LTP": ltp if ltp is not None else "N/A",
        "Chg %": f"{chg_pct:+.2f}%" if chg_pct is not None else "N/A",
        "Open": open_p if open_p is not None else "N/A",
        "Prev High": prev_high if prev_high is not None else "N/A",
        "Prev Low": prev_low if prev_low is not None else "N/A",
        "Support": support_str,
        "Resistance": resistance_str,
        "PCR": "N/A",
        "Max Pain": "N/A",
        "Buildup": "N/A",
        "Writing": "N/A",
        "_ltp_num": ltp,
        "_chg_pct": chg_pct,
        "_oi_num": oi,
    }


def classify_buildup(price_chg_pct, oi_chg_pct):
    """Classify Long Buildup, Short Buildup, Short Covering, or Long Unwinding."""
    if price_chg_pct is None or oi_chg_pct is None:
        return "N/A"
    if abs(price_chg_pct) < 0.01 and abs(oi_chg_pct) < 0.01:
        return "Flat / Neutral"
    if price_chg_pct > 0 and oi_chg_pct > 0:
        return "Long Buildup"
    if price_chg_pct < 0 and oi_chg_pct > 0:
        return "Short Buildup"
    if price_chg_pct > 0 and oi_chg_pct < 0:
        return "Short Covering"
    if price_chg_pct < 0 and oi_chg_pct < 0:
        return "Long Unwinding"
    return "N/A"


def calculate_max_pain(chain_df):
    """Calculate strike with minimum total intrinsic option payout at expiry."""
    if chain_df.empty:
        return "N/A"
    strikes = chain_df["Strike"].tolist()
    call_oi = chain_df["Call OI"].fillna(0).tolist()
    put_oi = chain_df["Put OI"].fillna(0).tolist()

    if sum(call_oi) == 0 and sum(put_oi) == 0:
        return "N/A"

    min_pain = None
    best_strike = None

    for expiry_strike in strikes:
        total_pain = 0.0
        for s, c_oi, p_oi in zip(strikes, call_oi, put_oi):
            if expiry_strike > s:
                total_pain += (expiry_strike - s) * c_oi
            if expiry_strike < s:
                total_pain += (s - expiry_strike) * p_oi
        if min_pain is None or total_pain < min_pain:
            min_pain = total_pain
            best_strike = expiry_strike

    return best_strike if best_strike is not None else "N/A"


def build_nse_style_option_chain(spot_price, step_size, num_strikes=7):
    """
    Build NSE-style option chain structure around ATM strike.
    Uses real values when provided; leaves unavailable live fields as None ('N/A').
    """
    if spot_price is None:
        return pd.DataFrame(
            columns=[
                "Call OI",
                "Call Chg OI",
                "Call Vol",
                "Call LTP",
                "Strike",
                "Put LTP",
                "Put Vol",
                "Put Chg OI",
                "Put OI",
            ]
        )

    atm = round(spot_price / step_size) * step_size
    strikes = [atm + (i * step_size) for i in range(-num_strikes, num_strikes + 1)]

    rows = []
    for k in strikes:
        rows.append(
            {
                "Call OI": np.nan,
                "Call Chg OI": np.nan,
                "Call Vol": np.nan,
                "Call LTP": np.nan,
                "Strike": k,
                "Put LTP": np.nan,
                "Put Vol": np.nan,
                "Put Chg OI": np.nan,
                "Put OI": np.nan,
            }
        )
    return pd.DataFrame(rows)


def main():
    st.title("Rahul Pro Index Terminal")

    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        smart_api, status_msg = get_smartapi_client()
        st.caption(f"SmartAPI Status: **{status_msg}**")
    with col_s2:
        auto_refresh = st.toggle("15s Auto Refresh", value=False)
    with col_s3:
        if st.button("Refresh Now"):
            st.cache_resource.clear()
            st.rerun()

    st.divider()

    # 1. All 9 Indices Overview Table
    st.subheader("1. All 9 Indices Overview (Open, Prev High/Low, S&R, PCR, Max Pain)")
    overview_rows = [get_index_quote(smart_api, cfg) for cfg in INDEX_CONFIG]
    df_overview = pd.DataFrame(overview_rows)

    display_cols = [
        "Index",
        "LTP",
        "Chg %",
        "Open",
        "Prev High",
        "Prev Low",
        "Support",
        "Resistance",
        "PCR",
        "Max Pain",
        "Buildup",
        "Writing",
    ]
    st.dataframe(df_overview[display_cols], use_container_width=True, hide_index=True)

    st.divider()

    # 2. Detailed Single Index Analyzer
    st.subheader("2. Detailed Index Analyzer (Call/Put Writing & Buildup)")
    index_names = [c["name"] for c in INDEX_CONFIG]
    selected_name = st.selectbox("Select Index", index_names, index=0)
    selected_cfg = next(c for c in INDEX_CONFIG if c["name"] == selected_name)
    selected_row = next(r for r in overview_rows if r["Index"] == selected_name)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP", str(selected_row["LTP"]), str(selected_row["Chg %"]))
    m2.metric("Open Price", str(selected_row["Open"]))
    m3.metric("Prev Day High", str(selected_row["Prev High"]))
    m4.metric("Prev Day Low", str(selected_row["Prev Low"]))

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Support", str(selected_row["Support"]))
    m6.metric("Resistance", str(selected_row["Resistance"]))
    m7.metric("PCR", str(selected_row["PCR"]))
    m8.metric("Max Pain", str(selected_row["Max Pain"]))

    # Buildup & Call/Put Writing section
    c_w1, c_w2 = st.columns(2)
    with c_w1:
        st.markdown("**Price + OI Buildup Status**")
        st.info(
            f"Current Buildup: **{selected_row['Buildup']}**  \n"
            "Rules: Long Buildup (Price ↑, OI ↑) | Short Buildup (Price ↓, OI ↑) | "
            "Short Covering (Price ↑, OI ↓) | Long Unwinding (Price ↓, OI ↓)"
        )
    with c_w2:
        st.markdown("**Call Writing vs Put Writing**")
        st.info(
            f"Writing Bias: **{selected_row['Writing']}**  \n"
            "Call Writing (Call OI ↑ → Resistance/Supply) | "
            "Put Writing (Put OI ↑ → Support/Demand)"
        )

    st.divider()

    # 3. NSE-Style Option Chain (CALLS | Strike Price | PUTS)
    st.subheader(f"3. NSE-Style Option Chain — {selected_name}")
    if not selected_cfg["has_oc"]:
        st.warning(f"Option Chain is not applicable/available for {selected_name}.")
    else:
        strikes_around = st.slider("Strikes Around ATM (±)", min_value=3, max_value=12, value=6, step=1)
        oc_df = build_nse_style_option_chain(
            selected_row["_ltp_num"],
            selected_cfg["step"],
            num_strikes=strikes_around,
        )

        if oc_df.empty:
            st.info("Live spot price unavailable right now; option chain strikes will appear once live LTP is received.")
        else:
            total_call_oi = oc_df["Call OI"].sum(skipna=True)
            total_put_oi = oc_df["Put OI"].sum(skipna=True)
            pcr_val = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else "N/A"
            max_pain_val = calculate_max_pain(oc_df)

            oc_c1, oc_c2, oc_c3 = st.columns(3)
            oc_c1.metric("Spot LTP", str(selected_row["LTP"]))
            oc_c2.metric("Option Chain PCR", str(pcr_val))
            oc_c3.metric("Calculated Max Pain", str(max_pain_val))

            st.dataframe(oc_df.fillna("N/A"), use_container_width=True, hide_index=True)

    if auto_refresh:
        time.sleep(15)
        st.rerun()


if __name__ == "__main__":
    main()
