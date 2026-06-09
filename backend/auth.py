import streamlit as st
from backend.database import get_setting

def check_password():
    if st.session_state.get("authenticated", False):
        return True
    password = get_setting("admin_password", "admin123")
    input_pass = st.text_input("Enter admin password", type="password")
    if st.button("Login"):
        if input_pass == password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False