import streamlit as st

st. title("Afibuy")
st. write("Welcome to Afibuy - Liberia Global Trade Intelligence Platform")
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Afibuy", layout="wide")

st.title("🌍 Afibuy")
st.subheader("Liberia Global Trade Intelligence Platform")

menu = st.sidebar.selectbox(
    "Navigation",
    ["Dashboard", "Market Insights", "Trade Data", "About"]
)

if menu == "Dashboard":
    st.header("Dashboard")
    st.metric("Active Countries", 54)
    st.metric("Trade Opportunities", 120)

elif menu == "Market Insights":
    st.header("Market Insights")
    st.write("View trade trends and opportunities.")

elif menu == "Trade Data":
    st.header("Trade Data")
    data = pd.DataFrame({
        "Country": ["Liberia", "Morocco", "Nigeria"],
        "Trade Volume": [50000, 70000, 120000]
    })
    st.dataframe(data)

elif menu == "About":
    st.header("About Afibuy")
    st.write("Connecting African businesses through data and trade intelligence.")
