import streamlit as st
from streamlit_option_menu import option_menu

# --- 导入所有应用模块 ---
from apps.ocr import run_ocr_app
from apps.daily_occupancy import run_daily_occupancy_app
from apps.comparison import run_comparison_app
from apps.analyzer import run_analyzer_app
from apps.ctrip_tools import run_ctrip_date_comparison_app, run_ctrip_audit_app
from apps.data_analysis import run_data_analysis_app
from apps.briefing_generator import run_morning_briefing_app
from apps.common_phrases import run_common_phrases_app
from apps.promo_checker import run_promo_checker_app
# --- 操，把新加的工具和滚动条函数引进来 ---
from utils import check_password, generate_ticker_html
from config import APP_NAME, APP_VERSION

# --- 主应用路由器 ---
st.set_page_config(layout="wide", page_title=APP_NAME)

if check_password():
    # --- 操，滚动条和文字输入框放这里 ---
    st.sidebar.markdown("---")
    ticker_text = st.sidebar.text_input("设置滚动栏文字", value="欢迎使用金陵工具箱！ | 新增 [连住权益审核] 工具 | 有任何问题请及时反馈！")
    st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)
    
    with st.sidebar:
        app_choice = option_menu(
            menu_title=f"{APP_NAME} v{APP_VERSION}",
            options=[
                "OCR 工具", 
                "每日出租率对照表", 
                "比对平台", 
                "团队到店统计", 
                "携程对日期", 
                "携程审单",
                "连住权益审核",
                "数据分析", 
                "话术生成器", 
                "常用话术"
            ],
            icons=[
                "camera-reels-fill", 
                "calculator", 
                "kanban", 
                "clipboard-data", 
                "calendar-check", 
                "person-check-fill",
                "award-fill",
                "graph-up-arrow", 
                "blockquote-left", 
                "card-text"
            ],
            menu_icon="tools",
            default_index=0,
        )

    # 根据选择运行对应的应用
    if app_choice == "OCR 工具":
        run_ocr_app()
    elif app_choice == "每日出租率对照表":
        run_daily_occupancy_app()
    elif app_choice == "比对平台":
        run_comparison_app()
    elif app_choice == "团队到店统计":
        run_analyzer_app()
    elif app_choice == "携程对日期":
        run_ctrip_date_comparison_app()
    elif app_choice == "携程审单":
        run_ctrip_audit_app()
    elif app_choice == "连住权益审核":
        run_promo_checker_app()
    elif app_choice == "数据分析":
        run_data_analysis_app()
    elif app_choice == "话术生成器":
        run_morning_briefing_app()
    elif app_choice == "常用话术":
        run_common_phrases_app()

