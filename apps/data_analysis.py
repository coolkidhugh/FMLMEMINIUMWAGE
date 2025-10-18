import streamlit as st
import pandas as pd
import traceback
from utils import to_excel
from config import JINLING_ROOM_TYPES, YATAI_ROOM_TYPES

# ==============================================================================
# --- Data Processing Logic ---
# ==============================================================================

@st.cache_data
def process_data(_uploaded_file):
    """Loads and preprocesses the uploaded Excel file for analysis."""
    try:
        df = pd.read_excel(_uploaded_file)
        df.columns = [str(col).strip().upper() for col in df.columns]

        # Rename columns based on possible names
        rename_map = {'ROOM CATEGORY': '房类', 'ROOMS': '房数', 'ARRIVAL': '到达', 'DEPARTURE': '离开', 'RATE': '房价', 'MARKET': '市场码', 'STATUS': '状态'}
        df.rename(columns=rename_map, inplace=True)

        required_cols = ['状态', '房类', '房数', '到达', '离开', '房价', '市场码']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"上传的文件缺少以下必要的列: {', '.join(missing_cols)}。请检查文件。")
            return None, None

        # --- Data Cleaning and Transformation ---
        df['到达'] = pd.to_datetime(df['到达'].astype(str).str.split(' ').str[0], format='%y/%m/%d', errors='coerce')
        df['离开'] = pd.to_datetime(df['离开'].astype(str).str.split(' ').str[0], format='%y/%m/%d', errors='coerce')
        df['房价'] = pd.to_numeric(df['房价'], errors='coerce')
        df['房数'] = pd.to_numeric(df['房数'], errors='coerce')
        df['市场码'] = df['市场码'].astype(str).str.strip()

        df.dropna(subset=['到达', '离开', '房价', '房数', '房类'], inplace=True)
        df['房数'] = df['房数'].astype(int)

        # --- Building Assignment ---
        room_to_building = {code: "金陵楼" for code in JINLING_ROOM_TYPES}
        room_to_building.update({code: "亚太楼" for code in YATAI_ROOM_TYPES})
        df['楼层'] = df['房类'].map(room_to_building)
        df.dropna(subset=['楼层'], inplace=True) # Remove rows with unassigned buildings

        df['入住天数'] = (df['离开'] - df['到达']).dt.days
        df_for_arrivals = df.copy()

        # Create the expanded DataFrame for daily in-house analysis
        df_for_stays = df[(df['入住天数'] > 0) & (df['状态'].isin(['R', 'I']))].copy()
        if df_for_stays.empty:
            return df_for_arrivals, pd.DataFrame()

        # Repeat rows for each day of stay
        df_repeated = df_for_stays.loc[df_for_stays.index.repeat(df_for_stays['入住天数'])]
        date_offset = df_repeated.groupby(level=0).cumcount()
        df_repeated['住店日'] = df_repeated['到达'] + pd.to_timedelta(date_offset, unit='D')
        
        expanded_df = df_repeated.drop(columns=['到达', '离开', '入住天数']).reset_index(drop=True)
        return df_for_arrivals, expanded_df

    except Exception as e:
        st.error(f"处理Excel文件时出错: {e}")
        st.code(f"Traceback: {traceback.format_exc()}")
        return None, None

# ==============================================================================
# --- Streamlit UI ---
# ==============================================================================

def run_data_analysis_app():
    """Renders the Streamlit UI for the Data Analysis Dashboard."""
    st.title("金陵工具箱 - 数据分析驾驶舱")
    
    uploaded_file = st.file_uploader("上传您的Excel文件", type=["xlsx", "xls"], key="data_analysis_uploader")
    if not uploaded_file:
        st.info("请上传您的Excel文件以开始分析。")
        return

    original_df, expanded_df = process_data(uploaded_file)
    if original_df is None or original_df.empty:
        st.warning("处理后的数据为空，请检查文件内容和格式。")
        return

    st.success(f"文件 '{uploaded_file.name}' 上传并处理成功！")

    # --- Section 1: Daily Arrivals/Departures ---
    st.header("1. 每日到店/离店房数统计")
    with st.expander("点击展开或折叠", expanded=True):
        all_statuses = sorted(original_df['状态'].unique())
        
        # Arrivals
        st.subheader("到店房数统计")
        selected_arrival_statuses = st.multiselect("选择到店状态", options=all_statuses, default=['R'])
        arrival_df = original_df[original_df['状态'].isin(selected_arrival_statuses)]
        if not arrival_df.empty:
            arrival_summary = arrival_df.groupby([arrival_df['到达'].dt.date, '楼层'])['房数'].sum().unstack(fill_value=0)
            arrival_summary.index.name = "到店日期"
            st.dataframe(arrival_summary)
        
        # Departures
        st.subheader("离店房数统计")
        selected_departure_statuses = st.multiselect("选择离店状态", options=all_statuses, default=['R', 'I', 'O'])
        departure_df = original_df[original_df['状态'].isin(selected_departure_statuses)]
        if not departure_df.empty:
            departure_summary = departure_df.groupby([departure_df['离开'].dt.date, '楼层'])['房数'].sum().unstack(fill_value=0)
            departure_summary.index.name = "离店日期"
            st.dataframe(departure_summary)

    # --- Section 2: Daily In-House Price Matrix ---
    st.header("2. 每日在住房间按价格分布矩阵")
    with st.expander("点击展开或折叠", expanded=True):
        if expanded_df.empty:
            st.warning("没有状态为 'R' 或 'I' 的在住记录，无法生成价格分布矩阵。")
            return

        all_market_codes = sorted(expanded_df['市场码'].dropna().unique())
        selected_market_codes = st.multiselect("选择市场码", options=all_market_codes, default=all_market_codes)
        
        filtered_df = expanded_df[expanded_df['市场码'].isin(selected_market_codes)]
        if not filtered_df.empty:
            pivot = pd.pivot_table(
                filtered_df,
                values='房数',
                index=filtered_df['住店日'].dt.date,
                columns='楼层',
                aggfunc='sum',
                fill_value=0
            )
            pivot.index.name = '住店日期'
            st.dataframe(pivot)
        else:
            st.info("在所选市场码下没有找到在住记录。")

