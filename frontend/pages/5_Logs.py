import streamlit as st
import pandas as pd
from api_client import api_get, api_post, require_login
from common import sidebar_user_box

st.set_page_config(page_title="Log Summary | F5 Portal", page_icon="📋", layout="wide")
require_login()
sidebar_user_box()

st.title("📋 Log Summary")

devices = api_get("/api/devices")
if not devices:
    st.info("Add a device first from the Devices page.")
    st.stop()

device_names = {f"{d['name']} ({d['mgmt_ip']})": d for d in devices}

c1, c2, c3 = st.columns([2, 1, 1])
selected = c1.selectbox("Device", list(device_names.keys()))
log_file = c2.selectbox("Log file", ["ltm", "gtm", "audit", "secure", "apm", "asm"])
lines = c3.number_input("Tail lines", min_value=50, max_value=5000, value=500, step=50)

if st.button("Pull & Summarize", type="primary"):
    device = device_names[selected]
    with st.spinner(f"Pulling last {lines} lines of {log_file} from {device['name']}..."):
        result = api_post("/api/logs/summary", json={
            "device_id": device["id"], "log_file": log_file, "lines": int(lines),
        })
    st.session_state["log_result"] = result

if "log_result" in st.session_state:
    result = st.session_state["log_result"]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Severity Breakdown")
        sev_df = pd.DataFrame(
            list(result["severity_counts"].items()), columns=["severity", "count"]
        ).sort_values("count", ascending=False)
        st.bar_chart(sev_df.set_index("severity"))

    with c2:
        st.subheader("Top Processes")
        proc_df = pd.DataFrame(
            list(result["process_counts"].items()), columns=["process", "count"]
        ).sort_values("count", ascending=False)
        st.bar_chart(proc_df.set_index("process"))

    st.markdown("---")
    st.subheader(f"Entries ({result['total_lines']} total, showing latest {len(result['entries'])})")

    sev_options = list(result["severity_counts"].keys())
    sev_filter = st.multiselect("Filter by severity", sev_options, default=[])

    entries = result["entries"]
    if sev_filter:
        entries = [e for e in entries if e["severity"] in sev_filter]

    df = pd.DataFrame(entries)
    if not df.empty:
        st.dataframe(df[["timestamp", "severity", "process", "message"]],
                     use_container_width=True, hide_index=True, height=500)
    else:
        st.info("No entries match the current filter.")
else:
    st.info("Select a device and click 'Pull & Summarize' to view logs.")


st.title("Designed and Developed by : Kailas Pathade_7777080508 ")
