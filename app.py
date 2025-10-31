import streamlit as st
from streamlit_option_menu import option_menu

# 操，把所有工具的启动函数都给老子引进来
from apps.ocr import run_ocr_app
from apps.analyzer import run_analyzer_app
from apps.comparison import run_comparison_app
from apps.data_analysis import run_data_analysis_app
from apps.briefing_generator import run_morning_briefing_app
from apps.common_phrases import run_common_phrases_app
from apps.daily_occupancy import run_daily_occupancy_app
from apps.ctrip_tools import run_ctrip_date_comparison_app, run_ctrip_audit_app
from apps.ctrip_pdf_checker import run_ctrip_pdf_checker_app
from apps.promo_checker import run_promo_checker_app
from apps.meituan_checker import run_meituan_checker_app
from apps.upgrade_finder import run_upgrade_finder_app
from apps.astro_matcher import run_astro_matcher_app
from apps.ocr_calculator import run_ocr_calculator_app # 操，这就是你刚要的那个牛逼新工具

# 操，把公用函数也引进来
from utils import check_password, generate_ticker_html
from config import APP_NAME, APP_VERSION

st.set_page_config(layout="wide", page_title=APP_NAME)

# --- 操，先他妈的登录 ---
if check_password():
    
    # --- 骚气的滚动条 ---
    default_ticker_text = "操！欢迎使用金陵工具箱！ | 内部使用，严禁外传！ | 有新需求就去烦那个AI！"
    ticker_text = st.sidebar.text_input("编辑滚动公告:", default_ticker_text)
    st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)

    # --- 侧边栏菜单 ---
    with st.sidebar:
        app_choice = option_menu(
            menu_title=f"{APP_NAME} v{APP_VERSION}",
            options=[
                "OCR出租率计算器", # 操，新工具放第一个，方便你点
                "OCR 工具",
                "携程PDF审单",
                "美团邮件审核",
                "携程审单",
                "携程对日期",
                "连住权益审核",
                "备注关键字查找",
                "比对平台",
                "团队到店统计",
                "数据分析",
                "每日出租率对照表",
                "话术生成器",
                "常用话术",
                "星座马屁精"
            ],
            icons=[
                "camera-fill",      # OCR出租率
                "camera-reels-fill",# OCR 工具
                "file-earmark-pdf-fill", # 携程PDF
                "envelope-paper-heart-fill", # 美团邮件
                "person-check-fill",# 携程审单
                "calendar-check",   # 携程对日期
                "award-fill",       # 连住权益
                "search-heart-fill",# 备注查找
                "kanban",           # 比对平台
                "clipboard-data",   # 团队到店
                "graph-up-arrow",   # 数据分析
                "calculator",       # 每日出租率
                "blockquote-left",  # 话术生成
                "card-text",        # 常用话术
                "stars"             # 星座马屁精
            ],
            menu_icon="tools",
            default_index=0,
        )
        st.sidebar.markdown("---")
        st.sidebar.info("这是一个牛逼的内部工具。")

    # --- 根据选择显示不同的傻逼工具 ---
    if app_choice == "OCR出租率计算器":
        run_ocr_calculator_app()
    elif app_choice == "OCR 工具":
        run_ocr_app()
    elif app_choice == "携程PDF审单":
        run_ctrip_pdf_checker_app()
    elif app_choice == "美团邮件审核":
        run_meituan_checker_app()
    elif app_choice == "携程审单":
        run_ctrip_audit_app()
    elif app_choice == "携程对日期":
        run_ctrip_date_comparison_app()
    elif app_choice == "连住权益审核":
        run_promo_checker_app()
    elif app_choice == "备注关键字查找":
        run_upgrade_finder_app()
    elif app_choice == "比对平台":
        run_comparison_app()
    elif app_choice == "团队到店统计":
        run_analyzer_app()
    elif app_choice == "数据分析":
        run_data_analysis_app()
    elif app_choice == "每日出租率对照表":
        run_daily_occupancy_app()
    elif app_choice == "话术生成器":
        run_morning_briefing_app()
    elif app_choice == "常用话术":
        run_common_phrases_app()
    elif app_choice == "星座马屁精":
        run_astro_matcher_app()

