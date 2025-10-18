import streamlit as st
import pandas as pd
import io
import re
import unicodedata

@st.cache_data
def to_excel(df_dict):
    """
    Converts a dictionary of pandas DataFrames into an Excel file in memory.
    This is cached to avoid re-generating the same Excel file on every rerun.
    """
    output = io.BytesIO()
    # Use the xlsxwriter engine for better formatting options in the future
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    # The getvalue() method gets the entire contents of the buffer.
    return output.getvalue()

def forensic_clean_text(text):
    """
    Performs an aggressive cleaning of a string to prepare it for comparison.
    It normalizes characters, removes zero-width spaces, and trims whitespace.
    """
    if not isinstance(text, str):
        return text
    try:
        # NFKC normalization handles full-width/half-width characters and other variants
        cleaned_text = unicodedata.normalize('NFKC', text)
        # Remove zero-width spaces and other invisible characters
        cleaned_text = re.sub(r'[\u200B-\u200D\uFEFF\s\xa0]+', '', cleaned_text)
        return cleaned_text.strip()
    except (TypeError, ValueError):
        # Return the original text if any error occurs during processing
        return text

def check_password():
    """
    Displays a login form and checks credentials against Streamlit secrets.
    Returns True if the password is correct, False otherwise.
    Manages session state for authentication status.
    """
    def password_entered():
        """Callback function to check the entered password."""
        # Retrieve credentials from secrets.toml
        app_username = st.secrets.app_credentials.get("username")
        app_password = st.secrets.app_credentials.get("password")

        # Check if the entered credentials match the stored ones
        if (st.session_state.get("username") == app_username and
                st.session_state.get("password") == app_password):
            st.session_state["password_correct"] = True
            # Clean up credentials from session state after verification
            if "password" in st.session_state:
                del st.session_state["password"]
            if "username" in st.session_state:
                del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Check if credentials are set up in secrets.toml
    if ("app_credentials" not in st.secrets or
            not st.secrets.app_credentials.get("username") or
            not st.secrets.app_credentials.get("password")):
        st.error("错误：应用的用户名或密码未在 Streamlit Secrets 中正确配置。")
        return False

    # If user is already authenticated, return True
    if st.session_state.get("password_correct", False):
        return True

    # Display the login form
    with st.form("Credentials"):
        st.text_input("用户名", key="username")
        st.text_input("密码", type="password", key="password")
        st.form_submit_button("登录", on_click=password_entered)

    # Display error message on failed login attempt
    if "password_correct" in st.session_state and not st.session_state.password_correct:
        st.error("用户名或密码不正确。")
    
    return False

