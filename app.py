import streamlit as st
from streamlit_option_menu import option_menu
from utils import check_password

# --- Import all the app modules ---
from apps import ocr, daily_occupancy, comparison, analyzer, ctrip_tools, data_analysis, briefing_generator, common_phrases

# ==============================================================================
# --- Main App Router ---
# ==============================================================================

def main():
    """
    Main function to run the Streamlit application.
    It handles page configuration, authentication, and routing to different tools.
    """
    st.set_page_config(layout="wide", page_title="金陵工具箱")

    # --- Authentication Check ---
    if not check_password():
        st.stop() # Stop execution if the password is not correct

    # --- Sidebar Navigation Menu ---
    with st.sidebar:
        st.image("https://placehold.co/250x100/000000/FFFFFF?text=Jinling+Toolbox", use_column_width=True)
        app_choice = option_menu(
            menu_title="金陵工具箱",
            options=[
                "OCR 工具", 
                "每日出租率对照表", 
                "比对平台", 
                "团队到店统计", 
                "携程对日期", 
                "携程审单", 
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
                "graph-up-arrow", 
                "blockquote-left", 
                "card-text"
            ],
            menu_icon="tools",
            default_index=0,
        )
        st.sidebar.markdown("---")
        st.sidebar.info("这是一个将多个独立工具集成在一起的模块化应用。")
        st.sidebar.markdown("V2.0 - Refactored Edition")

    # --- Route to the selected app ---
    if app_choice == "OCR 工具":
        ocr.run_ocr_app()
    elif app_choice == "每日出租率对照表":
        daily_occupancy.run_daily_occupancy_app()
    elif app_choice == "比对平台":
        comparison.run_comparison_app()
    elif app_choice == "团队到店统计":
        analyzer.run_analyzer_app()
    elif app_choice == "携程对日期":
        ctrip_tools.run_ctrip_date_comparison_app()
    elif app_choice == "携程审单":
        ctrip_tools.run_ctrip_audit_app()
    elif app_choice == "数据分析":
        data_analysis.run_data_analysis_app()
    elif app_choice == "话术生成器":
        briefing_generator.run_morning_briefing_app()
    elif app_choice == "常用话术":
        common_phrases.run_common_phrases_app()

if __name__ == "__main__":
    main()

