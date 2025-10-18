import streamlit as st
import pandas as pd
from datetime import date, timedelta

def create_and_display_table(building_name):
    """Creates a data editor table for a specific building and returns the edited data."""
    st.subheader(f"{building_name} - 数据输入")
    
    today = date.today()
    days = [(today + timedelta(days=i)) for i in range(7)]
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    # Initial data for the table
    initial_data = {
        "日期": [d.strftime("%m/%d") for d in days],
        "星期": [weekdays_zh[d.weekday()] for d in days],
        "当日预计 (%)": [0.0] * 7,
        "当日实际 (%)": [0.0] * 7,
        "周一预计 (%)": [0.0] * 7,
        "平均房价": [0.0] * 7
    }
    input_df = pd.DataFrame(initial_data)
    
    # Display the editable data table
    edited_df = st.data_editor(
        input_df,
        key=f"editor_{building_name}",
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "当日预计 (%)": st.column_config.NumberColumn(format="%.2f"),
            "当日实际 (%)": st.column_config.NumberColumn(format="%.2f"),
            "周一预计 (%)": st.column_config.NumberColumn(format="%.2f"),
            "平均房价": st.column_config.NumberColumn("平均房价 (元)", format="%.2f"),
        }
    )
    return edited_df

def run_daily_occupancy_app():
    """Renders the Streamlit UI for the Daily Occupancy Comparison tool."""
    st.title("金陵工具箱 - 每日出租率对照表")
    st.info("计算规则: 当日预计(A), 当日实际(C), 当日增加率(C-A) | 周一预计(E), 当日实际(C), 增加百分率(C-E)")

    tabs = st.tabs(["金陵楼", "亚太楼"])
    with tabs[0]:
        jl_df = create_and_display_table("金陵楼")
    with tabs[1]:
        yt_df = create_and_display_table("亚太楼")

    st.markdown("---")
    st.header("计算结果")

    if st.button("计算并生成报告", type="primary"):
        for df, name in [(jl_df, "金陵楼"), (yt_df, "亚太楼")]:
            st.subheader(f"{name} - 计算结果")
            try:
                result_df = df.copy()
                result_df["当日增加率 (%)"] = result_df["当日实际 (%)"] - result_df["当日预计 (%)"]
                result_df["增加百分率 (%)"] = result_df["当日实际 (%)"] - result_df["周一预计 (%)"]
                
                # Define the final display columns and their order
                display_columns = [
                    "日期", "星期", 
                    "当日预计 (%)", "当日实际 (%)", "当日增加率 (%)", 
                    "周一预计 (%)", "增加百分率 (%)", "平均房价"
                ]
                result_df_display = result_df[display_columns]

                # Format the output for better readability
                st.dataframe(result_df_display.style.format({
                    "当日预计 (%)": "{:.2f}%",
                    "当日实际 (%)": "{:.2f}%",
                    "当日增加率 (%)": "{:+.2f}%",
                    "周一预计 (%)": "{:.2f}%",
                    "增加百分率 (%)": "{:+.2f}%",
                    "平均房价": "{:.2f}"
                }))
                
                st.markdown("---")
                st.subheader(f"{name} - 本周总计")
                
                total_actual = result_df['当日实际 (%)'].sum()
                total_forecast = result_df['当日预计 (%)'].sum()
                total_increase = total_actual - total_forecast
                
                col1, col2, col3 = st.columns(3)
                col1.metric("本周实际 (加总)", f"{total_actual:.2f}%")
                col2.metric("本周预测 (加总)", f"{total_forecast:.2f}%")
                col3.metric("实际增加 (点数)", f"{total_increase:+.2f}")

            except (ValueError, KeyError) as e:
                st.error(f"在计算 {name} 数据时发生错误: {e}")

