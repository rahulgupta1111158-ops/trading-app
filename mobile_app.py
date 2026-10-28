
import streamlit as st
import yfinance as yf

st.title("Rahul Trading Dashboard")
st.write("Live Market Indices, Support-Resistance & Price Details")

# Sabhi 8 Indices ke tickers
index_options = {
    "Nifty 50": "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Sensex": "^BSESN",
    "FinNifty": "NIFTY_FIN_SERVICE.NS",
    "Bankex": "^BSEBANK",
    "MidcpNifty": "MIDCPNIFTY.NS",
    "Gift Nifty": "GIFTNIFTY.NS",
    "Dow Jones": "^DJI"
}

selected_name = st.selectbox("Index chunein:", list(index_options.keys()))
ticker_symbol = index_options[selected_name]

if st.button("Live Index Data Dekhein"):
    st.info(f"Market se live data laya ja raha hai, kripya pratiksha karein...")
    
    try:
        index_data = yf.Ticker(ticker_symbol)
        df = index_data.history(period="2d")
        
        if len(df) >= 1:
            latest_data = df.iloc[-1]
            open_price = float(latest_data['Open'])
            high = float(latest_data['High'])
            low = float(latest_data['Low'])
            close = float(latest_data['Close'])
            
            # Previous close ke liye agar data hai toh nikalenge
            prev_close = close
            if len(df) >= 2:
                prev_close = float(df.iloc[-2]['Close'])
            
            # Percentage change calculation
            change = close - prev_close
            pct_change = (change / prev_close) * 100 if prev_close != 0 else 0
            
            st.success(f"{selected_name} ka live data safaltapoorvak mil gaya!")
            
            # Live Metrics & Price Details
            st.metric(label="Live Close Price", value=f"₹{close:.2f}", delta=f"{change:.2f} ({pct_change:.2f}%)")
            
            st.markdown("---")
            st.subheader("Aaj ke Mukhya Ankadhe (Price Details)")
            st.write(f"**Open Price:** ₹{open_price:.2f}")
            st.write(f"**Aaj ka High (Ucha level):** ₹{high:.2f}")
            st.write(f"**Aaj ka Low (Nicha level):** ₹{low:.2f}")
            st.write(f"**Previous Close:** ₹{prev_close:.2f}")
            
            # Pivot Points Calculation
            pivot = (high + low + close) / 3
            r1 = (2 * pivot) - low
            s1 = (2 * pivot) - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            
            st.markdown("---")
            st.subheader("Support evam Resistance Level")
            st.write(f"**R2:** {r2:.2f}")
            st.write(f"**R1:** {r1:.2f}")
            st.write(f"**Pivot:** {pivot:.2f}")
            st.write(f"**S1:** {s1:.2f}")
            st.write(f"**S2:** {s2:.2f}")
            
            st.markdown("---")
            st.subheader("Market Signal")
            if close > pivot:
                st.success("Bullish: Market pivot point ke upar majboot hai.")
            else:
                st.error("Bearish: Market pivot point ke niche kamzor hai.")
        else:
            st.error("Data prapt nahi ho saka.")
            
    except Exception as e:
        st.error(f"Data khinchne mein samasya aayi: {e}")
