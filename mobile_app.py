

import streamlit as st

# ऐप का शीर्षक
st.title("Rahul Trading App - Support & Resistance Calculator")
st.write("यहाँ आप बाजार के भाव दर्ज करके अपने समर्थन और प्रतिरोध (Support & Resistance) के स्तर ज्ञात कर सकते हैं।")

# उपयोगकर्ता से इनपुट लेना (High, Low, Close)
high = st.number_input("आज का उच्च मूल्य (High Price):", value=0.0)
low = st.number_input("आज का न्यूनतम मूल्य (Low Price):", value=0.0)
close = st.number_input("अंतिम मूल्य (Close Price):", value=0.0)

# गणना करने का बटन
if st.button("स्तर निकालें (Calculate Levels)"):
    if high > 0 and low > 0 and close > 0:
        # पिवट पॉइंट की गणना
        pivot = (high + low + close) / 3
        
        # रेजिस्टेंस और सपोर्ट की गणना
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        st.success("गणना सफल रही!")
        
        # परिणामों को प्रदर्शित करना
        st.write(f"**पिवट पॉइंट (Pivot Point):** {pivot:.2f}")
        st.write(f"**पहला रेजिस्टेंस (Resistance 1):** {r1:.2f}")
        st.write(f"**पहला सपोर्ट (Support 1):** {s1:.2f}")
        st.write(f"**दूसरा रेजिस्टेंस (Resistance 2):** {r2:.2f}")
        st.write(f"**दूसरा सपोर्ट (Support 2):** {s2:.2f}")
    else:
        st.warning("कृपया सभी मूल्य सही-सही दर्ज करें।")
