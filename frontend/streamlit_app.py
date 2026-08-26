import streamlit as st
import requests
from api_client import BACKEND_URL

st.set_page_config(page_title="F5 Central Management Portal", page_icon="🛡️", layout="wide")

if "token" in st.session_state:
    st.switch_page("pages/1_Dashboard.py")

st.markdown(
    """
    <div style="text-align:center; padding-top: 4rem;">
        <h1>🛡️ F5 Central Management Portal</h1>
        <p style="color:gray;">Multi-datacenter BIG-IP inventory, access, logs &amp; backup control</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    with st.form("login_form"):
        st.subheader("Sign in")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/api/auth/login",
                    data={"username": username, "password": password},
                    timeout=15,
                )
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot reach backend at {BACKEND_URL}. Is it running?")
                st.stop()

            if resp.status_code == 200:
                data = resp.json()
                st.session_state["token"] = data["access_token"]
                st.session_state["username"] = data["username"]
                st.session_state["role"] = data["role"]
                st.switch_page("pages/1_Dashboard.py")
            else:
                st.error("Invalid username or password.")

    st.caption("Default first-run login: **admin / admin123** — change immediately after first login.")
