import streamlit as st
from streamlit_option_menu import option_menu
from utils import check_password, generate_ticker_html # 从 utils 导入函数
from config import APP_NAME, APP_VERSION # 从 config 导入全局配置

# --- 操，把所有工具的运行函数都他妈的导进来 ---
from apps.ocr import run_ocr_app
from apps.daily_occupancy import run_daily_occupancy_app
from apps.comparison import run_comparison_app
from apps.analyzer import run_analyzer_app
from apps.ctrip_tools import run_ctrip_date_comparison_app, run_ctrip_audit_app
from apps.data_analysis import run_data_analysis_app
from apps.briefing_generator import run_morning_briefing_app
from apps.common_phrases import run_common_phrases_app
from apps.promo_checker import run_promo_checker_app # 操，连住权益的
from apps.meituan_checker import run_meituan_checker_app # 操，美团的
from apps.upgrade_finder import run_upgrade_finder_app # 操，新加的备注查找！

# --- 主应用路由器 ---
st.set_page_config(layout="wide", page_title=f"{APP_NAME} v{APP_VERSION}")

# --- 操，滚动条 ---
ticker_text_default = f"{APP_NAME} v{APP_VERSION} - 持续更新中... | 今日天气: 晴 | 值班经理: 张三 | 联系电话: 138xxxx8888"
ticker_text = st.sidebar.text_input("滚动栏文字", ticker_text_default)
# 操，把滚动条放到 check_password 后面，登录后才显示
# st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)


if check_password():
    # 操，登录成功了再显示滚动条
    st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)

    with st.sidebar:
        st.sidebar.markdown(f"### {APP_NAME}")
        st.sidebar.caption(f"版本: {APP_VERSION}")
        app_choice = option_menu(
            menu_title=None, # 操，把标题去了，直接用上面的 Markdown
            options=[
                "OCR 工具",
                "每日出租率对照表",
                "比对平台",
                "团队到店统计",
                "携程对日期",
                "携程审单",
                "美团邮件审核", # 操，美团的加进来
                "连住权益审核", # 操，连住权益的
                "备注关键字查找", # 操，新加的放这里！名字改了
                "数据分析",
                "话术生成器",
                "常用话术"
                ],
            icons=[
                "camera-reels-fill", # OCR
                "calculator-fill",   # 每日出租率
                "kanban-fill",       # 比对平台
                "clipboard-data-fill",# 团队统计
                "calendar-check-fill",# 携程对日期
                "person-check-fill", # 携程审单
                "envelope-paper-heart-fill", # 美团邮件
                "award-fill",        # 连住权益
                "search",            # 备注查找 （操，换个搜索图标）
                "bar-chart-line-fill",# 数据分析
                "blockquote-left",   # 话术生成
                "card-text"          # 常用话术
                ],
            menu_icon="tools",
            default_index=0, # 默认显示第一个工具
        )

        st.sidebar.markdown("---")
        st.sidebar.info("这是一个集成了多个酒店运营工具的应用。")
        # st.sidebar.caption("由天才AI强力驱动") # 操，低调点

    # --- 操，根据选择调用不同的工具函数 ---
    if app_choice == "OCR 工具": run_ocr_app()
    elif app_choice == "每日出租率对照表": run_daily_occupancy_app()
    elif app_choice == "比对平台": run_comparison_app()
    elif app_choice == "团队到店统计": run_analyzer_app()
    elif app_choice == "携程对日期": run_ctrip_date_comparison_app()
    elif app_choice == "携程审单": run_ctrip_audit_app()
    elif app_choice == "美团邮件审核": run_meituan_checker_app() # 操，加上美团
    elif app_choice == "连住权益审核": run_promo_checker_app() # 操，加上连住权益
    elif app_choice == "备注关键字查找": run_upgrade_finder_app() # 操，加上新工具！
    elif app_choice == "数据分析": run_data_analysis_app()
    elif app_choice == "话术生成器": run_morning_briefing_app()
    elif app_choice == "常用话术": run_common_phrases_app()
else:
    st.info("请输入用户名和密码登录")

