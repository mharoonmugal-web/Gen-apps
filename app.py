import streamlit as st
import requests
import pandas as pd
import plotly.express as px
st.set_page_config(page_title="Market Explorer V1", layout="centered")

st.title("🌍 Market Explorer V1 (Simple Live Dashboard)")

# ---------------- USER INPUT ----------------
city = st.text_input("Enter City", "Lahore")

option = st.selectbox(
    "Select Data Type",
    ["Weather", "Forex (USD/PKR)", "Gold Price (USD)"]
)

# ---------------- WEATHER ----------------
if option == "Weather":
    if st.button("Get Weather"):
        API_KEY = "YOUR_OPENWEATHER_KEY"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

        res = requests.get(url).json()

        if "main" in res:
            temp = res["main"]["temp"]
            humidity = res["main"]["humidity"]

            st.metric("Temperature (°C)", temp)
            st.metric("Humidity (%)", humidity)

            df = pd.DataFrame({
                "Day": list(range(1, 8)),
                "Temp": [temp-2, temp-1, temp, temp+1, temp+2, temp+1, temp]
            })

            fig = px.line(df, x="Day", y="Temp", title="7-Day Sample Trend")
            st.plotly_chart(fig)
        else:
            st.error("Invalid city or API issue")

# ---------------- FOREX ----------------
elif option == "Forex (USD/PKR)":
    if st.button("Get Rate"):
        url = "https://open.er-api.com/v6/latest/USD"
        data = requests.get(url).json()

        rate = data["rates"]["PKR"]

        st.metric("USD → PKR", rate)

        df = pd.DataFrame({
            "Day": list(range(1, 8)),
            "Rate": [rate-2, rate-1, rate, rate+1, rate+2, rate+1, rate]
        })

        fig = px.line(df, x="Day", y="Rate", title="Forex Trend (Sample)")
        st.plotly_chart(fig)

# ---------------- GOLD ----------------
elif option == "Gold Price (USD)":
    if st.button("Get Gold Price"):
        url = "https://www.goldapi.io/api/XAU/USD"
        headers = {"x-access-token": "YOUR_GOLD_API_KEY"}

        res = requests.get(url, headers=headers).json()

        price = res.get("price", None)

        if price:
            st.metric("Gold Price (USD/Oz)", price)

            df = pd.DataFrame({
                "Day": list(range(1, 8)),
                "Price": [price-10, price-5, price, price+5, price+10, price+7, price]
            })

            fig = px.line(df, x="Day", y="Price", title="Gold Trend (Sample)")
            st.plotly_chart(fig)
        else:
            st.error("Gold API issue or key missing")
