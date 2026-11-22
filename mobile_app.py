import os
import pyotp
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from SmartApi import SmartConnect

# ---------------------------------------------------------
# 1. PAGE CONFIG (MOBILE-FIRST, CLEAN STATIC TABLES)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Rahul Pro Index Terminal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        h1, h2, h3 {
            margin-top: 0.25rem;
            margin-bottom: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Rahul Pro Index Terminal")
st.caption("Live Market & Derivatives Tracker | No Sample Data")

# Auto-refresh every 30 seconds (can be adjusted in UI if needed)
refresh_sec = st.selectbox(
    "Auto Refresh Interval",
    options=[0, 15, 30, 60],
    index=2,
    format_func=lambda x: "Off" if x == 0 else f"Every {x} sec",
)
if refresh_sec > 0:
    st_autorefresh(interval=refresh_sec * 1000, key="terminal_autorefresh")


# ---------------------------------------------------------
# 2. SECRETS / CREDENTIALS HELPER
# ---------------------------------------------------------
def get_secret(key: str, default: str = "") -> str:
    try:
        if "smartapi" in st.secrets and key in st.secrets["smartapi"]:
            val = str(st.secrets["smartapi"][key]).strip()
            if val:
                return val
    except Exception:
        pass
    try:
        if key in st.secrets:
            val = str(st.secrets[key]).strip()
            if val:
                return val
    except Exception:
        pass
    return os.getenv(key, default).strip()


# ---------------------------------------------------------
# 3. SMARTAPI LOGIN & SCRIP MASTER
# ---------------------------------------------------------
@st.cache_resource(show_spinner=False)
def init_smartapi_session():
    api_key = get_secret("ANGEL_API_KEY")
    client_code = get_secret("ANGEL_CLIENT_CODE")
    mpin = get_secret("ANGEL_MPIN")
    totp_secret = get_secret("ANGEL_TOTP_SECRET")

    if not all([api_key, client_code, mpin, totp_secret]):
        return None, "Missing SmartAPI secrets in Streamlit Secrets"

    try:
        totp = pyotp.TOTP(totp_secret).now()
        smart_api = SmartConnect(api_key=api_key)
        session = smart_api.generateSession(client_code, mpin, totp)
        if not session or not session.get("status"):
            msg = session.get("message") if isinstance(session, dict) else "Session failed"
            return None, f"SmartAPI login failed: {msg}"
        return smart_api, "Connected"
    except Exception as e:
        return None, f"SmartAPI connection error: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def load_angel_scrip_master():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
        if df.empty:
            return pd.DataFrame()
        for col in ["symbol", "name", "exch_seg", "instrumenttype", "strike", "expiry", "token"]:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame()


def classify_buildup(price_chg_pct, oi_chg_pct):
    """
    Standard price + OI buildup classification:
    - Price Up + OI Up     -> Long Buildup
    - Price Down + OI Up   -> Short Buildup
    - Price Up + OI Down   -> Short Covering
    - Price Down + OI Down -> Long Unwinding
    """
    if price_chg_pct is None or oi_chg_pct is None:
        return "N/A"
    if pd.isna(price_chg_pct) or pd.isna(oi_chg_pct):
        return "N/A"

    # If both are practically flat (0.00), treat as Neutral
    if abs(price_chg_pct) < 1e-6 and abs(oi_chg_pct) < 1e-6:
        return "Neutral"

    if price_chg_pct >= 0 and oi_chg_pct >= 0:
        return "Long Buildup"
    elif price_chg_pct < 0 and oi_chg_pct >= 0:
        return "Short Buildup"
    elif price_chg_pct >= 0 and oi_chg_pct < 0:
        return "Short Covering"
    else:
        return "Long Unwinding"


def find_index_future_token(scrip_df: pd.DataFrame, index_name: str):
    if scrip_df is None or scrip_df.empty:
        return None, None, None

    mapping = {
        "Nifty": ("NIFTY", ["NFO"]),
        "Bank Nifty": ("BANKNIFTY", ["NFO"]),
        "Sensex": ("SENSEX", ["BFO"]),
        "FinNifty": ("FINNIFTY", ["NFO"]),
        "Midcap Nifty": ("MIDCPNIFTY", ["NFO"]),
        "Bankex": ("BANKEX", ["BFO"]),
    }
    root, exchs = mapping.get(index_name, (None, []))
    if not root:
        return None, None, None

    sub = scrip_df[
        (scrip_df["name"].astype(str).str.upper() == root)
        & (scrip_df["exch_seg"].astype(str).str.upper().isin(exchs))
        & (scrip_df["instrumenttype"].astype(str).str.upper().str.contains("FUT"))
    ].copy()

    if sub.empty:
        return None, None, None

    sub["expiry_dt"] = pd.to_datetime(sub["expiry"], format="%d%b%Y", errors="coerce")
    sub = sub.dropna(subset=["expiry_dt"]).sort_values("expiry_dt")
    if sub.empty:
        return None, None, None

    nearest = sub.iloc[0]
    return str(nearest["exch_seg"]), str(nearest["token"]), str(nearest["symbol"])


def fetch_fno_indices_data(smart_api, scrip_df):
    indices = ["Nifty", "Bank Nifty", "Sensex", "FinNifty", "Midcap Nifty", "Bankex"]
    rows = []

    if smart_api is None:
        for idx in indices:
            rows.append(
                {
                    "Index": idx,
                    "Fut Symbol": "N/A",
                    "LTP": "N/A",
                    "Chg %": "N/A",
                    "OI": "N/A",
                    "OI Chg %": "N/A",
                    "Bias / Setup": "API Not Connected",
                }
            )
        return pd.DataFrame(rows)

    for idx in indices:
        exch, token, fut_sym = find_index_future_token(scrip_df, idx)
        if not token:
            rows.append(
                {
                    "Index": idx,
                    "Fut Symbol": "N/A",
                    "LTP": "N/A",
                    "Chg %": "N/A",
                    "OI": "N/A",
                    "OI Chg %": "N/A",
                    "Bias / Setup": "Token Not Found",
                }
            )
            continue

        try:
            quote = smart_api.getMarketData("FULL", {exch: [token]})
            fetched = quote.get("data", {}).get("fetched", []) if isinstance(quote, dict) else []
            if not fetched:
                rows.append(
                    {
                        "Index": idx,
                        "Fut Symbol": fut_sym,
                        "LTP": "N/A",
                        "Chg %": "N/A",
                        "OI": "N/A",
                        "OI Chg %": "N/A",
                        "Bias / Setup": "No Live Quote",
                    }
                )
                continue

            item = fetched[0]
            ltp = float(item.get("ltp")) if item.get("ltp") is not None else np.nan
            prev_close = float(item.get("close")) if item.get("close") is not None else np.nan
            oi = float(item.get("opnInterest")) if item.get("opnInterest") is not None else np.nan
            prev_oi = float(item.get("prevOpenInterest")) if item.get("prevOpenInterest") is not None else np.nan

            price_chg_pct = (
                ((ltp - prev_close) / prev_close) * 100.0
                if pd.notna(ltp) and pd.notna(prev_close) and prev_close != 0
                else np.nan
            )
            oi_chg_pct = (
                ((oi - prev_oi) / prev_oi) * 100.0
                if pd.notna(oi) and pd.notna(prev_oi) and prev_oi != 0
                else np.nan
            )

            setup = classify_buildup(price_chg_pct, oi_chg_pct)

            rows.append(
                {
                    "Index": idx,
                    "Fut Symbol": fut_sym,
                    "LTP": round(ltp, 2) if pd.notna(ltp) else "N/A",
                    "Chg %": f"{price_chg_pct:+.2f}%" if pd.notna(price_chg_pct) else "N/A",
                    "OI": f"{int(oi):,}" if pd.notna(oi) else "N/A",
                    "OI Chg %": f"{oi_chg_pct:+.2f}%" if pd.notna(oi_chg_pct) else "N/A",
                    "Bias / Setup": setup,
                }
            )
        except Exception:
            rows.append(
                {
                    "Index": idx,
                    "Fut Symbol": fut_sym or "N/A",
                    "LTP": "N/A",
                    "Chg %": "N/A",
                    "OI": "N/A",
                    "OI Chg %": "N/A",
                    "Bias / Setup": "Fetch Error",
                }
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# 4. GLOBAL / INDICATOR INDICES (STATIC, NO OPTION CHAIN)
# ---------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def fetch_global_indicators():
    # Candidate tickers; any unsupported/404 ticker safely resolves to N/A without fake values
    indicators = [
        ("GIFT Nifty", ["^NSEI"]),
        ("Dow Jones", ["^DJI"]),
        ("India VIX", ["^INDIAVIX"]),
    ]
    rows = []

    for label, candidates in indicators:
        ltp_val = np.nan
        chg_pct = np.nan
        used_ticker = "N/A"

        for tkr in candidates:
            try:
                hist = yf.Ticker(tkr).history(period="5d")
                if hist is not None and not hist.empty and "Close" in hist.columns:
                    closes = hist["Close"].dropna()
                    if len(closes) >= 1:
                        ltp_val = float(closes.iloc[-1])
                        used_ticker = tkr
                        if len(closes) >= 2 and float(closes.iloc[-2]) != 0:
                            prev_c = float(closes.iloc[-2])
                            chg_pct = ((ltp_val - prev_c) / prev_c) * 100.0
                        break
            except Exception:
                continue

        rows.append(
            {
                "Indicator": label,
                "Source Ticker": used_ticker,
                "Value": round(ltp_val, 2) if pd.notna(ltp_val) else "N/A",
                "Chg %": f"{chg_pct:+.2f}%" if pd.notna(chg_pct) else "N/A",
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# 5. RENDER UI (STATIC NON-DRILLDOWN TABLES)
# ---------------------------------------------------------
smart_api_client, status_msg = init_smartapi_session()
st.info(f"SmartAPI Status: {status_msg}")

scrip_master_df = load_angel_scrip_master()

st.subheader("6 F&O Active Indices (Derivatives & Buildup)")
fno_df = fetch_fno_indices_data(smart_api_client, scrip_master_df)
st.dataframe(fno_df, use_container_width=True, hide_index=True)

st.subheader("Global & Volatility Indicators (Static View)")
ind_df = fetch_global_indicators()
st.dataframe(ind_df, use_container_width=True, hide_index=True)
    
