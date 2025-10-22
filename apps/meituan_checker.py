import streamlit as st
import pandas as pd
import re
import email
from email import policy
from email.parser import BytesParser
import chardet
import io
import base64
from utils import find_and_rename_columns, to_excel # 从 utils 导入函数
from config import MEITUAN_SYSTEM_COLUMN_MAP # 从 config 导入列名映射

def parse_eml(file_content):
    """解析 EML 文件内容，提取文本信息，自动检测编码。"""
    try:
        # 使用 BytesParser 解析原始字节内容
        msg = BytesParser(policy=policy.default).parsebytes(file_content)

        body_text = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # 跳过附件和非文本部分
                if part.is_attachment() or "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        # 获取原始字节负载
                        payload_bytes = part.get_payload(decode=True)
                        # 检测编码
                        detected_encoding = chardet.detect(payload_bytes)['encoding']
                        if detected_encoding:
                            body_text += payload_bytes.decode(detected_encoding, errors='replace')
                        else:
                            # 如果检测失败，尝试用 utf-8 或 gbk
                            try:
                                body_text += payload_bytes.decode('utf-8', errors='replace')
                            except UnicodeDecodeError:
                                body_text += payload_bytes.decode('gbk', errors='replace')
                        body_text += "\n" # 添加换行符分隔不同部分
                    except Exception as e_decode:
                        st.warning(f"解码 text/plain 部分时出错: {e_decode}")
                        # 如果解码失败，尝试获取原始负载（可能是 base64 编码的）
                        raw_payload = part.get_payload(decode=False)
                        if isinstance(raw_payload, str):
                            try:
                                decoded_bytes = base64.b64decode(raw_payload)
                                detected_encoding = chardet.detect(decoded_bytes)['encoding']
                                if detected_encoding:
                                     body_text += decoded_bytes.decode(detected_encoding, errors='replace') + "\n"
                            except Exception:
                                pass # 忽略解码 base64 失败的情况

                elif content_type == "text/html":
                     # 可以选择性地处理 HTML 内容，例如提取纯文本，但当前需求只关注 JLG
                     pass
        else:
            # 处理非 multipart 邮件
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                 try:
                    payload_bytes = msg.get_payload(decode=True)
                    detected_encoding = chardet.detect(payload_bytes)['encoding']
                    if detected_encoding:
                        body_text = payload_bytes.decode(detected_encoding, errors='replace')
                    else:
                        try:
                           body_text = payload_bytes.decode('utf-8', errors='replace')
                        except UnicodeDecodeError:
                           body_text = payload_bytes.decode('gbk', errors='replace')
                 except Exception as e_non_multi:
                     st.warning(f"解码非 multipart 邮件时出错: {e_non_multi}")
                     raw_payload = msg.get_payload(decode=False)
                     if isinstance(raw_payload, str):
                            try:
                                decoded_bytes = base64.b64decode(raw_payload)
                                detected_encoding = chardet.detect(decoded_bytes)['encoding']
                                if detected_encoding:
                                     body_text += decoded_bytes.decode(detected_encoding, errors='replace') + "\n"
                            except Exception:
                                pass

        return body_text

    except Exception as e:
        st.error(f"解析 EML 文件时发生严重错误: {e}")
        return None

def extract_jlg_numbers(text):
    """从文本中提取所有 JLG 号码。"""
    if not text:
        return []
    # 操，这个正则表达式找 (JLG)后面的数字
    jlg_numbers = re.findall(r'\(JLG\)(\d+)', text)
    return list(set(jlg_numbers)) # 去重后返回列表

def convert_status_to_status2(status):
    """操，把状态码转成中文描述"""
    status_str = str(status).strip().upper() # 转大写，去空格
    if status_str == 'R':
        return '预定成功'
    elif status_str == 'I':
        return '在住'
    elif status_str in ['D', 'S', 'O']:
        return '离店'
    elif status_str == 'X':
        return '无效'
    else:
        return '未知状态' # 操，防止有其他傻逼状态码

def run_meituan_checker_app():
    """运行美团邮件审核工具的 Streamlit 界面。"""
    st.title(f"美团邮件审核")
    st.markdown("""
    操，这个工具是用来帮你从美团的 `.eml` 邮件里抠出 `(JLG)` 号码，
    然后去你的**系统订单 Excel** 里找到对应的客人信息。
    1.  上传包含 `(JLG)` 号码的 `.eml` 文件 (可以一次传多个)。
    2.  上传你的**系统订单 Excel** 文件。
    3.  点“开始匹配”，老子就把结果给你列出来。
    """)

    col1, col2 = st.columns(2)
    with col1:
        uploaded_eml_files = st.file_uploader("上传美团 EML 邮件文件 (.eml)", type=["eml"], accept_multiple_files=True, key="meituan_eml_uploader")
    with col2:
        uploaded_system_excel = st.file_uploader("上传系统订单 Excel 文件 (.xlsx)", type=["xlsx"], key="meituan_system_uploader")

    if st.button("开始匹配", type="primary", disabled=(not uploaded_eml_files or not uploaded_system_excel)):
        if not uploaded_eml_files: st.warning("操，你他妈的还没上传 EML 文件呢！"); st.stop()
        if not uploaded_system_excel: st.warning("操，你他妈的还没上传系统订单 Excel 文件呢！"); st.stop()

        all_jlg_numbers, eml_parsing_errors = [], []
        with st.spinner("正在解析 EML 文件..."):
            for eml_file in uploaded_eml_files:
                try:
                    content_bytes = eml_file.getvalue()
                    eml_text = parse_eml(content_bytes)
                    if eml_text:
                        jlg_found = extract_jlg_numbers(eml_text)
                        if jlg_found: all_jlg_numbers.extend(jlg_found)
                        else: st.warning(f"文件 '{eml_file.name}' 中没有找到 `(JLG)` 号码。")
                    else: eml_parsing_errors.append(eml_file.name)
                except Exception as e:
                    st.error(f"处理文件 '{eml_file.name}' 时出错: {e}")
                    eml_parsing_errors.append(eml_file.name)
        if eml_parsing_errors: st.error(f"以下 EML 文件解析失败，已被跳过: {', '.join(eml_parsing_errors)}")

        unique_jlg_numbers = list(set(all_jlg_numbers))
        if not unique_jlg_numbers: st.error("操，所有上传的 EML 文件里都没找到有效的 `(JLG)` 号码！活儿没法干了。"); st.stop()
        st.info(f"从 EML 文件中成功提取到 {len(unique_jlg_numbers)} 个唯一的 JLG 号码。")

        try:
            # --- 操，强制把可能的列读成字符串，特别是'预订号'和'房号' ---
            possible_cols = MEITUAN_SYSTEM_COLUMN_MAP.get('预订号', []) + MEITUAN_SYSTEM_COLUMN_MAP.get('房号', [])
            dtype_map = {col: str for col in possible_cols} # 给所有可能的列名设置 dtype=str
            system_df = pd.read_excel(uploaded_system_excel, dtype=dtype_map)
            system_df.columns = system_df.columns.str.strip() # 清理列名中的空格
            missing_cols = find_and_rename_columns(system_df, MEITUAN_SYSTEM_COLUMN_MAP)
            if missing_cols: st.error(f"操！系统订单 Excel 文件里找不到必需的列: {', '.join(missing_cols)}。没法继续了。"); st.stop()
            if '预订号' not in system_df.columns: st.error(f"操！在系统订单 Excel 文件里找不到 '预订号' 列（或其别名）。"); st.stop()
            system_df['预订号'] = system_df['预订号'].astype(str).str.strip() # 再次确保是字符串并清理空白
        except Exception as e:
            st.error(f"读取或处理系统订单 Excel 文件时出错: {e}"); st.stop()

        results, found_count, not_found_jlg = [], 0, []
        with st.spinner("正在系统订单中匹配 JLG 号码..."):
            # 操，这是你新要的那几列, 但要先检查它们是不是真的存在于 system_df 里
            base_required_info_cols = ['姓名', '状态', '房号', '到达', '离开', '预订号']
            # --- 操，这里是改动点：只包括 system_df 里真实存在的列 ---
            cols_to_extract = [col for col in base_required_info_cols if col in system_df.columns]
            missing_extract_cols = [col for col in base_required_info_cols if col not in cols_to_extract]
            if missing_extract_cols: st.warning(f"系统订单中缺少以下列，结果中将不包含这些信息: {', '.join(missing_extract_cols)}")

            for jlg_number in unique_jlg_numbers:
                match = system_df[system_df['预订号'] == jlg_number.strip()]
                if not match.empty:
                    found_count += 1
                    match_data = match.iloc[0]
                    result_entry = {'JLG号码': jlg_number} # 操，把JLG号码也加进去，方便核对
                    for col in cols_to_extract: # 只处理实际存在的列
                         if col in ['到达', '离开'] and pd.notna(match_data[col]):
                             try: result_entry[col] = pd.to_datetime(match_data[col]).strftime('%Y-%m-%d')
                             except Exception: result_entry[col] = str(match_data[col]) # 日期格式不对就直接转字符串
                         # 操，状态列要特殊处理一下
                         elif col == '状态' and pd.notna(match_data[col]):
                             result_entry[col] = str(match_data[col]).strip().upper() # 原始状态码
                             result_entry['状态2'] = convert_status_to_status2(match_data[col]) # 中文状态
                         elif pd.notna(match_data[col]):
                             result_entry[col] = match_data[col]
                         else:
                             result_entry[col] = None # 如果是空的，就填 None

                    # 如果原始数据里就没有状态列，也给它加上空的状态2
                    if '状态' not in cols_to_extract:
                        result_entry['状态'] = None
                        result_entry['状态2'] = None

                    results.append(result_entry)
                else:
                    not_found_jlg.append(jlg_number)

        st.success(f"匹配完成！共找到 {found_count} 个匹配项。")

        if results:
            result_df = pd.DataFrame(results)
            # 操，按照你指定的傻逼顺序排好
            final_cols_order = ['姓名', '状态', '状态2', '房号', '到达', '离开', '预订号', 'JLG号码']
            # 只保留实际存在的列
            existing_final_cols = [col for col in final_cols_order if col in result_df.columns]
            result_df = result_df[existing_final_cols]

            st.dataframe(result_df.fillna('')) # 把空值显示为空字符串，好看点

            excel_data = to_excel({"美团匹配结果": result_df})
            st.download_button(label="📥 下载匹配结果 (.xlsx)", data=excel_data, file_name="meituan_match_results_updated.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download-meituan-results-upd")
        else:
            st.warning("在系统订单中没有找到任何与 EML 文件中 JLG 号码匹配的记录。")

        if not_found_jlg:
            st.warning(f"以下 {len(not_found_jlg)} 个 JLG 号码在系统订单中未找到匹配项:")
            st.text(", ".join(not_found_jlg))

