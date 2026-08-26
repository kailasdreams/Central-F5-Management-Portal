import streamlit as st
import pandas as pd
from api_client import api_get, api_post, api_put, api_delete, require_login
from common import sidebar_user_box

st.set_page_config(page_title="Devices | F5 Portal", page_icon="🖥️", layout="wide")
require_login()
sidebar_user_box()

st.title("🖥️ Device Management")

tab_list, tab_add, tab_test = st.tabs(["Inventory", "Add Device", "Test Connection"])

SITES = ["DC_1", "DR_2", "DC_3"]

with tab_list:
    devices = api_get("/api/devices")
    if not devices:
        st.info("No devices registered yet.")
    else:
        df = pd.DataFrame(devices)
        st.dataframe(
            df[["id", "name", "mgmt_ip", "https_port", "ssh_port", "site", "ha_role", "is_active", "tags"]],
            use_container_width=True, hide_index=True,
        )

        st.markdown("### Edit / Remove")
        device_names = {f"{d['name']} ({d['mgmt_ip']})": d["id"] for d in devices}
        selected = st.selectbox("Select device", list(device_names.keys()))
        device_id = device_names[selected]
        device = next(d for d in devices if d["id"] == device_id)

        with st.form(f"edit_{device_id}"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name", device["name"])
            mgmt_ip = c2.text_input("Mgmt IP", device["mgmt_ip"])
            site = c3.selectbox("Site", SITES, index=SITES.index(device["site"]) if device["site"] in SITES else 0)

            c4, c5, c6 = st.columns(3)
            https_port = c4.number_input("HTTPS Port", value=device["https_port"])
            ssh_port = c5.number_input("SSH Port", value=device["ssh_port"])
            ha_role = c6.selectbox("HA Role", ["standalone", "active", "standby"],
                                    index=["standalone", "active", "standby"].index(device["ha_role"])
                                    if device["ha_role"] in ["standalone", "active", "standby"] else 0)

            tags = st.text_input("Tags", device["tags"])
            notes = st.text_area("Notes", device["notes"])
            is_active = st.checkbox("Active", device["is_active"])

            st.markdown("**Update credentials (leave blank to keep unchanged)**")
            c7, c8 = st.columns(2)
            new_username = c7.text_input("New Username", "")
            new_password = c8.text_input("New Password", "", type="password")

            colA, colB = st.columns(2)
            save = colA.form_submit_button("Save Changes", use_container_width=True)
            delete = colB.form_submit_button("🗑️ Delete Device", use_container_width=True)

            if save:
                payload = {
                    "name": name, "mgmt_ip": mgmt_ip, "site": site,
                    "https_port": int(https_port), "ssh_port": int(ssh_port),
                    "ha_role": ha_role, "tags": tags, "notes": notes, "is_active": is_active,
                }
                if new_username:
                    payload["username"] = new_username
                if new_password:
                    payload["password"] = new_password
                api_put(f"/api/devices/{device_id}", json=payload)
                st.success("Device updated.")
                st.rerun()

            if delete:
                api_delete(f"/api/devices/{device_id}")
                st.success("Device deleted.")
                st.rerun()

with tab_add:
    with st.form("add_device"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Device Name*")
        mgmt_ip = c2.text_input("Management IP*")
        site = c3.selectbox("Site*", SITES)

        c4, c5, c6 = st.columns(3)
        https_port = c4.number_input("HTTPS Port", value=443)
        ssh_port = c5.number_input("SSH Port", value=22)
        ha_role = c6.selectbox("HA Role", ["standalone", "active", "standby"])

        c7, c8 = st.columns(2)
        username = c7.text_input("Username*")
        password = c8.text_input("Password*", type="password")

        tags = st.text_input("Tags (comma separated)")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add Device", use_container_width=True)
        if submitted:
            if not (name and mgmt_ip and username and password):
                st.warning("Please fill all required (*) fields.")
            else:
                api_post("/api/devices", json={
                    "name": name, "mgmt_ip": mgmt_ip, "site": site,
                    "https_port": int(https_port), "ssh_port": int(ssh_port),
                    "ha_role": ha_role, "username": username, "password": password,
                    "tags": tags, "notes": notes,
                })
                st.success(f"Device '{name}' added.")
                st.rerun()

with tab_test:
    devices = api_get("/api/devices")
    if not devices:
        st.info("Add a device first.")
    else:
        device_names = {f"{d['name']} ({d['mgmt_ip']})": d["id"] for d in devices}
        selected = st.selectbox("Device to test", list(device_names.keys()), key="test_select")
        if st.button("Run Connection Test"):
            result = api_post(f"/api/devices/{device_names[selected]}/test")
            if result["reachable"]:
                st.success(f"✅ Reachable — {result.get('hostname')} running {result.get('version')}")
            else:
                st.error(f"❌ {result['detail']}")


st.title("Designed and Developed by : Kailas Pathade_7777080508 ")
