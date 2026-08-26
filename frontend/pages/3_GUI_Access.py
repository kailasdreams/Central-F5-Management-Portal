import streamlit as st
from api_client import api_get, require_login
from common import sidebar_user_box

st.set_page_config(page_title="GUI Access | F5 Portal", page_icon="🌐", layout="wide")
require_login()
sidebar_user_box()

st.title("🌐 GUI Access")
st.caption(
    "F5 TMUI enforces its own frame-busting security headers, so it can't be embedded "
    "inside this portal. Below are one-click secure launch links that open the device's "
    "native TMUI in a new browser tab, using your saved inventory address."
)

devices = api_get("/api/devices")
sites = sorted(set(d["site"] for d in devices if d["site"]))
site_filter = st.selectbox("Filter by site", ["All"] + sites)

filtered = devices if site_filter == "All" else [d for d in devices if d["site"] == site_filter]

if not filtered:
    st.info("No devices found.")
else:
    for d in filtered:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            c1.markdown(f"**{d['name']}**")
            c2.markdown(f"`{d['mgmt_ip']}:{d['https_port']}` — {d['site']}")
            c3.markdown(f"HA: {d['ha_role']}")
            with c4:
                if st.button("Launch GUI ↗", key=f"launch_{d['id']}"):
                    link = api_get(f"/api/devices/{d['id']}/gui-link")
                    st.markdown(
                        f'<a href="{link["gui_url"]}" target="_blank">Click here if not redirected: {link["gui_url"]}</a>',
                        unsafe_allow_html=True,
                    )
                    st.link_button("Open TMUI", link["gui_url"])


st.title("Designed and Developed by : Kailas Pathade_7777080508 ")