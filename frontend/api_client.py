"""
Thin REST client wrapper used by every Streamlit page to talk to the FastAPI backend.
Keeps the JWT token and base URL in Streamlit session_state.
"""
import os
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_get(path, params=None):
    resp = requests.get(f"{BACKEND_URL}{path}", headers=_headers(), params=params, timeout=30)
    return _handle(resp)


def api_post(path, json=None, data=None):
    resp = requests.post(f"{BACKEND_URL}{path}", headers=_headers(), json=json, data=data, timeout=60)
    return _handle(resp)


def api_put(path, json=None):
    resp = requests.put(f"{BACKEND_URL}{path}", headers=_headers(), json=json, timeout=30)
    return _handle(resp)


def api_delete(path):
    resp = requests.delete(f"{BACKEND_URL}{path}", headers=_headers(), timeout=30)
    return _handle(resp)


def _handle(resp):
    if resp.status_code == 401:
        st.session_state.clear()
        st.error("Session expired. Please log in again.")
        st.stop()
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"API error ({resp.status_code}): {detail}")
        st.stop()
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp


def require_login():
    if "token" not in st.session_state:
        st.switch_page("streamlit_app.py")
