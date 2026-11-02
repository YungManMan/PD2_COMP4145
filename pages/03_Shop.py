import streamlit as st

from app_utils import get_products_df


st.set_page_config(page_title="Shop", layout="wide")
st.title("Shop")

products_df = get_products_df()
if products_df.empty:
    st.info("No products available in the catalog.")
    st.stop()

cols = st.columns(len(products_df))
for index, product in enumerate(products_df.to_dict("records")):
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
