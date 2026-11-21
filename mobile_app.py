import pandas as pd
import pyotp
import streamlit as st
from SmartApi import SmartConnect

SIX_OC_INDICES = [
    "BankNifty",
    "Nifty",
    "Sensex",
    "FinNifty",
    "Midcpnifty",
    "Bankex",
]


def connect_smartapi(api_key: str, client_id: str, pin: str, totp_secret: str):
    """
    SmartAPI से असली सेशन बनाने के लिए
    """
    smart_api = SmartConnect(api_key=api_key)
    totp_code = pyotp.TOTP(totp_secret).now()
    session_data = smart_api.generateSession(client_id, pin, totp_code)

    if not session_data or not session_data.get("status"):
        raise RuntimeError(f"SmartAPI login failed: {session_data}")

    return smart_api


def fetch_contract_quote(smart_api: SmartConnect, exchange: str, trading_symbol: str, symbol_token: str):
    """
    किसी एक कॉन्ट्रैक्ट (CE या PE) का असली LTP और OI खींचने के लिए
    """
    quote_resp = smart_api.ltpData(exchange, trading_symbol, symbol_token)
    data = (quote_resp or {}).get("data") or {}
    return {
        "ltp": data.get("ltp"),
        "oi": data.get("oi"),
    }


def build_option_chain_df(smart_api: SmartConnect, contracts_rows: list) -> pd.DataFrame:
    """
    contracts_rows में हर स्ट्राइक की CE और PE की असली जानकारी (exchange, symbol, token, strike, ce_chg, pe_chg)
    होनी चाहिए ताकि SmartAPI से असली LTP और OI भरकर टेबल बनाई जा सके।
    """
    rows = []
    for item in contracts_rows:
        ce = fetch_contract_quote(
            smart_api,
            item["ce_exchange"],
            item["ce_symbol"],
            item["ce_token"],
        )
        pe = fetch_contract_quote(
            smart_api,
            item["pe_exchange"],
            item["pe_symbol"],
            item["pe_token"],
        )
        rows.append(
            {
                "Call OI": ce["oi"],
                "Call Chg": item.get("ce_chg"),
                "Call LTP": ce["ltp"],
                "Strike Price": item["strike"],
                "Put LTP": pe["ltp"],
                "Put Chg": item.get("pe_chg"),
                "Put OI": pe["oi"],
            }
        )

    columns = [
        "Call OI",
        "Call Chg",
        "Call LTP",
        "Strike Price",
        "Put LTP",
        "Put Chg",
        "Put OI",
    ]
    return pd.DataFrame(rows, columns=columns)


def render_six_indices_option_chain(smart_api: SmartConnect, contracts_by_index: dict):
    """
    6 इंडेक्स (BankNifty, Nifty, Sensex, FinNifty, Midcpnifty, Bankex) के लिए
    असली Option Chain टेबल दिखाने के लिए
    """
    st.subheader("Option Chain (6 Indices)")
    selected_index = st.selectbox("Select Index", SIX_OC_INDICES, key="six_oc_selector")

    index_contracts = contracts_by_index.get(selected_index, [])
    if not index_contracts:
        st.warning(f"{selected_index} ke liye active CE/PE contract list set nahi hai.")
        return

    df_oc = build_option_chain_df(smart_api, index_contracts)
    st.dataframe(df_oc, use_container_width=True, hide_index=True)
