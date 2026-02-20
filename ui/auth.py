"""Authentication module for Streamlit app."""

import streamlit as st
from config import ACCESS_CODE


def check_password() -> None:
    """Check user password and set authentication state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter access code", type="password")
        if password:
            if password == ACCESS_CODE:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect code")
        st.stop()
