import streamlit as st
import yfinance as yf

st.title("Rahul Trading App - Index Market Analyzer")
st.write("Yeh app sirf Nifty 50, Bank Nifty aur Sensex ka live data laakar support aur resistance batata hai.")

index_options = {
    "Nifty 50": "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Sensex": "^BSESN"
}

selected_name = st.selectbox("Index chunein:", list(index_options.keys()))
ticker_symbol = index_options[selected_name]

if st.button("Live Index Data Dekhein"):
    st.info("Market se live data laya ja raha hai, kripya pratiksha karein...")
    
    try:
        index_data = yf.Ticker(ticker_symbol)
        df = index_data.history(period="2d")
        
        if len(df) >= 1:
            latest_data = df.iloc[-1]
            high = float(latest_data['High'])
            low = float(latest_data['Low'])
            close = float(latest_data['Close'])
            
            st.success(f"**{selected_name}** ka live data safaltapoorvak mil gaya!")
            
            st.metric(label="Live Close Price", value=f"₹{close:.2f}")
            st.write(f"**High:** ₹{high:.2f}")
            st.write(f"**Low:** ₹{low:.2f}")
            
            pivot = (high + low + close) / 3
            r1 = (2 * pivot) - low
            s1 = (2 * pivot) - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            
            st.markdown("---")
            st.subheader("Support एवं Resistance Level")
            st.write(f"R2: {r2:.2f}")
            st.write(f"R1: {r1:.2f}")
            st.write(f"Pivot: {pivot:.2f}")
            st.write(f"S1: {s1:.2f}")
            st.write(f"S2: {s2:.2f}")
            
            st.markdown("---")
            st.subheader("Market Signal")
            if close > pivot:
                st.success("Bullish: Market pivot point ke upar majboot hai.")
            else:
                st.error("Bearish: Market pivot point ke niche kamjor hai.")
        else:
            st.error("Data prapt nahi ho saka.")
            
    except Exception as e:
        st.error(f"Data khinchne mein samasya aayi: {e}")
