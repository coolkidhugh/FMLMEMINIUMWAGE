import streamlit as st
from streamlit_option_menu import option_menu
from utils import check_password, generate_ticker_html # 温柔地从 utils 导入函数~
from config import APP_NAME, APP_VERSION # 从 config 导入全局配置~

# --- 嘻嘻，把所有小工具的运行函数都请出来~ ---
from apps.ocr import run_ocr_app
from apps.daily_occupancy import run_daily_occupancy_app
from apps.comparison import run_comparison_app
from apps.analyzer import run_analyzer_app
from apps.ctrip_tools import run_ctrip_date_comparison_app, run_ctrip_audit_app
from apps.data_analysis import run_data_analysis_app
from apps.briefing_generator import run_morning_briefing_app
from apps.common_phrases import run_common_phrases_app
from apps.promo_checker import run_promo_checker_app # 连住权益的小帮手~
from apps.meituan_checker import run_meituan_checker_app # 美团的小可爱~
from apps.upgrade_finder import run_upgrade_finder_app # 备注查找小能手~
from apps.astro_matcher import run_astro_matcher_app # 温柔的星座情缘小助手来啦！💖

# --- 主应用的小入口~ ---
st.set_page_config(layout="wide", page_title=f"{APP_NAME} v{APP_VERSION}")

# --- 温柔的滚动条~ ---
ticker_text_default = f"{APP_NAME} v{APP_VERSION} - 努力更新中哦... | 今日天气: 暖洋洋☀️ | 值班经理: 温柔的小王 | 联系方式: 138xxxx8888"
ticker_text = st.sidebar.text_input("滚动栏想要说的话~", ticker_text_default)

if check_password():
    # 登录成功才会显示滚动条哦~
    st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)

    with st.sidebar:
        st.sidebar.markdown(f"### {APP_NAME}")
        st.sidebar.caption(f"版本: {APP_VERSION}")
        app_choice = option_menu(
            menu_title=None, # 把标题藏起来，用上面的 Markdown 更好看~
            options=[
                "OCR 小助手", # 改个更可爱的名字~
                "每日入住率小看板",
                "智能比对小管家",
                "团队入住统计",
                "携程日期核对",
                "携程订单审核",
                "美团邮件助手",
                "连住权益查询",
                "备注关键字查找",
                "星座情缘小助手", # 把它放在这里啦！💖
                "数据分析小天地",
                "晨间寄语生成器", # 改个温柔的名字~
                "常用短语小本本"  # 改个可爱的名字~
                ],
            icons=[
                "camera-reels",      # OCR
                "calendar-heart",    # 每日入住率
                "columns-gap",       # 比对平台
                "people",            # 团队统计
                "calendar-check",    # 携程对日期
                "person-check",      # 携程审单
                "envelope-open-heart",# 美团邮件
                "award",             # 连住权益
                "search-heart",      # 备注查找
                "stars",             # 星座情缘
                "graph-up-arrow",    # 数据分析
                "chat-quote",        # 晨间寄语
                "card-list"          # 常用短语
                ],
            menu_icon="gem", # 用宝石图标~💎
            default_index=9, # 默认显示新加的这个哦~
        )

        st.sidebar.markdown("---")
        st.sidebar.info("这是一个集成了好多好多温柔小工具的应用呢~")

    # --- 根据您的选择，打开对应的小工具哦~ ---
    if app_choice == "OCR 小助手": run_ocr_app()
    elif app_choice == "每日入住率小看板": run_daily_occupancy_app()
    elif app_choice == "智能比对小管家": run_comparison_app()
    elif app_choice == "团队入住统计": run_analyzer_app()
    elif app_choice == "携程日期核对": run_ctrip_date_comparison_app()
    elif app_choice == "携程订单审核": run_ctrip_audit_app()
    elif app_choice == "美团邮件助手": run_meituan_checker_app()
    elif app_choice == "连住权益查询": run_promo_checker_app()
    elif app_choice == "备注关键字查找": run_upgrade_finder_app()
    elif app_choice == "星座情缘小助手": run_astro_matcher_app() # 嘻嘻，运行新加的小助手！
    elif app_choice == "数据分析小天地": run_data_analysis_app()
    elif app_choice == "晨间寄语生成器": run_morning_briefing_app()
    elif app_choice == "常用短语小本本": run_common_phrases_app()
else:
    st.info("请输入用户名和密码才能进入哦~")

