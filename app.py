import streamlit as st
from streamlit_option_menu import option_menu

# 操，先把公用的傻逼玩意儿和配置引进来
try:
    from config import APP_NAME, APP_VERSION
    from utils import check_password, generate_ticker_html
except ImportError:
    st.error("操，没找到 config.py 或 utils.py 文件！你是不是他妈的忘了创建？")
    st.stop()

# 操，把apps文件夹里所有的工具都他妈的给老子引进来
try:
    from apps.ocr import run_ocr_app
    from apps.daily_occupancy import run_daily_occupancy_app
    from apps.comparison import run_comparison_app
    from apps.analyzer import run_analyzer_app
    from apps.ctrip_tools import run_ctrip_date_comparison_app, run_ctrip_audit_app
    from apps.ctrip_pdf_checker import run_ctrip_pdf_checker_app # 操，新加的PDF审单
    from apps.meituan_checker import run_meituan_checker_app # 操，新加的美团审单
    from apps.data_analysis import run_data_analysis_app
    from apps.briefing_generator import run_morning_briefing_app
    from apps.common_phrases import run_common_phrases_app
    from apps.promo_checker import run_promo_checker_app # 操，连住权益的
    from apps.upgrade_finder import run_upgrade_finder_app # 操，备注关键字查找
    from apps.astro_matcher import run_astro_matcher_app # 操，星座马屁精
except ImportError as e:
    st.error(f"操，导入工具模块的时候出错了！是不是apps文件夹里少了文件？错误信息：{e}")
    st.stop()


# ==============================================================================
# --- 妈的，主程序开始 ---
# ==============================================================================

# 操，先设置个页面标题
st.set_page_config(layout="wide", page_title=f"{APP_NAME} v{APP_VERSION}")

# 操，先他妈的给老子登录
if check_password():

    # --- 骚气的滚动条 ---
    ticker_text = st.sidebar.text_input("滚动公告", value="操你妈的，又开始上班了... 赶紧他妈的干活... 别忘了核对所有订单...")
    st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)
    
    # --- 侧边栏菜单 ---
    with st.sidebar:
        app_choice = option_menu(
            menu_title=APP_NAME,
            options=[
                "OCR 工具", 
                "携程审单",
                "携程PDF审单",
                "美团邮件审核",
                "连住权益审核",
                "备注关键字查找",
                "团队到店统计",
                "数据分析",
                "比对平台",
                "携程对日期",
                "每日出租率",
                "话术生成器",
                "常用话术",
                "星座马屁精"
            ],
            # 操，图标自己看着加
            icons=[
                "camera-reels-fill", 
                "person-check-fill",
                "file-earmark-pdf-fill",
                "envelope-check-fill",
                "award-fill",
                "search",
                "clipboard-data", 
                "graph-up-arrow",
                "kanban", 
                "calendar-check",
                "calculator",
                "blockquote-left", 
                "card-text",
                "stars" # 操，马屁精
            ],
            menu_icon="tools",
            default_index=0,
        )

    st.sidebar.markdown("---")
    st.sidebar.info(f"版本号: {APP_VERSION}")

    # --- 操，根据选择显示不同的工具 ---
    if app_choice == "OCR 工具":
        run_ocr_app()
    elif app_choice == "携程审单":
        run_ctrip_audit_app()
    elif app_choice == "携程PDF审单":
        run_ctrip_pdf_checker_app()
    elif app_choice == "美团邮件审核":
        run_meituan_checker_app()
    elif app_choice == "连住权益审核":
        run_promo_checker_app()
    elif app_choice == "备注关键字查找":
        run_upgrade_finder_app()
    elif app_choice == "团队到店统计":
        run_analyzer_app()
    elif app_choice == "数据分析":
        run_data_analysis_app()
    elif app_choice == "比对平台":
        run_comparison_app()
    elif app_choice == "携程对日期":
        run_ctrip_date_comparison_app()
    elif app_choice == "每日出租率":
        run_daily_occupancy_app()
    elif app_choice == "话术生成器":
        run_morning_briefing_app()
    elif app_choice == "常用话术":
        run_common_phrases_app()
    elif app_choice == "星座马屁精":
        run_astro_matcher_app()

