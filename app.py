import streamlit as st

st.set_page_config(page_title="Skin Analysis App", layout="wide")

if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""

st.title("Skin Analysis App")
st.write("Choose a page from the sidebar to analyze skin, view trends, or shop for products.")
