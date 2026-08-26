import streamlit as st
import pandas as pd
from api_client import api_get, api_post, api_delete, require_login, BACKEND_URL
from common import sidebar_user_box

st.set_page_config(page_title="Backups | F5 Portal", page_icon="💾", layout="wide")
require_login()
sidebar_user_box()

st.title("💾 Backup Management")

devices = api_get("/api/devices")
if not devices:
    st.info("Add a device first from the Devices page.")
    st.stop()

device_names = {f"{d['name']} ({d['mgmt_ip']})": d for d in devices}

tab_manual, tab_schedule, tab_history = st.tabs(["Manual Backup", "Auto Schedules", "History"])

# ---------------- Manual ----------------
with tab_manual:
    selected = st.selectbox("Device", list(device_names.keys()), key="manual_device")
    device = device_names[selected]

    push_remote = st.checkbox("Also push to remote backup server (SCP)")
    remote_host = remote_user = remote_password = remote_path = None
    if push_remote:
        c1, c2 = st.columns(2)
        remote_host = c1.text_input("Remote host")
        remote_user = c2.text_input("Remote username")
        c3, c4 = st.columns(2)
        remote_password = c3.text_input("Remote password", type="password")
        remote_path = c4.text_input("Remote path", value="/backups/f5")

    if st.button("Run Backup Now", type="primary"):
        with st.spinner(f"Creating UCS backup of {device['name']}... this can take a minute."):
            payload = {"device_id": device["id"], "push_remote": push_remote}
            if push_remote:
                payload.update({
                    "remote_host": remote_host, "remote_user": remote_user,
                    "remote_password": remote_password, "remote_path": remote_path,
                })
            record = api_post("/api/backups/run", json=payload)

        if record["status"] == "success":
            st.success(f"✅ Backup complete: {record['filename']} ({record['size_bytes']} bytes)")
        else:
            st.error(f"❌ Backup failed: {record['error_detail']}")

# ---------------- Schedules ----------------
with tab_schedule:
    st.subheader("Create Auto Backup Schedule")
    with st.form("new_schedule"):
        selected2 = st.selectbox("Device", list(device_names.keys()), key="sched_device")
        device2 = device_names[selected2]

        preset = st.selectbox("Frequency", ["Daily 02:00", "Weekly (Sun 02:00)", "Every 6 hours", "Custom cron"])
        cron_map = {
            "Daily 02:00": "0 2 * * *",
            "Weekly (Sun 02:00)": "0 2 * * 0",
            "Every 6 hours": "0 */6 * * *",
        }
        if preset == "Custom cron":
            cron_expr = st.text_input("Cron expression (min hour day month weekday)", "0 2 * * *")
        else:
            cron_expr = cron_map[preset]
            st.caption(f"Cron: `{cron_expr}`")

        retain = st.number_input("Retain last N backups", min_value=1, max_value=365, value=14)

        push_remote2 = st.checkbox("Push to remote backup server on each auto run")
        r_host = r_user = r_pass = r_path = None
        if push_remote2:
            c1, c2 = st.columns(2)
            r_host = c1.text_input("Remote host", key="s_host")
            r_user = c2.text_input("Remote username", key="s_user")
            c3, c4 = st.columns(2)
            r_pass = c3.text_input("Remote password", type="password", key="s_pass")
            r_path = c4.text_input("Remote path", value="/backups/f5", key="s_path")

        submitted = st.form_submit_button("Create Schedule", use_container_width=True)
        if submitted:
            api_post("/api/backups/schedules", json={
                "device_id": device2["id"], "cron_expression": cron_expr,
                "remote_push_enabled": push_remote2, "remote_host": r_host,
                "remote_user": r_user, "remote_password": r_pass, "remote_path": r_path,
                "retain_count": int(retain),
            })
            st.success("Schedule created.")
            st.rerun()

    st.markdown("---")
    st.subheader("Existing Schedules")
    schedules = api_get("/api/backups/schedules")
    if not schedules:
        st.info("No schedules configured yet.")
    else:
        id_to_name = {d["id"]: d["name"] for d in devices}
        for s in schedules:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                c1.markdown(f"**{id_to_name.get(s['device_id'], s['device_id'])}**")
                c2.code(s["cron_expression"])
                c3.markdown("✅ Enabled" if s["is_enabled"] else "⏸️ Disabled")
                c4.markdown(f"Retain: {s['retain_count']}")
                if c5.button("Delete", key=f"del_sched_{s['id']}"):
                    api_delete(f"/api/backups/schedules/{s['id']}")
                    st.rerun()

# ---------------- History ----------------
with tab_history:
    filt = st.selectbox("Filter by device", ["All"] + list(device_names.keys()), key="hist_filter")
    params = {"limit": 200}
    if filt != "All":
        params["device_id"] = device_names[filt]["id"]

    history = api_get("/api/backups/history", params=params)
    if not history:
        st.info("No backup history yet.")
    else:
        id_to_name = {d["id"]: d["name"] for d in devices}
        df = pd.DataFrame(history)
        df["device"] = df["device_id"].map(id_to_name)
        st.dataframe(
            df[["device", "filename", "trigger_type", "triggered_by", "status",
                "remote_pushed", "size_bytes", "started_at"]],
            use_container_width=True, hide_index=True, height=500,
        )

        st.markdown("### Download a backup file")
        record_options = {f"{id_to_name.get(r['device_id'])} - {r['filename']} ({r['started_at']})": r["id"]
                           for r in history if r["status"] == "success"}
        if record_options:
            sel = st.selectbox("Select backup", list(record_options.keys()))
            record_id = record_options[sel]
            st.link_button("⬇️ Download UCS file", f"{BACKEND_URL}/api/backups/{record_id}/download")
