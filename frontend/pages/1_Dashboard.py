import streamlit as st
import pandas as pd
from api_client import api_get, require_login
from common import sidebar_user_box

st.set_page_config(page_title="Dashboard | F5 Portal", page_icon="🛡️", layout="wide")
require_login()
sidebar_user_box()

st.title("🛡️ F5 Central Management Portal")

st.caption("Dashboard")

st.title("Designed and Developed by : Kailas Pathade_7777080508 ")

devices = api_get("/api/devices")
backups = api_get("/api/backups/history", params={"limit": 10})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Devices", len(devices))
sites = sorted(set(d["site"] for d in devices if d["site"]))
col2.metric("Sites", len(sites))
active = sum(1 for d in devices if d["is_active"])
col3.metric("Active Devices", active)
recent_success = sum(1 for b in backups if b["status"] == "success")
col4.metric("Recent Backups OK", f"{recent_success}/{len(backups)}" if backups else "0/0")

st.markdown("---")

c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("Devices by Site")
    if devices:
        df = pd.DataFrame(devices)
        st.bar_chart(df.groupby("site")["id"].count())
    else:
        st.info("No devices registered yet. Add one from the Devices page.")

with c2:
    st.subheader("Recent Backups")
    if backups:
        df = pd.DataFrame(backups)[["device_id", "filename", "status", "trigger_type", "started_at"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No backup history yet.")

st.markdown("---")
st.subheader("Device Inventory")
if devices:
    df = pd.DataFrame(devices)[["name", "mgmt_ip", "site", "ha_role", "device_type", "is_active"]]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No devices yet.")

    
