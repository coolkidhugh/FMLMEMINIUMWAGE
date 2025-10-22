import streamlit as st
import pandas as pd
import re
import email
import base64
import chardet # Need to add this to requirements.txt
from io import BytesIO
from config import APP_NAME, MEITUAN_SYSTEM_COLUMN_MAP # Added MEITUAN_SYSTEM_COLUMN_MAP
from utils import find_and_rename_columns, to_excel

def get_eml_body(file_content):
    """操，从 EML 文件内容里把正文文本抠出来，解码啥的都干了"""
    msg = email.message_from_bytes(file_content)
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # 只找 text/plain，并且不是附件的
            if content_type == "text/plain" and "attachment" not in content_disposition:
                charset = part.get_content_charset()
                payload = part.get_payload(decode=True)
                
                # 尝试解码
                if payload:
                    if charset:
                        try:
                            body = payload.decode(charset, errors='replace')
                            break # 找到第一个就够了
                        except (LookupError, UnicodeDecodeError):
                            pass # 解码失败，试试下面的自动检测
                    
                    # 如果没有charset或者解码失败，尝试自动检测
                    try:
                        detected_encoding = chardet.detect(payload)['encoding']
                        if detected_encoding:
                            body = payload.decode(detected_encoding, errors='replace')
                            break # 找到第一个就够了
                    except Exception:
                         # 妈的，实在不行就算了
                        body = payload.decode('utf-8', errors='replace') # 最后尝试UTF-8
                        break
            # 如果没找到 text/plain，试试 text/html，然后去掉标签（虽然效果可能不好）
            elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                 charset = part.get_content_charset()
                 payload = part.get_payload(decode=True)
                 if payload:
                    try:
                        html_body = payload.decode(charset if charset else 'utf-8', errors='replace')
                        # 极简处理：去掉HTML标签，效果可能很差
                        body = re.sub('<[^<]+?>', '', html_body)
                        # 注意：这里找到HTML就不再找了，因为通常邮件里要么纯文本要么HTML
                        break 
                    except Exception:
                        pass # HTML也搞不定就算了
    else:
        # 不是 multipart 的邮件
        charset = msg.get_content_charset()
        payload = msg.get_payload(decode=True)
        if payload:
            try:
                if charset:
                    body = payload.decode(charset, errors='replace')
                else:
                    detected_encoding = chardet.detect(payload)['encoding']
                    body = payload.decode(detected_encoding if detected_encoding else 'utf-8', errors='replace')
            except Exception:
                body = payload.decode('utf-8', errors='replace') # 最后尝试UTF-8

    # 操，有时候解码出来还带些乱七八糟的换行，处理一下
    if body:
        body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
        
    return body


def extract_jlg_numbers(text):
    """从一大坨屎一样的文本里找到 (JLG)后面的数字"""
    # 匹配 (JLG) 后紧跟的一串数字
    matches = re.findall(r'\(JLG\)(\d+)', text)
    # 操，有时候可能是 JLG)12345 这种傻逼格式，也加上
    matches += re.findall(r'JLG\)(\d+)', text)
    # 妈的，还有可能是 JLG<数字> 这种更傻逼的格式
    matches += re.findall(r'JLG(\d+)', text) 
    
    # 去重并返回纯数字列表
    return list(set(matches))


def run_meituan_checker_app():
    """美团邮件审核工具的主界面"""
    st.title(f"{APP_NAME} - 美团邮件审核")
    st.markdown("""
    操，这个工具是用来搞美团邮件的。
    1.  把你从邮件导出的 `.eml` 文件（可以一次传多个）传上来。
    2.  把你最新的**系统订单 Excel** 文件也给老子传上来。
    3.  点下面的按钮，老子就帮你把邮件里的 JLG 号码抠出来，去系统订单里找匹配的记录。
    """)

    col1, col2 = st.columns(2)
    with col1:
        eml_files = st.file_uploader("上传美团邮件 (.eml 文件)", type=["eml"], accept_multiple_files=True, key="meituan_eml_uploader")
    with col2:
        system_file = st.file_uploader("上传系统订单 Excel 文件 (.xlsx)", type=["xlsx"], key="meituan_system_uploader")

    if st.button("开始审核美团订单", type="primary", disabled=(not eml_files or not system_file)):
        if not MEITUAN_SYSTEM_COLUMN_MAP:
             st.error("操，配置文件 config.py 里没找到 `MEITUAN_SYSTEM_COLUMN_MAP`，老子不知道系统订单里哪些列是啥意思！")
             st.stop()
             
        all_jlg_numbers = set()
        eml_errors = []

        with st.spinner("正在读取邮件，抠 JLG 号码..."):
            for eml_file in eml_files:
                try:
                    content = eml_file.getvalue()
                    body = get_eml_body(content)
                    if not body:
                        # 妈的，有时候是 base64 套 base64？ 再试试
                        try:
                           maybe_b64 = content.split(b'\r\n\r\n', 1)[1]
                           decoded_again = base64.b64decode(maybe_b64)
                           body = get_eml_body(decoded_again)
                        except Exception:
                           pass # 还不行就算了
                           
                    if body:
                        numbers = extract_jlg_numbers(body)
                        if numbers:
                            all_jlg_numbers.update(numbers)
                        else:
                            st.warning(f"文件 '{eml_file.name}' 里没找到 JLG 号码。")
                    else:
                         st.warning(f"操，读不懂文件 '{eml_file.name}' 的正文内容。")

                except Exception as e:
                    eml_errors.append(f"处理文件 '{eml_file.name}' 出错: {e}")

        if eml_errors:
            st.error("处理部分 EML 文件时出错：")
            for error in eml_errors:
                st.error(f"- {error}")

        if not all_jlg_numbers:
            st.error("操，所有上传的邮件里都没找到任何 JLG 号码！检查下你的文件或者邮件格式。")
            st.stop()

        st.info(f"从邮件里找到了 {len(all_jlg_numbers)} 个不重复的 JLG 号码。")
        # st.write("找到的号码:", ", ".join(sorted(list(all_jlg_numbers)))) # Debug用，先注释掉

        try:
            with st.spinner("正在读取系统订单并匹配..."):
                system_df = pd.read_excel(system_file)
                system_df.columns = system_df.columns.str.strip()

                # 动态查找并重命名列
                missing_cols = find_and_rename_columns(system_df, MEITUAN_SYSTEM_COLUMN_MAP)
                if missing_cols:
                    st.error(f"操！系统订单 Excel 文件里缺少必需的列: {', '.join(missing_cols)}。在 config.py 里检查 `MEITUAN_SYSTEM_COLUMN_MAP` 配置！")
                    st.stop()

                # 确保 '预订号' 列是字符串类型，方便匹配
                system_df['预订号'] = system_df['预订号'].astype(str).str.strip()
                
                # 开始匹配
                matched_rows = system_df[system_df['预订号'].isin(all_jlg_numbers)].copy()

            if matched_rows.empty:
                st.warning("操，邮件里的 JLG 号码在系统订单里一个都没匹配上！")
            else:
                st.success(f"成功匹配到 {len(matched_rows)} 条记录！")
                
                # 只显示需要的列
                display_columns = ['姓名', '到达', '离开', '预订号', '第三方预定号']
                # 确保这些列都存在
                final_columns = [col for col in display_columns if col in matched_rows.columns]
                
                st.dataframe(matched_rows[final_columns])

                # 添加下载按钮
                excel_data = to_excel({"美团审核结果": matched_rows[final_columns]})
                st.download_button(
                    label="📥 下载匹配结果 (.xlsx)",
                    data=excel_data,
                    file_name="meituan_matched_orders.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download-meituan-results"
                )
                
            # 报告哪些号码没匹配上
            found_system_numbers = set(matched_rows['预订号'].astype(str))
            missing_numbers = all_jlg_numbers - found_system_numbers
            if missing_numbers:
                 st.warning(f"有 {len(missing_numbers)} 个从邮件里找到的 JLG 号码在系统订单里没匹配上：")
                 st.warning(", ".join(sorted(list(missing_numbers))))


        except Exception as e:
            st.error(f"操！读取或处理系统订单 Excel 文件时出错了: {e}")
