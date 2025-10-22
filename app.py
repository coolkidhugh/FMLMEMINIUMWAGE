import streamlit as st
from streamlit_option_menu import option_menu
from config import APP_NAME, APP_VERSION # 从config导入
from utils import check_password, generate_ticker_html # 从utils导入

# --- 导入各个工具的运行函数 ---
# 操，这里一个个把你的工具函数引进来
from apps.ocr import run_ocr_app
from apps.daily_occupancy import run_daily_occupancy_app
from apps.comparison import run_comparison_app
from apps.analyzer import run_analyzer_app
from apps.ctrip_tools import run_ctrip_date_comparison_app, run_ctrip_audit_app
from apps.data_analysis import run_data_analysis_app
from apps.briefing_generator import run_morning_briefing_app
from apps.common_phrases import run_common_phrases_app
from apps.promo_checker import run_promo_checker_app
from apps.meituan_checker import run_meituan_checker_app # 操，把新加的这个引进来

# ==============================================================================
# --- 主应用逻辑 ---
# ==============================================================================
st.set_page_config(layout="wide", page_title=f"{APP_NAME} v{APP_VERSION}")

# --- 登录验证 ---
if not check_password():
    st.stop()

# --- 顶部滚动条 ---
ticker_text_default = f"欢迎使用 {APP_NAME} v{APP_VERSION}！ | 今天也要努力搬砖！ | 有问题及时反馈！"
ticker_text = st.sidebar.text_input("编辑滚动栏文字", ticker_text_default)
st.markdown(generate_ticker_html(ticker_text), unsafe_allow_html=True)


# --- 侧边栏菜单 ---
with st.sidebar:
    st.title(f"🛠️ {APP_NAME}")
    st.caption(f"版本: {APP_VERSION}")
    
    app_choice = option_menu(
        menu_title="选择工具",
        options=[
            "OCR 工具", 
            "每日出租率对照表", 
            "比对平台", 
            "团队到店统计", 
            "携程对日期", 
            "携程审单", 
            "连住权益审核", # 之前的工具
            "美团邮件审核", # 操，新加的工具放这里
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
            "gift",          # 连住权益的图标
            "envelope-paper",# 美团邮件的图标
            "graph-up-arrow", 
            "blockquote-left", 
            "card-text"
        ],
        menu_icon="tools",
        default_index=0, # 默认选中第一个工具
    )

    st.markdown("---")
    st.info("这是一个集成了多个酒店常用工具的应用。")

# --- 根据选择加载不同的应用 ---
# 操，这里根据你选的菜单，决定运行哪个工具的代码
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
elif app_choice == "美团邮件审核": # 操，路由到新工具
    run_meituan_checker_app()
elif app_choice == "数据分析":
    run_data_analysis_app()
elif app_choice == "话术生成器":
    run_morning_briefing_app()
elif app_choice == "常用话术":
    run_common_phrases_app()
else:
    # 操，万一出错了，显示个提示
    st.error("操，选了个啥玩意儿？没这个工具！")

