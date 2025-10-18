import streamlit as st
import pandas as pd
import io

def check_password():
    """返回 True 如果用户已登录, 否则返回 False."""
    def login_form():
        with st.form("Credentials"):
            st.text_input("用户名", key="username")
            st.text_input("密码", type="password", key="password")
            st.form_submit_button("登录", on_click=password_entered)

    def password_entered():
        app_username = st.secrets.app_credentials.get("username", "")
        app_password = st.secrets.app_credentials.get("password", "")
        if st.session_state.get("username") == app_username and st.session_state.get("password") == app_password:
            st.session_state["password_correct"] = True
            if "password" in st.session_state: del st.session_state["password"]
            if "username" in st.session_state: del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "app_credentials" not in st.secrets or not st.secrets.app_credentials.get("username") or not st.secrets.app_credentials.get("password"):
        st.error("错误：应用的用户名或密码未在 Streamlit Secrets 中正确配置。")
        return False

    if st.session_state.get("password_correct", False):
        return True

    login_form()
    if "password_correct" in st.session_state and not st.session_state.password_correct:
        st.error("用户名或密码不正确。")
    return False

@st.cache_data
def to_excel(df_dict):
    """将包含多个DataFrame的字典转换为Excel文件的二进制数据。"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    processed_data = output.getvalue()
    return processed_data

def find_and_rename_columns(df, column_map):
    """
    动态查找并重命名DataFrame的列。
    首先尝试精确匹配，然后尝试模糊（包含）匹配。
    """
    missing_standard_cols = []
    for standard_name, possible_names in column_map.items():
        found_col = None
        # 第一步：尝试精确匹配
        for name in possible_names:
            if name in df.columns:
                found_col = name
                break
        # 第二步：如果精确匹配失败，尝试模糊（包含）匹配
        if not found_col:
            for name in possible_names:
                for col in df.columns:
                    if name in col:
                        found_col = col
                        break
                if found_col:
                    break
        
        if found_col:
            if found_col != standard_name:
                df.rename(columns={found_col: standard_name}, inplace=True)
        else:
            missing_standard_cols.append(standard_name)
    return missing_standard_cols

def generate_ticker_html(text):
    """生成一个横向滚动的股票代码式信息栏的HTML和CSS。"""
    html_template = f"""
    <style>
        @keyframes ticker-animation {{
            0% {{ transform: translateX(100%); }}
            100% {{ transform: translateX(-100%); }}
        }}
        .ticker-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #212529; /* 深灰色背景 */
            color: #f8f9fa; /* 亮色文字 */
            padding: 8px 0;
            overflow: hidden;
            white-space: nowrap;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            border-bottom: 2px solid #495057;
        }}
        .ticker-content {{
            display: inline-block;
            padding-left: 100%;
            animation: ticker-animation 30s linear infinite;
            font-size: 16px;
            font-family: 'Arial', sans-serif;
        }}
        .ticker-content:hover {{
            animation-play-state: paused;
        }}
        /* 为Streamlit的主体内容增加上边距，防止被滚动条遮挡 */
        .main .block-container {{
            padding-top: 60px;
        }}
    </style>
    <div class="ticker-container">
        <div class="ticker-content">{text}</div>
    </div>
    """
    return html_template

