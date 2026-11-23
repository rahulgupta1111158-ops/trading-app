import datetime
import math
import time
import numpy as np
import pandas as pd
import pyotp
import requests
import streamlit as st
from SmartApi import SmartConnect

st.set_page_config(
    page_title="Rahul Pro Index Terminal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# 9 Indices Configuration (6 F&O + 3 Global/Volatility)
INDEX_CONFIG = [
    {
        "name": "Nifty",
        "exch": "NSE",
        "fo_exch": "NFO",
        "symbol": "Nifty 50",
        "fo_name": "NIFTY",
        "token": "99926000",
        "step": 50,
        "has_oc": True,
    },
    {
        "name": "Bank Nifty",
        "exch": "NSE",
        "fo_exch": "NFO",
        "symbol": "Nifty Bank",
        "fo_name": "BANKNIFTY",
        "token": "99926009",
        "step": 100,
        "has_oc": True,
    },
    {
        "name": "Sensex",
        "exch": "BSE",
        "fo_exch": "BFO",
        "symbol": "SENSEX",
        "fo_name": "SENSEX",
        "token": "99919000",
        "step": 100,
        "has_oc": True,
    },
    {
        "name": "FinNifty",
        "exch": "NSE",
        "fo_exch": "NFO",
        "symbol": "Nifty Fin Service",
        "fo_name": "FINNIFTY",
        "token": "99926037",
        "step": 50,
        "has_oc": True,
    },
    {
        "name": "Midcap Nifty",
        "exch": "NSE",
        "fo_exch": "NFO",
        "symbol": "NIFTY MID SELECT",
        "fo_name": "MIDCPNIFTY",
        "token": "99926074",
        "step": 25,
        "has_oc": True,
    },
    {
        "name": "Bankex",
        "exch": "BSE",
        "fo_exch": "BFO",
        "symbol": "BANKEX",
        "fo_name": "BANKEX",
        "token": "99919012",
        "step": 100,
        "has_oc": False,
    },
    {
        "name": "GIFT Nifty",
        "exch": "NSE",
        "fo_exch": None,
        "symbol": "GIFT NIFTY",
        "fo_name": None,
        "token": None,
        "step": 50,
        "has_oc": False,
    },
    {
        "name": "Dow Jones",
        "exch": "US",
        "fo_exch": None,
        "symbol": "DOW JONES",
        "fo_name": None,
        "token": None,
        "step": 100,
        "has_oc": False,
    },
    {
        "name": "India VIX",
        "exch": "NSE",
        "fo_exch": None,
        "symbol": "India VIX",
        "fo_name": None,
        "token": "99926017",
        "step": 1,
        "has_oc": False,
    },
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


@st.cache_data(ttl=3600)
def load_scrip_master():
    """Download and cache Angel One OpenAPI Scrip Master for option contract lookup."""
    try:
        resp = requests.get(SCRIP_MASTER_URL, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                return df
    except Exception:
        pass
    return pd.DataFrame()


def safe_float(val):
    try:
        if val is None or val == "":
            return None
        num = float(val)
        return None if math.isnan(num) or math.isinf(num) else num
    except Exception:
        return None


def parse_expiry_date(exp_str):
    if not exp_str:
        return None
    s = str(exp_str).strip()
    for fmt in ("%d%b%Y", "%d%b%y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.datetime.strptime(s.upper(), fmt).date()
        except ValueError:
            continue
    return None


@st.cache_data(ttl=120)
def get_prev_day_ohlc_cached(_smart_api_id, exch, token):
    """Fetch previous trading session High and Low from historical daily candle data."""
    smart_api, _ = get_smartapi_client()
    if not smart_api or not token:
        return None, None
    try:
        now = datetime.datetime.now()
        to_dt = now.strftime("%Y-%m-%d %H:%M")
        from_dt = (now - datetime.timedelta(days=12)).strftime("%Y-%m-%d %H:%M")
        params = {
            "exchange": exch,
            "symboltoken": str(token),
            "interval": "ONE_DAY",
            "fromdate": from_dt,
            "todate": to_dt,
        }
        resp = smart_api.getCandleData(params)
        candles = resp.get("data") if isinstance(resp, dict) else None
        if candles:
            today_str = now.strftime("%Y-%m-%d")
            last_candle = candles[-1]
            if len(candles) >= 2 and str(last_candle[0]).startswith(today_str):
                prev_candle = candles[-2]
            else:
                prev_candle = last_candle
            return safe_float(prev_candle[2]), safe_float(prev_candle[3])
    except Exception:
        pass
    return None, None


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


def classify_writing(call_oi_chg, put_oi_chg):
    """Identify dominant Call Writing vs Put Writing from OI changes."""
    if call_oi_chg is None and put_oi_chg is None:
        return "N/A"
    c_chg = call_oi_chg if call_oi_chg is not None else 0.0
    p_chg = put_oi_chg if put_oi_chg is not None else 0.0
    if c_chg <= 0 and p_chg <= 0:
        return "Unwinding / Neutral"
    if p_chg > c_chg and p_chg > 0:
        return "Put Writing (Support)"
    if c_chg > p_chg and c_chg > 0:
        return "Call Writing (Resistance)"
    return "Balanced / Mixed"


def calculate_max_pain(chain_df):
    """Calculate strike with minimum total intrinsic option payout at expiry."""
    if chain_df.empty:
        return "N/A"
    strikes = chain_df["Strike"].tolist()
    call_oi = pd.to_numeric(chain_df["Call OI"], errors="coerce").fillna(0).tolist()
    put_oi = pd.to_numeric(chain_df["Put OI"], errors="coerce").fillna(0).tolist()

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


def get_index_quote(smart_api, cfg, status_msg):
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

    prev_high, prev_low = get_prev_day_ohlc_cached(status_msg, cfg["exch"], cfg["token"])

    chg_pct = None
    if ltp is not None and prev_close not in (None, 0):
        chg_pct = round(((ltp - prev_close) / prev_close) * 100, 2)

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


def get_option_contracts(scrip_df, fo_exch, fo_name, spot_price, step_size, num_strikes):
    """Find nearest expiry CE and PE contracts around ATM strike from Scrip Master."""
    if scrip_df.empty or not fo_exch or not fo_name or spot_price is None:
        return None, []

    needed_cols = {"exch_seg", "name", "symbol", "token", "expiry", "strike"}
    if not needed_cols.issubset(set(scrip_df.columns)):
        return None, []

    sub = scrip_df[
        (scrip_df["exch_seg"] == fo_exch) & (scrip_df["name"] == fo_name)
    ].copy()
    if sub.empty:
        return None, []

    today = datetime.date.today()
    sub["_exp_date"] = sub["expiry"].apply(parse_expiry_date)
    sub = sub[sub["_exp_date"].notna() & (sub["_exp_date"] >= today)]
    if sub.empty:
        return None, []

    nearest_exp = min(sub["_exp_date"].unique())
    exp_df = sub[sub["_exp_date"] == nearest_exp].copy()

    # Angel One scrip master strike is often multiplied by 100; normalize to actual strike
    exp_df["_strike_raw"] = pd.to_numeric(exp_df["strike"], errors="coerce")
    atm = round(spot_price / step_size) * step_size
    target_strikes = {atm + (i * step_size) for i in range(-num_strikes, num_strikes + 1)}

    def match_strike(raw_s):
        if pd.isna(raw_s):
            return None
        if raw_s in target_strikes:
            return int(raw_s)
        if (raw_s / 100.0) in target_strikes:
            return int(raw_s / 100.0)
        return None

    exp_df["_strike_norm"] = exp_df["_strike_raw"].apply(match_strike)
    exp_df = exp_df[exp_df["_strike_norm"].notna()]

    contracts = []
    for _, r in exp_df.iterrows():
        sym = str(r["symbol"]).upper()
        opt_type = None
        if sym.endswith("CE"):
            opt_type = "CE"
        elif sym.endswith("PE"):
            opt_type = "PE"
        if opt_type:
            contracts.append(
                {
                    "strike": int(r["_strike_norm"]),
                    "type": opt_type,
                    "symbol": str(r["symbol"]),
                    "token": str(r["token"]),
                    "exch": fo_exch,
                }
            )

    return nearest_exp.strftime("%d-%b-%Y"), contracts


def fetch_option_market_data(smart_api, contracts):
    """Fetch live LTP, OI, and Volume for option contracts in safe small batches."""
    results = {}
    if not smart_api or not contracts:
        return results

    # Group tokens by exchange for FULL / QUOTE mode if available
    by_exch = {}
    for c in contracts:
        by_exch.setdefault(c["exch"], []).append(c["token"])

    for exch, tokens in by_exch.items():
        unique_tokens = list(dict.fromkeys(tokens))
        batch_size = 20
        for i in range(0, len(unique_tokens), batch_size):
            batch = unique_tokens[i : i + batch_size]
            try:
                resp = smart_api.getMarketData("FULL", {exch: batch})
                fetched = resp.get("data", {}).get("fetched", []) if isinstance(resp, dict) else []
                for item in fetched:
                    tok = str(item.get("symbolToken", ""))
                    if tok:
                        ltp_v = safe_float(item.get("ltp"))
                        oi_v = safe_float(item.get("opnInterest"))
                        prev_oi_v = safe_float(item.get("prevOpenInterest"))
                        vol_v = safe_float(item.get("tradeVolume"))
                        chg_oi_v = None
                        if oi_v is not None and prev_oi_v is not None:
                            chg_oi_v = oi_v - prev_oi_v
                        results[tok] = {
                            "ltp": ltp_v,
                            "oi": oi_v,
                            "chg_oi": chg_oi_v,
                            "vol": vol_v,
                        }
            except Exception:
                # Fallback to ltpData per token if getMarketData fails
                for tok in batch:
                    c_info = next((x for x in contracts if x["token"] == tok), None)
                    if c_info:
                        try:
                            q = smart_api.ltpData(exch, c_info["symbol"], tok)
                            if isinstance(q, dict) and q.get("status") and q.get("data"):
                                results[tok] = {
                                    "ltp": safe_float(q["data"].get("ltp")),
                                    "oi": safe_float(q["data"].get("oi")),
                                    "chg_oi": None,
                                    "vol": None,
                                }
                        except Exception:
                            pass
            time.sleep(0.15)

    return results


def build_nse_style_option_chain(spot_price, step_size, contracts, market_map, num_strikes=6):
    """Build NSE-style CALLS | Strike | PUTS option chain DataFrame with real data."""
    cols = [
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
    if spot_price is None:
        return pd.DataFrame(columns=cols)

    atm = int(round(spot_price / step_size) * step_size)
    strikes = [int(atm + (i * step_size)) for i in range(-num_strikes, num_strikes + 1)]

    lookup = {}
    for c in contracts:
        m = market_map.get(c["token"], {})
        lookup[(c["strike"], c["type"])] = m

    rows = []
    for k in strikes:
        ce = lookup.get((k, "CE"), {})
        pe = lookup.get((k, "PE"), {})
        rows.append(
            {
                "Call OI": ce.get("oi") if ce.get("oi") is not None else np.nan,
                "Call Chg OI": ce.get("chg_oi") if ce.get("chg_oi") is not None else np.nan,
                "Call Vol": ce.get("vol") if ce.get("vol") is not None else np.nan,
                "Call LTP": ce.get("ltp") if ce.get("ltp") is not None else np.nan,
                "Strike": k,
                "Put LTP": pe.get("ltp") if pe.get("ltp") is not None else np.nan,
                "Put Vol": pe.get("vol") if pe.get("vol") is not None else np.nan,
                "Put Chg OI": pe.get("chg_oi") if pe.get("chg_oi") is not None else np.nan,
                "Put OI": pe.get("oi") if pe.get("oi") is not None else np.nan,
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
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # 1. All 9 Indices Overview Table
    st.subheader("1. All 9 Indices Overview (Open, Prev High/Low, S&R, PCR, Max Pain)")
    overview_rows = [get_index_quote(smart_api, cfg, status_msg) for cfg in INDEX_CONFIG]
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

    # Fetch Option Chain early for selected index so PCR, Max Pain & Writing sync with Analyzer
    oc_df = pd.DataFrame()
    expiry_label = None
    pcr_val = "N/A"
    max_pain_val = "N/A"
    writing_status = "N/A"
    buildup_status = "N/A"

    strikes_around = 5
    if selected_cfg["has_oc"] and selected_row["_ltp_num"] is not None:
        scrip_df = load_scrip_master()
        expiry_label, contracts = get_option_contracts(
            scrip_df,
            selected_cfg["fo_exch"],
            selected_cfg["fo_name"],
            selected_row["_ltp_num"],
            selected_cfg["step"],
            num_strikes=strikes_around,
        )
        market_map = fetch_option_market_data(smart_api, contracts)
        oc_df = build_nse_style_option_chain(
            selected_row["_ltp_num"],
            selected_cfg["step"],
            contracts,
            market_map,
            num_strikes=strikes_around,
        )
        if not oc_df.empty:
            total_call_oi = oc_df["Call OI"].sum(skipna=True)
            total_put_oi = oc_df["Put OI"].sum(skipna=True)
            if total_call_oi > 0:
                pcr_val = round(total_put_oi / total_call_oi, 2)
            max_pain_val = calculate_max_pain(oc_df)

            total_call_chg_oi = oc_df["Call Chg OI"].sum(skipna=True) if oc_df["Call Chg OI"].notna().any() else None
            total_put_chg_oi = oc_df["Put Chg OI"].sum(skipna=True) if oc_df["Put Chg OI"].notna().any() else None
            writing_status = classify_writing(total_call_chg_oi, total_put_chg_oi)

            net_oi_chg_pct = None
            prev_total_oi = (total_call_oi + total_put_oi) - ((total_call_chg_oi or 0.0) + (total_put_chg_oi or 0.0))
            if (total_call_chg_oi is not None or total_put_chg_oi is not None) and prev_total_oi > 0:
                net_oi_chg_pct = (((total_call_chg_oi or 0.0) + (total_put_chg_oi or 0.0)) / prev_total_oi) * 100.0
            buildup_status = classify_buildup(selected_row["_chg_pct"], net_oi_chg_pct)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP", str(selected_row["LTP"]), str(selected_row["Chg %"]))
    m2.metric("Open Price", str(selected_row["Open"]))
    m3.metric("Prev Day High", str(selected_row["Prev High"]))
    m4.metric("Prev Day Low", str(selected_row["Prev Low"]))

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Support", str(selected_row["Support"]))
    m6.metric("Resistan
