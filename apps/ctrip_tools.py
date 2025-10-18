import streamlit as st
import pandas as pd
import re
import numpy as np
from utils import find_and_rename_columns, to_excel
# 操，就是下面这行引用写错了，现在改对了
from config import (
    CTRIP_DATE_COMPARE_SYSTEM_COLS, 
    CTRIP_DATE_COMPARE_CTRIP_COLS, 
    CTRIP_AUDIT_COLUMN_MAP_CTRIP, 
    CTRIP_AUDIT_COLUMN_MAP_SYSTEM
)

# ==============================================================================
# --- APP: 携程对日期 ---
# ==============================================================================
def run_ctrip_date_comparison_app():
    st.title("金陵工具箱 - 携程对日期")
    st.markdown("""
    此工具用于比对 **系统订单 (System Order)** 和 **携程订单 (Ctrip Order)**。
    1.  请分别上传两个对应的 Excel 文件。
    2.  工具会自动识别并统一两种不同的日期格式 (`YYMMDD` 和 `YYYY/MM/DD`)。
    3.  点击“开始比对”，下方将显示结果摘要，并提供详细报告下载。
    """)

    col1, col2 = st.columns(2)
    with col1:
        system_file_uploaded = st.file_uploader("上传您的 System Order (.xlsx)", type=["xlsx"], key="system_uploader")
    with col2:
        ctrip_file_uploaded = st.file_uploader("上传您的 Ctrip Order (.xlsx)", type=["xlsx"], key="ctrip_uploader")

    if st.button("开始比对", type="primary", disabled=(not system_file_uploaded or not ctrip_file_uploaded)):
        
        @st.cache_data
        def perform_comparison(system_file, ctrip_file):
            
            def clean_data(file_buffer, cols_map, date_format=None):
                try:
                    df = pd.read_excel(file_buffer)
                except Exception as e:
                    st.error(f"读取文件失败: {e}")
                    return None

                required_cols = list(cols_map.values())
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    st.error(f"上传的文件中缺少以下必需的列: {missing_cols}")
                    return None

                df_selected = df[required_cols].copy()
                df_selected.columns = ['预定号', '入住日期', '离店日期']
                
                df_selected['预定号'] = df_selected['预定号'].astype(str).str.strip().str.upper()
                
                df_selected['入住日期_str'] = df_selected['入住日期'].astype(str)
                df_selected['离店日期_str'] = df_selected['离店日期'].astype(str)

                if date_format:
                    df_selected['入住日期'] = pd.to_datetime(df_selected['入住日期_str'], format=date_format, errors='coerce').dt.date
                    df_selected['离店日期'] = pd.to_datetime(df_selected['离店日期_str'], format=date_format, errors='coerce').dt.date
                else:
                    df_selected['入住日期'] = pd.to_datetime(df_selected['入住日期_str'], errors='coerce').dt.date
                    df_selected['离店日期'] = pd.to_datetime(df_selected['离店日期_str'], errors='coerce').dt.date
                
                df_selected.dropna(subset=['预定号', '入住日期', '离店日期'], inplace=True)
                return df_selected.drop(columns=['入住日期_str', '离店日期_str'])

            with st.spinner("正在处理和比对文件..."):
                df_system = clean_data(system_file, CTRIP_DATE_COMPARE_SYSTEM_COLS, date_format='%y%m%d')
                df_ctrip = clean_data(ctrip_file, CTRIP_DATE_COMPARE_CTRIP_COLS)

                if df_system is None or df_ctrip is None:
                    return None 

                merged_df = pd.merge(
                    df_system, df_ctrip, on='预定号', how='left', suffixes=('_系统', '_Ctrip')
                )

                not_found_df = merged_df[merged_df['入住日期_Ctrip'].isnull()].copy()
                not_found_df = not_found_df[['预定号', '入住日期_系统', '离店日期_系统']]

                found_df = merged_df[merged_df['入住日期_Ctrip'].notnull()].copy()
                
                date_mismatch_df = found_df[
                    (found_df['入住日期_系统'] != found_df['入住日期_Ctrip']) |
                    (found_df['离店日期_系统'] != found_df['离店日期_Ctrip'])
                ].copy()
                date_mismatch_df = date_mismatch_df[['预定号', '入住日期_系统', '离店日期_系统', '入住日期_Ctrip', '离店日期_Ctrip']]
                
                return date_mismatch_df, not_found_df

        results = perform_comparison(system_file_uploaded, ctrip_file_uploaded)

        if results:
            date_mismatch_df, not_found_df = results
            st.success("比对完成！")
            
            st.header("结果摘要")
            col1, col2 = st.columns(2)
            col1.metric("⚠️ 日期不匹配的订单", f"{len(date_mismatch_df)} 条")
            col2.metric("ℹ️ 在携程中未找到的订单", f"{len(not_found_df)} 条")

            df_to_download = {
                "日期不匹配的订单": date_mismatch_df,
                "在Ctrip中未找到的订单": not_found_df
            }
            excel_data = to_excel(df_to_download)
            st.download_button(
                label="📥 下载详细比对报告 (.xlsx)",
                data=excel_data,
                file_name="携程日期比对报告.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.header("结果详情")
            with st.expander(f"查看 {len(date_mismatch_df)} 条日期不匹配的订单", expanded=True if not date_mismatch_df.empty else False):
                if not date_mismatch_df.empty:
                    st.dataframe(date_mismatch_df)
                else:
                    st.info("没有发现日期不匹配的订单。")
            
            with st.expander(f"查看 {len(not_found_df)} 条在携程中未找到的订单"):
                if not not_found_df.empty:
                    st.dataframe(not_found_df)
                else:
                    st.info("所有系统订单都能在携程订单中找到。")

# ==============================================================================
# --- APP: 携程审单 ---
# ==============================================================================
def run_ctrip_audit_app():
    st.title("金陵工具箱 - 携程审单")
    st.markdown("""
    此工具用于根据 **系统导出的订单** 来审核 **携程订单** 的离店时间和房号。
    1.  请分别上传 **携程订单Excel** 和 **系统订单Excel**。
    2.  工具将按以下优先级进行三轮匹配：
        - (1) **第三方预订号**
        - (2) **确认号/预订号**
        - (3) **客人姓名**
    3.  最终生成包含 `订单号`, `客人姓名`, `到达`, `离开`, `房号`, `状态` 的审核结果。
    """)

    col1, col2 = st.columns(2)
    with col1:
        ctrip_file_uploaded = st.file_uploader("上传携程订单.xlsx", type=["xlsx"], key="ctrip_audit_uploader_final")
    with col2:
        system_file_uploaded = st.file_uploader("上传系统订单.xlsx", type=["xlsx"], key="system_audit_uploader_final")

    def perform_audit_in_streamlit(ctrip_buffer, system_buffer):
        
        def clean_confirmation_number(number):
            if pd.isna(number): return None
            digits = re.findall(r'\d+', str(number))
            return ''.join(digits) if digits else None

        def clean_third_party_number(number):
            if pd.isna(number): return None
            number_str = str(number).strip()
            return re.sub(r'R\d+$', '', number_str)

        try:
            ctrip_df = pd.read_excel(ctrip_buffer, dtype={'订单号': str, '确认号': str})
            system_df = pd.read_excel(system_buffer, dtype={'预订号': str, '第三方预定号': str, '第三方预订号': str})
            
            if ctrip_df.empty:
                return "错误: 上传的携程订单文件为空或格式不正确。"
            if system_df.empty:
                return "错误: 上传的系统订单文件为空或格式不正确。"

            ctrip_df.columns = ctrip_df.columns.str.strip()
            system_df.columns = system_df.columns.str.strip()
            
            missing_ctrip_cols = find_and_rename_columns(ctrip_df, CTRIP_AUDIT_COLUMN_MAP_CTRIP)
            if missing_ctrip_cols: return f"错误: 携程订单文件中缺少必需的列: {', '.join(missing_ctrip_cols)}"
            missing_system_cols = find_and_rename_columns(system_df, CTRIP_AUDIT_COLUMN_MAP_SYSTEM)
            if missing_system_cols: return f"错误: 系统订单文件中缺少必需的列: {', '.join(missing_system_cols)}"
            
            ctrip_df['匹配的离开时间'] = np.nan
            ctrip_df['匹配的房号'] = np.nan
            ctrip_df['匹配的状态'] = np.nan
            ctrip_df['纯数字确认号'] = ctrip_df['确认号'].apply(clean_confirmation_number)
            system_df['清洗后第三方预定号'] = system_df['第三方预定号'].apply(clean_third_party_number)
            system_df['姓名'] = system_df['姓名'].astype(str).str.strip()
            ctrip_df['客人姓名'] = ctrip_df['客人姓名'].astype(str).str.strip()
            system_df['is_matched'] = False
            
            # 第1轮
            for i, ctrip_row in ctrip_df.iterrows():
                ctrip_order_id = str(ctrip_row['订单号']).strip()
                if ctrip_order_id:
                    match = system_df[(system_df['清洗后第三方预定号'] == ctrip_order_id) & (~system_df['is_matched'])]
                    if not match.empty:
                        system_idx = match.index[0]
                        ctrip_df.at[i, '匹配的离开时间'] = system_df.at[system_idx, '离开']
                        ctrip_df.at[i, '匹配的房号'] = system_df.at[system_idx, '房号']
                        ctrip_df.at[i, '匹配的状态'] = system_df.at[system_idx, '状态']
                        system_df.at[system_idx, 'is_matched'] = True
            # 第2轮
            unmatched_round1 = ctrip_df[ctrip_df['匹配的房号'].isna()]
            for i, ctrip_row in unmatched_round1.iterrows():
                conf_num = ctrip_row['纯数字确认号']
                if conf_num:
                    match = system_df[(system_df['预订号'] == conf_num) & (~system_df['is_matched'])]
                    if not match.empty:
                        system_idx = match.index[0]
                        ctrip_df.at[i, '匹配的离开时间'] = system_df.at[system_idx, '离开']
                        ctrip_df.at[i, '匹配的房号'] = system_df.at[system_idx, '房号']
                        ctrip_df.at[i, '匹配的状态'] = system_df.at[system_idx, '状态']
                        system_df.at[system_idx, 'is_matched'] = True
            # 第3轮
            unmatched_round2 = ctrip_df[ctrip_df['匹配的房号'].isna()]
            for i, ctrip_row in unmatched_round2.iterrows():
                guest_name = ctrip_row['客人姓名']
                if guest_name:
                    match = system_df[(system_df['姓名'] == guest_name) & (~system_df['is_matched'])]
                    if not match.empty:
                        system_idx = match.index[0]
                        ctrip_df.at[i, '匹配的离开时间'] = system_df.at[system_idx, '离开']
                        ctrip_df.at[i, '匹配的房号'] = system_df.at[system_idx, '房号']
                        ctrip_df.at[i, '匹配的状态'] = system_df.at[system_idx, '状态']
                        system_df.at[system_idx, 'is_matched'] = True
            
            for col in ['房号', '状态']:
                if col not in ctrip_df.columns:
                    ctrip_df[col] = np.nan
            ctrip_df['离开'] = ctrip_df['匹配的离开时间'].where(pd.notna(ctrip_df['匹配的离开时间']), ctrip_df['离开'])
            ctrip_df['房号'] = ctrip_df['匹配的房号'].where(pd.notna(ctrip_df['匹配的房号']), ctrip_df['房号'])
            ctrip_df['状态'] = ctrip_df['匹配的状态'].where(pd.notna(ctrip_df['匹配的状态']), ctrip_df['状态'])
            final_df = ctrip_df[['订单号', '客人姓名', '到达', '离开', '房号', '状态']]
            return final_df

        except Exception as e:
            return f"处理过程中发生未知错误: {e}."

    if st.button("开始审核", type="primary", disabled=(not ctrip_file_uploaded or not system_file_uploaded)):
        with st.spinner("正在执行三轮匹配与审核..."):
            result = perform_audit_in_streamlit(ctrip_file_uploaded, system_file_uploaded)

            if isinstance(result, str):
                st.error(result)
            else:
                st.success("审核完成！")
                st.dataframe(result)
                
                excel_data_audit = to_excel({"审核结果": result})
                st.download_button(
                    label="📥 下载审核结果 (.xlsx)",
                    data=excel_data_audit,
                    file_name="matched_orders.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download-audit-final"
                )

