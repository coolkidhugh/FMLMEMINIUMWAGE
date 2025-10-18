import streamlit as st

# Import configurations from the central config file
from config import COMMON_PHRASES

def run_common_phrases_app():
    """Renders the Streamlit UI for the Common Phrases Copier."""
    st.title("金陵工具箱 - 常用话术")
    
    st.subheader("点击右上角复制图标即可复制话术")
    
    if COMMON_PHRASES:
        for phrase in COMMON_PHRASES:
            st.code(phrase, language=None)
    else:
        st.warning("配置文件 config.py 中未找到任何常用话术。")

