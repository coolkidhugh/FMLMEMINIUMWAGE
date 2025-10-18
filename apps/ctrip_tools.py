import streamlit as st
import pandas as pd
import numpy as np
import re
from utils import to_excel
from config import CTRIP_DATE_SYSTEM_COLUMNS, CTRIP_DATE_CTRIP_COLUMNS, CTRIP_AUDIT_CTRIP_COLUMN_MAP, CTRIP_AUDIT_SYSTEM_COLUMN_MAP

# ==============================================================================
# --- [APP] Ctrip Date Comparison Tool ---
# ==============================================================================

def run_ctrip_date_comparison_app():
    """Renders the UI for the Ctrip Date Comparison tool."""
    st.title("金陵工具箱 - 携程对日期")
    st.markdown("""
    此工具用于比对 **系统订单 (System Order)** 和 **携程订单 (Ctrip Order)**。
    1.  请分别上传两个对应的 Excel 文件。
    2.  工具会自动识别并统一两种不同的日期格式 (`YYMMDD` 和 `YYYY/MM/DD`)。
    3.  点击“开始比对”，下方将显示结果摘要，并提供详细报告下载。
    """)

    # --- File Upload ---
    col1, col2 = st.columns(2)
    with col1:
        system_file_uploaded = st.file_uploader("上传您的 System Order (.xlsx)", type=["xlsx"], key="system_uploader")
    with col2:
        ctrip_file_uploaded = st.file_uploader("上传您的 Ctrip Order (.xlsx)", type=["xlsx"], key="ctrip_uploader")

    # --- Comparison Logic ---
    if st.button("开始比对", type="primary", disabled=(not system_file_uploaded or not ctrip_file_uploaded)):
        results = perform_date_comparison(system_file_uploaded, ctrip_file_uploaded)

        if isinstance(results, str): # Handle error messages
            st.error(results)
        elif results:
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
            with st.expander(f"查看 {len(date_mismatch_df)} 条日期不匹配的订单", expanded=not date_mismatch_df.empty):
                if not date_mismatch_df.empty:
                    st.dataframe(date_mismatch_df)
                else:
                    st.info("没有发现日期不匹配的订单。")
            
            with st.expander(f"查看 {len(not_found_df)} 条在携程中未找到的订单"):
                if not not_found_df.empty:
                    st.dataframe(not_found_df)
                else:
                    st.info("所有系统订单都能在携程订单中找到。")

# --- Helper function for Date Comparison ---
@st.cache_data
def perform_date_comparison(_system_file_buffer, _ctrip_file_buffer):
    """Core logic to compare two dataframes for date mismatches."""
    
    def clean_data(file_buffer, cols_map, date_format=None):
        try:
            df = pd.read_excel(file_buffer)
            required_cols = list(cols_map.values())
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return f"文件缺少必需的列: {', '.join(missing_cols)}"

            df_selected = df[required_cols].copy()
            df_selected.columns = ['预定号', '入住日期', '离店日期']
            
            df_selected['预定号'] = df_selected['预定号'].astype(str).str.strip().str.upper()
            
            date_cols = ['入住日期', '离店日期']
            for col in date_cols:
                if date_format:
                    df_selected[col] = pd.to_datetime(df_selected[col], format=date_format, errors='coerce').dt.date
                else:
                    df_selected[col] = pd.to_datetime(df_selected[col], errors='coerce').dt.date
            
            df_selected.dropna(subset=['预定号'] + date_cols, inplace=True)
            return df_selected
        except Exception as e:
            return f"读取文件失败: {e}"

    df_system = clean_data(_system_file_buffer, CTRIP_DATE_SYSTEM_COLUMNS, date_format='%y%m%d')
    if isinstance(df_system, str): return df_system

    df_ctrip = clean_data(_ctrip_file_buffer, CTRIP_DATE_CTRIP_COLUMNS)
    if isinstance(df_ctrip, str): return df_ctrip
    
    merged_df = pd.merge(df_system, df_ctrip, on='预定号', how='left', suffixes=('_系统', '_Ctrip'))

    not_found_df = merged_df[merged_df['入住日期_Ctrip'].isnull()][['预定号', '入住日期_系统', '离店日期_系统']]
    
    found_df = merged_df.dropna(subset=['入住日期_Ctrip']).copy()
    
    date_mismatch_df = found_df[
        (found_df['入住日期_系统'] != found_df['入住日期_Ctrip']) |
        (found_df['离店日期_系统'] != found_df['离店日期_Ctrip'])
    ][['预定号', '入住日期_系统', '离店日期_系统', '入住日期_Ctrip', '离店日期_Ctrip']]
    
    return date_mismatch_df, not_found_df

# ==============================================================================
# --- [APP] Ctrip Audit Tool ---
# ==============================================================================

def run_ctrip_audit_app():
    """Renders the UI for the Ctrip Audit tool."""
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

    # --- File Upload ---
    col1, col2 = st.columns(2)
    with col1:
        ctrip_file_uploaded = st.file_uploader("上传携程订单.xlsx", type=["xlsx"], key="ctrip_audit_uploader_final")
    with col2:
        system_file_uploaded = st.file_uploader("上传系统订单.xlsx", type=["xlsx"], key="system_audit_uploader_final")

    if st.button("开始审核", type="primary", disabled=(not ctrip_file_uploaded or not system_file_uploaded)):
        with st.spinner("正在执行三轮匹配与审核..."):
            result = perform_audit(ctrip_file_uploaded, system_file_uploaded)

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

# --- Helper function for Audit ---
def perform_audit(ctrip_buffer, system_buffer):
    """Core logic for the three-round audit process."""
    def clean_confirmation_number(number):
        if pd.isna(number): return None
        digits = re.findall(r'\d+', str(number))
        return ''.join(digits) if digits else None

    def clean_third_party_number(number):
        if pd.isna(number): return None
        return re.sub(r'R\d+$', '', str(number).strip())
    
    def find_and_rename_columns(df, column_map):
        """Finds columns from a list of possibles and renames to a standard name."""
        missing_cols = []
        for standard_name, possible_names in column_map.items():
            found_col = next((name for name in possible_names if name in df.columns), None)
            if not found_col: # Try fuzzy match if exact match fails
                found_col = next((col for col in df.columns for name in possible_names if name in col), None)

            if found_col:
                df.rename(columns={found_col: standard_name}, inplace=True)
            else:
                missing_cols.append(standard_name)
        return missing_cols

    try:
        ctrip_df = pd.read_excel(ctrip_buffer, dtype={'订单号': str, '确认号': str})
        system_df = pd.read_excel(system_buffer, dtype={'预订号': str, '第三方预定号': str})

        if ctrip_df.empty: return "错误: 上传的携程订单文件为空。"
        if system_df.empty: return "错误: 上传的系统订单文件为空。"

        ctrip_df.columns = ctrip_df.columns.str.strip()
        system_df.columns = system_df.columns.str.strip()

        missing_ctrip = find_and_rename_columns(ctrip_df, CTRIP_AUDIT_CTRIP_COLUMN_MAP)
        if missing_ctrip: return f"错误: 携程文件缺少列: {', '.join(missing_ctrip)}"
        
        missing_system = find_and_rename_columns(system_df, CTRIP_AUDIT_SYSTEM_COLUMN_MAP)
        if missing_system: return f"错误: 系统文件缺少列: {', '.join(missing_system)}"
        
        # --- Data Preparation ---
        ctrip_df.rename(columns={'客人姓名': '姓名'}, inplace=True)
        ctrip_df['姓名'] = ctrip_df['姓名'].astype(str).str.strip()
        system_df['姓名'] = system_df['姓名'].astype(str).str.strip()

        ctrip_df['纯数字确认号'] = ctrip_df['确认号'].apply(clean_confirmation_number)
        system_df['清洗后第三方预定号'] = system_df['第三方预定号'].apply(clean_third_party_number)

        system_df.drop_duplicates(subset=['预订号', '姓名', '清洗后第三方预定号'], keep='first', inplace=True)
        
        # --- Matching Logic ---
        # Round 1: Third-party booking number
        merged1 = pd.merge(
            ctrip_df, 
            system_df, 
            left_on='订单号', 
            right_on='清洗后第三方预定号', 
            how='left', 
            suffixes=('', '_sys1')
        )
        
        # Round 2: Confirmation number
        unmatched1 = merged1[merged1['预订号'].isna()].drop(columns=[c for c in merged1.columns if '_sys1' in c])
        merged2 = pd.merge(
            unmatched1,
            system_df,
            left_on='纯数字确认号',
            right_on='预订号',
            how='left',
            suffixes=('', '_sys2')
        )

        # Round 3: Guest name
        unmatched2 = merged2[merged2['预订号_sys2'].isna()].drop(columns=[c for c in merged2.columns if '_sys2' in c])
        merged3 = pd.merge(
            unmatched2,
            system_df,
            on='姓名',
            how='left',
            suffixes=('', '_sys3')
        )

        # --- Combine Results ---
        matched1 = merged1.dropna(subset=['预订号'])
        matched2 = merged2.dropna(subset=['预订号_sys2'])
        matched3 = merged3.dropna(subset=['预订号_sys3'])
        
        # Standardize columns before combining
        for df, suffix in [(matched1, ''), (matched2, '_sys2'), (matched3, '_sys3')]:
            df.rename(columns={
                f'离开{suffix}': '匹配的离开时间',
                f'房号{suffix}': '匹配的房号',
                f'状态{suffix}': '匹配的状态'
            }, inplace=True)

        final_df = pd.concat([
            matched1, matched2, matched3, 
            merged3[merged3['预订号_sys3'].isna()] # Unmatched from round 3
        ], ignore_index=True, sort=False)
        
        # Update original values with matched values
        final_df['离开'] = final_df['匹配的离开时间'].fillna(final_df['离开'])
        final_df['房号'] = final_df['匹配的房号'].fillna(np.nan)
        final_df['状态'] = final_df['匹配的状态'].fillna('未匹配')

        return final_df[['订单号', '姓名', '到达', '离开', '房号', '状态']]
        
    except Exception as e:
        return f"处理过程中发生未知错误: {e}"

