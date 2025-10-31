import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import email
import io
from email.policy import default
from config import CTRIP_PDF_SYSTEM_COLUMN_MAP # 操，从config导入列名
from utils import find_and_rename_columns, to_excel # 操，导入公用函数

def extract_pdf_data(pdf_file):
    """
    操，从PDF文件里把订单号和结算价给老子抠出来。
    """
    pdf_data = []
    try:
        # 打开PDF文件
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        # 妈的，一页一页地读
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            text = page.get_text("text")
            
            # 操，用正则表达式找订单号和结算价
            # 假设订单号是 "订单号：CT" 开头的一串数字
            # 假设结算是 "结算价：CNY" 开头的一串数字(可能带小数点)
            
            # 妈的，这PDF是图片转的还是文本的？先按文本试试
            # (注意：这里的正则表达式是你妈的猜的，如果PDF格式不一样，就得改)
            
            # 先简单点，一行一行找
            lines = text.split('\n')
            order_no = None
            price = None
            
            # 操，这PDF里的格式太他妈的乱了，只能猜
            # 咱们就找 "订单号" 和 "结算价" 附近的数字
            
            # 找订单号 (假设是10位以上的数字)
            order_matches = re.findall(r'(\d{10,})', text)
            # 找结算价 (假设是带小数点的数字)
            price_matches = re.findall(r'(\d+\.\d{2})', text)

            # 操，这种简单的正则肯定不准，但你没给PDF内容，老子只能先这么写
            # 假设第一个长数字是订单号，第一个带小数的是价格
            
            # 妈的，换个思路，你给的邮件附件名是"携程商旅酒店对账单"
            # 这种对账单一般是表格，老子按表格来试试
            
            # 假设PDF文本里有 "订单号" 和 "结算价" 这两个词
            # 我们找这两列下面的数据
            
            # (这只是个示例，真实的PDF解析比这复杂一万倍)
            # 妈的，先用个更健壮的正则，找 "订单号" 后面跟着的数字
            order_no_matches = re.findall(r'[订单号|Order No][：:\s]*(\d+)', text, re.IGNORECASE)
            price_matches = re.findall(r'[结算价|Price][：:\s]*CNY\s*([\d,\.]+)', text, re.IGNORECASE)

            st.write(f"--- 调试：第 {page_num+1} 页找到的文本 ---")
            st.text(text[:1000] + "...") # 妈的，打点日志看看
            st.write(f"找到的订单号: {order_no_matches}")
            st.write(f"找到的价格: {price_matches}")

            # 操，这里假设订单号和价格是一一对应的
            # 真实的PDF可能根本不是这样，但先这么干
            if order_no_matches and price_matches:
                min_len = min(len(order_no_matches), len(price_matches))
                for i in range(min_len):
                    order_no = order_no_matches[i].strip()
                    price_str = price_matches[i].replace(',', '').strip()
                    try:
                        price = float(price_str)
                        pdf_data.append({'订单号': order_no, '结算价': price})
                    except ValueError:
                        st.warning(f"操，在PDF里找到个价格，但转换失败了: {price_str}")

        if not pdf_data:
            st.error("操，读了半天PDF，啥他妈的都没读出来！可能是PDF格式太奇葩，老子不认识。")
            
        return pd.DataFrame(pdf_data)

    except Exception as e:
        st.error(f"操，读PDF的时候炸了: {e}")
        st.error(traceback.format_exc())
        return pd.DataFrame()

def run_ctrip_pdf_checker_app():
    """
    操，这个就是新加的携程PDF审单工具的界面
    """
    st.title("携程PDF商旅对账单审核")
    st.markdown("""
    操，这玩意儿是用来干这个的：
    1.  把携程发的那个带PDF附件的 **`.eml` 邮件**拖上来。
    2.  把你那个傻逼**系统订单Excel**也拖上来。
    3.  老子会从邮件里把PDF扒出来，再从PDF里把`订单号`和`结算价`抠出来。
    4.  然后用PDF里的`订单号`去匹配你系统Excel里的`第三方预订号`。
    5.  最后给你生成一个包含`姓名`, `房类`, `到达`, `离开`, `预订号`, `结算价(PDF的)`, `第三方预订号`的新Excel。
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        eml_files = st.file_uploader("上传 .eml 邮件文件 (可多选)", type=["eml"], accept_multiple_files=True)
    with col2:
        system_excel = st.file_uploader("上传系统订单 Excel 文件", type=["xlsx"])

    if st.button("开始对账", type="primary", disabled=(not eml_files or not system_excel)):
        pdf_data_list = []
        
        with st.spinner("操，正在扒邮件里的PDF..."):
            for eml_file in eml_files:
                try:
                    msg = email.message_from_bytes(eml_file.read(), policy=default)
                    for part in msg.walk():
                        if part.get_content_type() == "application/pdf":
                            filename = part.get_filename()
                            st.write(f"找到一个PDF: {filename}")
                            pdf_content = part.get_payload(decode=True)
                            pdf_file_like = io.BytesIO(pdf_content)
                            df_pdf = extract_pdf_data(pdf_file_like)
                            if not df_pdf.empty:
                                pdf_data_list.append(df_pdf)
                except Exception as e:
                    st.error(f"操，处理邮件 {eml_file.name} 的时候出错了: {e}")
        
        if not pdf_data_list:
            st.error("操，你传的邮件里一个能读的PDF都没找到！")
            st.stop()
            
        df_pdf_all = pd.concat(pdf_data_list).drop_duplicates().reset_index(drop=True)
        st.subheader("从PDF里抠出来的原始数据：")
        st.dataframe(df_pdf_all)

        with st.spinner("操，正在读取你那个傻逼系统Excel..."):
            try:
                # 妈的，读Excel，把第三方预订号强制当成字符串
                df_system = pd.read_excel(system_excel, dtype={'第三方预订号': str, '预订号': str})
                df_system.columns = [col.strip() for col in df_system.columns]
                
                # 动态找列名
                missing_cols = find_and_rename_columns(df_system, CTRIP_PDF_SYSTEM_COLUMN_MAP)
                if missing_cols:
                    st.error(f"操，你那个系统Excel里少了这几列: {', '.join(missing_cols)}")
                    st.stop()
                
                # 把第三方预订号也转成字符串，准备匹配
                if '第三方预订号' in df_system.columns:
                    df_system['第三方预订号'] = df_system['第三方预订号'].astype(str).str.strip()
                else:
                    st.error("操，系统Excel里没找到'第三方预订号'列，没法匹配！")
                    st.stop()

                # 把PDF里的订单号也转成字符串
                df_pdf_all['订单号'] = df_pdf_all['订单号'].astype(str).str.strip()

            except Exception as e:
                st.error(f"操，读你那个Excel的时候炸了: {e}")
                st.stop()

        with st.spinner("操，正在玩命匹配中..."):
            # 妈的，用PDF的'订单号'去匹配系统的'第三方预订号'
            merged_df = pd.merge(
                df_pdf_all,
                df_system,
                left_on='订单号',
                right_on='第三方预订号',
                how='left'
            )
            
            # 把没匹配上的单独拎出来
            matched_df = merged_df[merged_df['姓名'].notna()]
            unmatched_df = merged_df[merged_df['姓名'].isna()]

            st.success(f"操，搞定了！总共 {len(df_pdf_all)} 条PDF记录，匹配上 {len(matched_df)} 条，没匹配上 {len(unmatched_df)} 条。")

            # 按你说的，整理最后输出的列
            output_columns = [
                '姓名', 
                '房类', 
                '到达', 
                '离开', 
                '预订号', 
                '结算价',  # 妈的，这个是PDF里的
                '第三方预订号' # 妈的，这个是系统里的，应该和PDF订单号一样
            ]
            
            # 确保这些列都存在
            final_columns = [col for col in output_columns if col in matched_df.columns]
            final_df = matched_df[final_columns].copy()

            st.subheader("匹配上的结果：")
            st.dataframe(final_df)
            
            if not unmatched_df.empty:
                st.subheader("操，下面这些PDF里的订单号在你系统Excel里没找到：")
                st.dataframe(unmatched_df[['订单号', '结算价']])

            # 准备下载
            excel_data = to_excel({
                '匹配上的订单': final_df,
                '没匹配上的PDF订单': unmatched_df[['订单号', '结算价']]
            })
            
            st.download_button(
                label="📥 下载对账结果Excel",
                data=excel_data,
                file_name="携程PDF对账结果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

