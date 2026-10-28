
import streamlit as st
import yfinance as yf

# Page configuration
st.set_page_config(page_title="Rahul Trading App", layout="wide")

st.title("📊 Rahul Trading Dashboard")

# Sabhi Indices ki list jisme naye indices bhi jode gaye hain
indices = {
    "Nifty 50": "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Sensex": "^BSESN",
    "FinNifty": "NIFTY_FIN_SERVICE.NS",
    "Bankex": "^BSEBKX",
    "MidcpNifty": "NIFTY_MID_SELECT.NS",
    "Gift Nifty": "GIFTNIFTY.NS",
    "Dow Jones": "^DJI"
}

st.subheader("Live Market Indices")

# Ek ek karke sabhi indices ka data fetch karke display karna
for name, symbol in indices.items():
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if not data.empty:
            current_price = data['Close'].iloc[-1]
            prev_close = ticker.info.get('previousClose', current_price)
            change = current_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**{name}**")
            with col2:
                st.write(f"₹{current_price:,.2f}" if "^" in symbol or "NS" in symbol else f"{current_price:,.2f}")
            with col3:
                color_code = "green" if change >= 0 else "red"
                st.markdown(f"<span style='color:{color_code};'>{change:+,.2f} ({pct_change:+.2f}%)</span>", unsafe_allow_html=True)
        else:
            st.write(f"**{name}**: Data uplabdh nahi hai")
    except Exception as e:
        st.write(f"**{name}**: Error aayi hai")
