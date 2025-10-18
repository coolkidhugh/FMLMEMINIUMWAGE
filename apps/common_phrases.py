import streamlit as st
from config import COMMON_PHRASES, APP_NAME

def run_common_phrases_app():
    """Renders the Streamlit UI for the Common Phrases tool."""
    st.title(f"{APP_NAME} - 常用话术")
    st.subheader("点击右上角复制图标即可复制话术")
    
    if COMMON_PHRASES:
        for phrase in COMMON_PHRASES:
            st.code(phrase, language=None)
    else:
        st.warning("操，常用话术列表是空的，快去 config.py 文件里给老子加上！")

