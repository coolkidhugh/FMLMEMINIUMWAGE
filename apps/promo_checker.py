import streamlit as st
import pandas as pd
from utils import find_and_rename_columns
from config import PROMO_CHECKER_COLUMN_MAP

def perform_promo_check(df):
    """
    Performs the check for the "Consecutive Stay Benefit" promotion.
    """
    # 动态查找并重命名列
    missing_cols = find_and_rename_columns(df, PROMO_CHECKER_COLUMN_MAP)
    if missing_cols:
        return f"错误：上传的文件中缺少以下必需的列: {', '.join(missing_cols)}"

    df_copy = df.copy()

    # 确保关键列是字符串格式，以便进行文本查找
    df_copy['备注'] = df_copy['备注'].astype(str)
    df_copy['房类'] = df_copy['房类'].astype(str)
    df_copy['订单号'] = df_copy['订单号'].astype(str)

    # 条件1: 在“备注”中查找关键字，不区分大小写，处理空值
    condition1 = df_copy['备注'].str.contains('早餐', case=False, na=False) & \
                 df_copy['备注'].str.contains('吉祥物', case=False, na=False)

    # 条件2: 在“房类”中确认是否为'JEKN'
    condition2 = df_copy['房类'].str.contains('JEKN', case=False, na=False)

    # 合并两个条件进行筛选
    filtered_df = df_copy[condition1 & condition2]

    if not filtered_df.empty:
        # 提取并重命名订单号列
        result_df = filtered_df[['订单号']].copy()
        result_df.rename(columns={'订单号': '需要手工维护的订单号'}, inplace=True)
        return result_df.reset_index(drop=True)
    else:
        # 如果没有找到匹配项，返回一个空DataFrame
        return pd.DataFrame()

def run_promo_checker_app():
    """Renders the Streamlit UI for the promotion checker tool."""
    st.title("金陵工具箱 - 携程连住权益审核")
    st.markdown("""
    #### 使用说明:
    1.  上传包含“备注”、“房类”和订单号的携程订单Excel文件。
    2.  工具会自动查找备注中包含 **“早餐”** 和 **“吉祥物”** 关键字，并且房类为 **“JEKN”** 的订单。
    3.  下方将直接显示所有需要手工维护的订单号列表。
    """)

    uploaded_file = st.file_uploader(
        "上传您的携程订单 Excel 文件 (.xlsx)", 
        type=["xlsx"], 
        key="promo_checker_uploader"
    )

    if uploaded_file:
        if st.button("开始审核", type="primary"):
            with st.spinner("正在审核中，请稍候..."):
                try:
                    df = pd.read_excel(uploaded_file)
                    result = perform_promo_check(df)

                    if isinstance(result, str):
                        st.error(result)
                    elif result.empty:
                        st.success("审核完成！未发现需要手工维护“连住权益”的订单。")
                    else:
                        st.success(f"审核完成！共找到 {len(result)} 条需要手工维护的订单：")
                        st.dataframe(result, use_container_width=True)
                except Exception as e:
                    st.error(f"处理文件时发生未知错误: {e}")
