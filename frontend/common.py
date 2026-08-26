import streamlit as st


def sidebar_user_box():
    if "token" not in st.session_state:
        st.switch_page("streamlit_app.py")

    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**User:** {st.session_state.get('username','?')}")
        st.markdown(f"**Role:** {st.session_state.get('role','?')}")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("streamlit_app.py")
