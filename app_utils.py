import base64
import json
import re
import sqlite3
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from PIL import Image


API_URL = "https://genai.hkbu.edu.hk/api/v1/chat/completions"
MODEL_NAME = "gpt-6-luna"
DB_PATH = Path(__file__).resolve().parent / "skin_history.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cleanliness REAL NOT NULL,
            quality REAL NOT NULL,
            age INTEGER NOT NULL,
            concerns_json TEXT NOT NULL,
            recommended_products_json TEXT NOT NULL DEFAULT '[]'
        )
        """
    )

    columns = conn.execute("PRAGMA table_info(history)").fetchall()
    has_recommended_products = any(
        col[1] == "recommended_products_json" for col in columns
    )
    if not has_recommended_products:
        conn.execute(
            "ALTER TABLE history ADD COLUMN recommended_products_json TEXT NOT NULL DEFAULT '[]'"
        )

    conn.commit()
    conn.close()


def save_history_record(cleanliness, quality, age, concerns, recommended_products=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recommended_products = recommended_products or []
    conn.execute(
        "INSERT INTO history (timestamp, cleanliness, quality, age, concerns_json, recommended_products_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            timestamp,
            float(cleanliness),
            float(quality),
            int(age),
            json.dumps(concerns),
            json.dumps(recommended_products),
        ),
    )
    conn.commit()
    conn.close()


def fetch_history_records():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, timestamp, cleanliness, quality, age, concerns_json, recommended_products_json FROM history ORDER BY id DESC"
    ).fetchall()
    conn.close()

    records = []
    for row in rows:
        records.append(
            {
                "id": row[0],
                "timestamp": row[1],
                "cleanliness": row[2],
                "quality": row[3],
                "age": row[4],
                "concerns": json.loads(row[5]),
                "recommended_products": json.loads(row[6] or "[]"),
            }
        )
    return records


def extract_json_object(raw_text):
    text = str(raw_text).strip()
    if not text:
        raise ValueError("No response content returned by the model.")

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)

    return json.loads(text)


def prepare_image_bytes(image_obj, uploaded_file=None):
    if uploaded_file is not None:
        return uploaded_file.getvalue(), uploaded_file.type or "image/jpeg"

    if image_obj is None:
        return None, "image/jpeg"

    image = Image.fromarray(image_obj)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue(), "image/jpeg"


def normalize_concern(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def get_products_df():
    return pd.read_csv("data/products.csv")


def find_matching_products(concerns):
    product_df = get_products_df()
    if product_df.empty:
        return product_df

    normalized_concerns = [
        normalize_concern(item) for item in concerns if str(item).strip()
    ]

    if not normalized_concerns:
        return product_df.iloc[0:0].copy()

    product_df = product_df.copy()
    product_df["target_concern_norm"] = product_df["target_concern"].fillna("").map(normalize_concern)

    matches = product_df[
        product_df["target_concern_norm"].apply(
            lambda target: any(
                target == concern or target in concern or concern in target
                for concern in normalized_concerns
            )
        )
    ].drop(columns=["target_concern_norm"]).reset_index(drop=True)

    return matches
