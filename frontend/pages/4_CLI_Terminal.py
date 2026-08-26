import streamlit as st
import streamlit.components.v1 as components
from api_client import api_get, api_post, require_login, BACKEND_URL
from common import sidebar_user_box

st.set_page_config(page_title="CLI Access | F5 Portal", page_icon="⌨️", layout="wide")
require_login()
sidebar_user_box()

st.title("⌨️ CLI Access")

devices = api_get("/api/devices")
if not devices:
    st.info("Add a device first from the Devices page.")
    st.stop()

device_names = {f"{d['name']} ({d['mgmt_ip']})": d for d in devices}

tab_term, tab_cmd = st.tabs(["Interactive Terminal", "Structured Command Runner"])

# ---------------- Interactive terminal ----------------
with tab_term:
    selected = st.selectbox("Device", list(device_names.keys()), key="term_device")
    device = device_names[selected]

    ws_base = BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_base}/api/cli/ws/{device['id']}?token={st.session_state['token']}"

    st.caption(f"Connecting to `{device['mgmt_ip']}:{device['ssh_port']}` as configured device credentials.")

    terminal_html = f"""
    <div id="terminal" style="width:100%; height:520px; background:#000; border-radius:6px;"></div>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/xterm/5.3.0/css/xterm.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xterm/5.3.0/xterm.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xterm/5.3.0/addons/fit/xterm-addon-fit.min.js"></script>
    <script>
        const term = new Terminal({{
            cursorBlink: true,
            fontSize: 14,
            theme: {{ background: '#000000', foreground: '#00ff00' }}
        }});
        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal'));
        fitAddon.fit();

        const socket = new WebSocket("{ws_url}");

        socket.onopen = () => {{
            term.writeln("Connecting to {device['mgmt_ip']} ...");
            socket.send(JSON.stringify({{type: "resize", cols: term.cols, rows: term.rows}}));
        }};
        socket.onmessage = (event) => {{ term.write(event.data); }};
        socket.onclose = () => {{ term.writeln("\\r\\n[Connection closed]"); }};
        socket.onerror = () => {{ term.writeln("\\r\\n[WebSocket error]"); }};

        term.onData(data => {{
            if (socket.readyState === WebSocket.OPEN) {{
                socket.send(JSON.stringify({{type: "input", data: data}}));
            }}
        }});

        window.addEventListener('resize', () => {{
            fitAddon.fit();
            if (socket.readyState === WebSocket.OPEN) {{
                socket.send(JSON.stringify({{type: "resize", cols: term.cols, rows: term.rows}}));
            }}
        }});
    </script>
    """
    components.html(terminal_html, height=550, scrolling=False)
    st.caption(
        "Session is logged to the audit trail (start/end). Closing this page or navigating away "
        "ends the SSH session on the backend."
    )

# ---------------- Structured command runner ----------------
with tab_cmd:
    selected2 = st.selectbox("Device", list(device_names.keys()), key="cmd_device")
    device2 = device_names[selected2]

    st.markdown("**Common commands**")
    common_cmds = {
        "Show version": "tmsh show sys version",
        "Show failover status": "tmsh show sys failover",
        "Show virtual servers": "tmsh show ltm virtual",
        "Show pool status": "tmsh show ltm pool",
        "Show CPU/memory": "tmsh show sys performance system",
        "Show interfaces": "tmsh show net interface",
    }
    cols = st.columns(3)
    quick_cmd = None
    for i, (label, cmd) in enumerate(common_cmds.items()):
        if cols[i % 3].button(label, use_container_width=True):
            quick_cmd = cmd

    command = st.text_input("Command", value=quick_cmd or "tmsh show sys version",
                             help="Runs over SSH on the device. Destructive shell escapes are blocked.")

    if st.button("Run Command", type="primary"):
        result = api_post("/api/cli/run", json={"device_id": device2["id"], "command": command})
        if result["success"]:
            st.success("Command executed.")
        else:
            st.error("Command failed.")
        st.code(result["output"] or "(no output)", language="bash")


st.title("Designed and Developed by : Kailas Pathade_7777080508 ")
