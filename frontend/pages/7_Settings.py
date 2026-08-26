import streamlit as st
from api_client import api_get, api_post, require_login
from common import sidebar_user_box

st.set_page_config(page_title="Settings | F5 Portal", page_icon="⚙️", layout="wide")
require_login()
sidebar_user_box()

st.title("⚙️ Settings")

if st.session_state.get("role") != "admin":
    st.warning("Only admins can access user management.")
    st.stop()

tab_users, tab_audit, tab_about = st.tabs(["User Management", "Audit Log", "About"])

with tab_users:
    st.subheader("Existing Users")
    users = api_get("/api/auth/users")
    st.table([{"username": u["username"], "role": u["role"], "active": u["is_active"]} for u in users])

    st.subheader("Create User")
    with st.form("new_user"):
        c1, c2, c3 = st.columns(3)
        username = c1.text_input("Username")
        password = c2.text_input("Password", type="password")
        role = c3.selectbox("Role", ["admin", "operator", "viewer"])
        submitted = st.form_submit_button("Create User")
        if submitted:
            if not username or not password:
                st.warning("Username and password required.")
            else:
                api_post("/api/auth/users", json={"username": username, "password": password, "role": role})
                st.success(f"User '{username}' created.")
                st.rerun()

with tab_audit:
    st.subheader("Recent Audit Events")
    logs = api_get("/api/audit", params={"limit": 300})
    if logs:
        import pandas as pd
        df = pd.DataFrame(logs)
        st.dataframe(df[["timestamp", "username", "action", "target", "detail", "success"]],
                     use_container_width=True, hide_index=True, height=550)
    else:
        st.info("No audit events yet.")

with tab_about:
    st.markdown("""
    **Roles**
    - `admin` — full access, including user management and device deletion
    - `operator` — manage devices, run backups, CLI access, view logs
    - `viewer` — read-only across dashboard, logs, and history

    **Security notes**
    - Device credentials are encrypted at rest (Fernet/AES) using `VAULT_KEY`.
    - All CLI sessions, GUI launches, backups, and device changes are written to the audit log.
    - GUI access opens the device's native TMUI in a new tab rather than embedding it, since
      F5 TMUI enforces its own frame-busting headers.
    """)
