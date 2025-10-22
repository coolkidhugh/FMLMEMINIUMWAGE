import streamlit as st
import pandas as pd
import numpy as np
from utils import find_and_rename_columns, to_excel # 从 utils 导入函数
from config import UPGRADE_FINDER_COLUMN_MAP # 从 config 导入列名映射 (这个名字不改了，懒得动config)

def run_upgrade_finder_app():
    """运行【可自定义关键字】备注查找工具的 Streamlit 界面。"""
    st.title(f"备注关键字查找 (DIY版)") # 操，改标题
    st.markdown("""
    操，这个工具让你在**系统订单 Excel** 的 **`备注`** 列里查找**任何你想要的字**。
    1.  上传你的**系统订单 Excel** 文件。
    2.  在下面的框里输入你要查找的 **关键字** (比如 `升级`, `延迟`, `加床` 等等)。
    3.  点“开始查找”，老子就把包含这个关键字的订单信息给你列出来，包括 `预订号`, `第三方预定号`, `最近修改人`。
    """)

    # --- 操，加个输入框让你填关键字 ---
    search_keyword = st.text_input("输入你要在“备注”列查找的关键字", value="升级")

    uploaded_system_excel = st.file_uploader("上传系统订单 Excel 文件 (.xlsx)", type=["xlsx"], key="upgrade_system_uploader")

    if st.button("开始查找", type="primary", disabled=(not uploaded_system_excel)):
        if not uploaded_system_excel: st.warning("操，你他妈的还没上传系统订单 Excel 文件呢！"); st.stop()
        if not search_keyword: st.warning("操，你他妈的还没输入要查找的关键字呢！"); st.stop() # 操，加个检查

        try:
            # --- 操，强制把可能的列读成字符串 ---
            possible_cols = (
                UPGRADE_FINDER_COLUMN_MAP.get('预订号', []) +
                UPGRADE_FINDER_COLUMN_MAP.get('第三方预定号', []) +
                UPGRADE_FINDER_COLUMN_MAP.get('最近修改人', []) +
                UPGRADE_FINDER_COLUMN_MAP.get('备注', [])
            )
            dtype_map = {col: str for col in possible_cols}

            system_df = pd.read_excel(uploaded_system_excel, dtype=dtype_map, parse_dates=False)
            system_df.columns = system_df.columns.str.strip()

            # --- 操，检查并重命名列 ---
            missing_cols = find_and_rename_columns(system_df, UPGRADE_FINDER_COLUMN_MAP)
            required_cols = ['备注', '预订号', '最近修改人']
            missing_required = [col for col in required_cols if col not in system_df.columns]
            if missing_required: st.error(f"操！系统订单 Excel 文件里找不到必需的列: {', '.join(missing_required)}。没法继续了。"); st.stop()

            # --- 操，用你输入的关键字来查找！ ---
            st.info(f"正在备注列中查找包含 “{search_keyword}” 的订单...")
            # fillna('') 防止备注列有空值导致 .str.contains 报错
            # case=False 忽略大小写, na=False 把空备注当作不包含关键字
            keyword_mask = system_df['备注'].fillna('').str.contains(search_keyword, case=False, na=False, regex=False) # regex=False 提高点效率
            found_df = system_df[keyword_mask].copy()

        except Exception as e:
            st.error(f"读取或处理系统订单 Excel 文件时出错: {e}"); st.stop()

        st.success(f"查找完成！共找到 {len(found_df)} 条备注包含 “{search_keyword}” 的订单。")

        if not found_df.empty:
            # --- 操，选择并排列你要的列 ---
            output_cols = ['预订号', '第三方预定号', '最近修改人', '备注']
            existing_output_cols = [col for col in output_cols if col in found_df.columns] # 只保留实际存在的列
            result_df = found_df[existing_output_cols]

            st.dataframe(result_df.fillna('')) # 把空值显示为空字符串

            excel_data = to_excel({f"备注含_{search_keyword}": result_df}) # 文件名也改动态的
            st.download_button(
                label=f"📥 下载查找结果 (.xlsx)",
                data=excel_data,
                file_name=f"remark_search_{search_keyword}.xlsx", # 文件名也动态
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download-remark-search-results"
            )
        else:
            st.warning(f"在系统订单的备注列中没有找到包含 “{search_keyword}” 字样的记录。")

