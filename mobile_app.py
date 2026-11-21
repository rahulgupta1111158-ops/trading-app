import pandas as pd
import streamlit as st


def get_option_chain_data(index_name: str) -> pd.DataFrame:
    """
    यहाँ SmartAPI से चुने हुए इंडेक्स (जैसे NIFTY, BANKNIFTY, SENSEX, FINNIFTY, MIDCPNIFTY)
    की Call (CE) और Put (PE) की असली जानकारी लाकर DataFrame में डालें।
    """
    # उदाहरण के लिए ढाँचा (जब SmartAPI से लाइव डेटा जोड़ें, तो यहाँ असली मान भरें)
    sample_rows = [
        {
            "Call OI": 0,
            "Call Chg": 0,
            "Call LTP": 0.0,
            "Strike Price": 0,
            "Put LTP": 0.0,
            "Put Chg": 0,
            "Put OI": 0,
        }
    ]
    return pd.DataFrame(sample_rows)


def render_option_chain_section(indices_list: list):
    st.subheader("Option Chain")
    selected_index = st.selectbox("Select Index", indices_list, key="oc_index_select")

    # जिन इंडेक्स की ऑप्शन चेन नहीं होती, उनके लिए साफ़ संदेश
    no_oc_indices = {"GIFT NIFTY", "DOW JONES", "INDIA VIX"}
    if selected_index.upper() in no_oc_indices:
        st.info(f"{selected_index} ke liye Option Chain uplabdh nahi hoti.")
        return

    df_oc = get_option_chain_data(selected_index)
    st.dataframe(df_oc, use_container_width=True, hide_index=True)


# इस्तेमाल:
nine_indices = [
    "BankNifty",
    "Nifty",
    "Sensex",
    "FinNifty",
    "Midcpnifty",
    "Bankex",
    "GIFT Nifty",
    "Dow Jones",
    "India VIX",
]
render_option_chain_section(nine_indices)
