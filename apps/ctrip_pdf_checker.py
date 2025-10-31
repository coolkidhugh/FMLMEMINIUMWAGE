import streamlit as st
import pandas as pd
import re
import fitz  # 操, PyMuPDF
import io
import base64
import email # 操, 用来读 .eml
from email.policy import default
from config import CTRIP_PDF_SYSTEM_COLUMN_MAP # 操, 导入配置
from utils import find_and_rename_columns, to_excel # 操, 导入公用函数

def parse_pdf_text(pdf_bytes):
    """
    操, 这个函数专门从PDF的二进制数据里把订单号和价格抠出来。
    新逻辑：会把所有订单和价格都扒下来，然后按订单号分组求和，抵消掉那些一正一负的傻逼订单。
    """
    text = ""
    try:
        # 操, 打开PDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            # 操，把所有换行替换成空格，对付那些傻逼换行
            text += page.get_text("text").replace('\n', ' ') + " "
        pdf_doc.close()
    except Exception as e:
        return f"操，PyMuPDF库在读取PDF时出错了: {e}"

    if not text:
        return "操，PDF是空的或者读不出来字。"

    st.text_area("--- 调试：从PDF读出的原始文本 (已替换换行) ---", text, height=150)

    # 操，新版正则表达式：
    # (\d{16})     : 专门抓16位数字的订单号 (你说的)
    # \s(.*?)\s      : 抓中间所有的垃圾信息，非贪婪模式
    # (-?\d+\.\d{2}) : 抓带正负号和小数点的结算价
    # 妈的，携程有时候订单号和入住者之间没空格，老子把中间的 \s 改成 (.*?)
    matches = re.findall(r"(\d{16})(.*?)\s(-?\d+\.\d{2})", text)

    if not matches:
        st.warning("操，在PDF里没找到 '16位订单号 ... 价格' 这种格式的数据。")
        # 操，尝试只抓订单号，万一价格匹配不上呢
        order_ids_only = re.findall(r"(\d{16})", text)
        st.info(f"只抓到这些16位订单号 (没抓到价格): {list(set(order_ids_only))}")
        return pd.DataFrame(columns=['订单号', '结算价']) # 返回个空的DataFrame

    # 操，把抓到的数据放进DataFrame
    pdf_data = pd.DataFrame(matches, columns=['订单号', '详情', '结算价_str'])
    
    # 操，把价格转成数字，转不了的都算0
    pdf_data['结算价'] = pd.to_numeric(pdf_data['结算价_str'], errors='coerce').fillna(0)
    
    st.info("--- 调试：从PDF扒下来的原始订单和价格 ---")
    st.dataframe(pdf_data[['订单号', '结算价']], use_container_width=True)
    
    # --- 核心逻辑：分组求和 ---
    st.info("--- 开始对账：按订单号聚合结算价 (正负抵消) ---")
    # 操，按订单号分组，把结算价加起来
    aggregated_df = pdf_data.groupby('订单号')['结算价'].sum().reset_index()
    
    # 操，只保留那些最后结算价不是0的订单
    final_pdf_df = aggregated_df[aggregated_df['结算价'] != 0].copy()
    
    st.success("--- 聚合完成！下面是结算价不为0的最终订单 ---")
    st.dataframe(final_pdf_df, use_container_width=True)
    
    return final_pdf_df


def run_ctrip_pdf_checker_app():
    """
    操，这是“携程PDF审单”的主程序
    """
    st.title(f"携程PDF审单 (邮件套PDF)")
    st.markdown("""
    操，这个工具是专门对付携程那个傻逼`.eml`邮件里藏着`.pdf`附件的对账单的。
    1.  上传包含PDF附件的 `.eml` 邮件文件。
    2.  上传你从系统导出的订单Excel (xlsx)。
    3.  老子会从PDF里把**16位订单号**和**结算价**抠出来，**自动抵消正负订单**，然后去Excel里找匹配的**第三方预订号**。
    4.  最后给你一份干净的对账Excel。
    """)

    col1, col2 = st.columns(2)
    with col1:
        eml_file = st.file_uploader("1. 上传 `.eml` 邮件文件", type=["eml"])
    with col2:
        system_excel = st.file_uploader("2. 上传系统订单 Excel (.xlsx)", type=["xlsx"])

    if st.button("开始对账", type="primary", disabled=(not eml_file or not system_excel)):
        pdf_df_list = []
        
        try:
            # 操，读 .eml 文件
            msg = email.message_from_bytes(eml_file.getvalue(), policy=default)
            
            found_pdf = False
            for part in msg.walk():
                if part.get_content_type() == "application/pdf":
                    found_pdf = True
                    pdf_name = part.get_filename() or "未命名.pdf"
                    st.success(f"找到一个PDF: {pdf_name}")
                    
                    # 操，获取PDF的二进制内容
                    pdf_bytes = part.get_payload(decode=True)
                    
                    # 操，调用新函数解析PDF
                    with st.spinner(f"正在读取 '{pdf_name}' 里的数据..."):
                        result_df = parse_pdf_text(io.BytesIO(pdf_bytes))
                        
                        if isinstance(result_df, str):
                            st.error(result_df) # 操，出错了
                        elif result_df.empty:
                            st.warning(f"'{pdf_name}' 里没找到有效的、结算价不为0的订单。")
                        else:
                            pdf_df_list.append(result_df)
            
            if not found_pdf:
                st.error("操，你传的邮件里一个PDF附件都没找到！")
                st.stop()
        
        except Exception as e:
            st.error(f"操，读取 .eml 文件时出错了: {e}")
            st.stop()
    
        if not pdf_df_list:
            st.error("操，所有PDF都读完了，但没找到任何有效的订单数据。")
            st.stop()
        
        # 操，把所有PDF里读出来的数据合并到一起
        all_pdf_data = pd.concat(pdf_df_list).drop_duplicates(subset=['订单号']).reset_index(drop=True)
        
        # --- 开始处理系统Excel ---
        try:
            with st.spinner("正在读取系统Excel..."):
                system_df = pd.read_excel(system_excel, dtype=str) # 操，全当成文本读
                system_df.columns = system_df.columns.str.strip() # 操，去他妈的空格
            
            # 操，动态查找并重命名列
            missing_cols = find_and_rename_columns(system_df, CTRIP_PDF_SYSTEM_COLUMN_MAP)
            if missing_cols:
                st.error(f"操，你的系统Excel文件里少了这些列: {', '.join(missing_cols)}")
                st.stop()
            
            # 操，只保留需要的列
            required_system_cols = list(CTRIP_PDF_SYSTEM_COLUMN_MAP.keys())
            system_df = system_df[required_system_cols]
            
        except Exception as e:
            st.error(f"操，读取系统Excel时出错了: {e}")
            st.stop()

        # --- 核心匹配逻辑 ---
        with st.spinner("正在用PDF数据匹配系统订单..."):
            # 操，用PDF的'订单号' 匹配 系统的'第三方预订号'
            merged_df = pd.merge(
                system_df,
                all_pdf_data,
                left_on='第三方预订号',
                right_on='订单号'
            )
        
        if merged_df.empty:
            st.warning("操，PDF里的订单号一个都没在你系统Excel的'第三方预订号'里找到。")
            st.subheader("--- PDF里的订单号 (聚合后结算价不为0) ---")
            st.dataframe(all_pdf_data)
            st.subheader("--- 系统Excel里的第三方预订号 (前100个) ---")
            st.dataframe(system_df[['第三方预订号', '姓名']].head(100))
            st.stop()
        
        st.success(f"操，牛逼！成功匹配上 {len(merged_df)} 条订单！")

        # 操，按你说的列名和顺序准备结果
        final_output_df = merged_df[[
            '姓名',
            '房类',
            '到达',
            '离开',
            '预订号',
            '结算价',  # 操，这个就是PDF里来的
            '第三方预订号'
        ]]
        
        # 操，重命名一下结算价，免得你搞混
        final_output_df = final_output_df.rename(columns={'结算价': '结算价(来自PDF)'})

        st.dataframe(final_output_df, use_container_width=True)

        # 操，准备下载
        excel_data = to_excel({"携程PDF对账结果": final_output_df})
        st.download_button(
            label="📥 下载对账结果Excel",
            data=excel_data,
            file_name="ctrip_pdf_audit_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

