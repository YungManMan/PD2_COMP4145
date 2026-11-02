import pandas as pd
import streamlit as st

from app_utils import fetch_history_records


st.set_page_config(page_title="My Dashboard", layout="wide")
st.title("My Dashboard")

records = fetch_history_records()
if not records:
    st.info("No analysis history yet. Run an analysis from the Analyze Skin page.")
    st.stop()

history_df = pd.DataFrame(records)
if "timestamp" not in history_df.columns:
    st.warning("History data is missing a timestamp column.")
    st.stop()

history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
history_df = history_df.sort_values("timestamp").reset_index(drop=True)

if "cleanliness" in history_df.columns:
    history_df = history_df.rename(columns={"cleanliness": "cleanliness_score"})
if "quality" in history_df.columns:
    history_df = history_df.rename(columns={"quality": "quality_score"})

if {"cleanliness_score", "quality_score"}.issubset(history_df.columns):
    chart_df = history_df.set_index("timestamp")[["cleanliness_score", "quality_score"]]
    st.line_chart(chart_df, use_container_width=True)
else:
    st.warning("History data is missing score fields.")

st.subheader("Recent History")
st.dataframe(
    history_df[["timestamp", "cleanliness_score", "quality_score", "age", "concerns"]],
    use_container_width=True,
)
