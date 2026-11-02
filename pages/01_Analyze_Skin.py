import base64

import requests
import streamlit as st

from app_utils import (
    API_URL,
    MODEL_NAME,
    extract_json_object,
    find_matching_products,
    prepare_image_bytes,
    save_history_record,
)


st.set_page_config(page_title="Analyze Skin", layout="wide")

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

st.title("Analyze Skin")

api_key = st.text_input("API Key", type="password", key="api_key")

uploaded_file = st.file_uploader("Upload a face photo", type=["png", "jpg", "jpeg"])
camera_image = st.camera_input("Or take a photo")

if st.button("Analyze Skin"):
    if not api_key:
        st.warning("Please enter your API key.")
        st.stop()

    image_bytes, image_type = prepare_image_bytes(camera_image, uploaded_file)
    if image_bytes is None:
        st.warning("Please upload or capture a face photo before analyzing.")
        st.stop()

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        "Analyze the facial skin in this image and return valid JSON only. "
        "The JSON must include these keys exactly: "
        "cleanliness_score, quality_score, estimated_age, summary, and concerns. "
        "The scores must be integers from 0 to 10 inclusive. "
        "estimated_age should be an integer estimate in years. "
        "summary should be a short paragraph. "
        "concerns should be a list of strings. "
        "Return JSON only without markdown fences."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_type};base64,{base64_image}"},
                    },
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "api-key": api_key,
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)

        if response.status_code == 401:
            details = response.text.strip() or "No response body returned."
            st.error(
                "Unauthorized: the API key is invalid, expired, or not allowed for this service. "
                f"Please verify your key and try again. Server response: {details[:500]}"
            )
            st.stop()

        response.raise_for_status()
        response_json = response.json()
        content = response_json["choices"][0]["message"]["content"]
        result = extract_json_object(content)
    except Exception as exc:
        st.error(f"Failed to analyze the image: {exc}")
        st.stop()

    cleanliness_score = int(result.get("cleanliness_score", 0))
    quality_score = int(result.get("quality_score", 0))
    estimated_age = result.get("estimated_age", 0)
    summary = result.get("summary", "No summary available.")
    concerns = result.get("concerns", [])
    recommended_products = find_matching_products(concerns).to_dict("records")

    save_history_record(
        cleanliness_score,
        quality_score,
        estimated_age,
        concerns,
        recommended_products,
    )

    st.session_state["last_analysis"] = {
        "cleanliness_score": cleanliness_score,
        "quality_score": quality_score,
        "estimated_age": estimated_age,
        "summary": summary,
        "concerns": concerns,
        "recommended_products": recommended_products,
    }

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Input Photo")
        st.image(image_bytes, caption="Uploaded or captured image", use_container_width=True)

    with right_col:
        st.subheader("Results")
        metric_cols = st.columns(2)
        metric_cols[0].metric("Cleanliness Score", f"{cleanliness_score}/10")
        metric_cols[1].metric("Quality Score", f"{quality_score}/10")

        st.write("Cleanliness")
        st.progress(cleanliness_score / 10)
        st.write("Quality")
        st.progress(quality_score / 10)

        st.metric("Estimated Age", estimated_age)
        st.write("Summary")
        st.write(summary)
        st.write("Concerns")
        st.write(concerns)

    st.subheader("Recommended Products")
    recommended_products_df = find_matching_products(concerns)
    if recommended_products_df.empty:
        st.info("No matching products found for the detected concerns.")
    else:
        cols = st.columns(len(recommended_products_df))
        for index, product in enumerate(recommended_products_df.to_dict("records")):
            with cols[index]:
                st.markdown(
                    f"""
                    <div style="border: 1px solid #D0D0D0; border-radius: 10px; padding: 1rem; height: 100%;">
                        <h4 style="margin-top: 0;">{product['name']}</h4>
                        <p>{product['description']}</p>
                        <p><strong>Price:</strong> {product['price']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.link_button("Buy Now", product["buy_link"])

elif "last_analysis" in st.session_state:
    last = st.session_state["last_analysis"]
    st.subheader("Last Analysis")
    st.write(last["summary"])
    st.write(last["concerns"])
