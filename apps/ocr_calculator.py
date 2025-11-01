import streamlit as st
import pandas as pd
import re
import io
import traceback
import json
from PIL import Image
from datetime import date, timedelta
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# --- 新增 V5 依赖 (Alibaba Cloud) ---
try:
    from alibabacloud_ocr_api20210707.client import Client as OcrClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_ocr_api20210707 import models as ocr_models
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False
    # 在UI中会显示错误

# --- 移除 V4 依赖 (OpenAI) ---
# from openai import OpenAI
# import base64

# ==============================================================================
# --- [核心功能 V5: Alibaba Cloud General OCR] ---
# ==============================================================================

def get_aliyun_ocr(image: Image.Image) -> str:
    """
    V5: 调用阿里云通用文字识别 (RecognizeGeneral)，并从 st.secrets 读取密钥。
    """
    st.write("正在调用 Alibaba Cloud General OCR API...")
    
    if not ALIYUN_SDK_AVAILABLE:
        st.error("错误：你没有安装阿里云SDK！请运行: pip install alibabacloud_ocr_api20210707")
        return None
    
    # 1. 从 st.secrets 读取密钥 (*** V5 修改 ***)
    try:
        access_key_id = st.secrets["aliyun"]["access_key_id"]
        access_key_secret = st.secrets["aliyun"]["access_key_secret"]
    except (KeyError, AttributeError):
        st.error("错误：没在 .streamlit/secrets.toml 里找到 [aliyun] -> access_key_id 或 access_key_secret！")
        st.code("请在 .streamlit/secrets.toml 文件中添加：\n\n[aliyun]\naccess_key_id = \"YOUR_KEY_ID\"\naccess_key_secret = \"YOUR_KEY_SECRET\"\n")
        return None

    if not access_key_id or not access_key_secret:
        st.error("错误：你 .streamlit/secrets.toml 里的阿里云密钥是空的！")
        return None

    # 2. 初始化客户端
    try:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint='ocr-api.cn-hangzhou.aliyuncs.com'
        )
        client = OcrClient(config)
    except Exception as e:
        st.error(f"初始化阿里云客户端失败: {e}")
        return None
        
    # 3. 准备图片
    buffered = io.BytesIO()
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    
    # 不压缩，使用高质量
    image.save(buffered, format="JPEG", quality=95)
    buffered.seek(0)
    
    # 4. 发起请求
    request = ocr_models.RecognizeGeneralRequest(body=buffered)
    
    try:
        response = client.recognize_general(request)

        if response.status_code == 200 and response.body and response.body.data:
            data = json.loads(response.body.data)
            content = data.get('content', '')
            if content:
                st.write("API 调用成功，获取到文本内容。")
                return content
            else:
                st.error("阿里云 OCR API 返回了空内容。")
                st.json(data) # 显示返回的JSON
                return None
        else:
            error_message = '无详细信息'
            if response.body and hasattr(response.body, 'message'):
                error_message = response.body.message
            elif response.body:
                error_message = str(response.body)
            st.error(f"阿里云 OCR API 返回错误 (Code: {response.status_code}): {error_message}")
            return None

    except Exception as e:
        st.error(f"调用阿里云 OCR API 失败: {e}")
        st.code(traceback.format_exc())
        return None

def parse_ocr_to_dataframe(ocr_text: str, building_name: str) -> pd.DataFrame:
    """
    V5: 恢复使用V1的稳健的文本行解析器。
    它处理由 RecognizeGeneral 返回的单个文本块。
    """
    
    # 1. 准备一个空的默认DataFrame
    today = date.today()
    days = [(today + timedelta(days=i)) for i in range(7)]
    weekdays_zh_map = ["一", "二", "三", "四", "五", "六", "日"]
    
    initial_data = {
        "日期": [d.strftime("%m/%d") for d in days],
        "星期": [weekdays_zh_map[d.weekday()] for d in days],
        "当日预计 (%)": ["0.0"] * 7,
        "当日实际 (%)": ["0.0"] * 7,
        "周一预计 (%)": ["0.0"] * 7,
        "平均房价": ["0.0"] * 7
    }
    df = pd.DataFrame(initial_data)

    if not ocr_text:
        st.warning("OCR 文本为空，无法解析。")
        return df

    lines = ocr_text.split('\n')
    building_lines = []
    found_building = False
    
    other_building = "亚太商务楼" if building_name == "金陵楼" else "金陵楼"
    # 日期正则, 匹配 '20/10' 或 '20-10'
    date_regex = re.compile(r'\d{1,2}[/-]\d{1,2}') 

    # 2. 从文本块中分离出属于本楼的数据行
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if building_name in line:
            found_building = True
            continue # 这是标题行，跳过
        
        # 如果找到了另一栋楼，就停止
        if other_building in line and building_name not in line:
            found_building = False
            break 
        
        if found_building:
            # 关键：只处理包含日期的行
            if date_regex.search(line):
                building_lines.append(line)

    if not building_lines:
        st.warning(f"在OCR结果中未找到 '{building_name}' 的有效数据行。")
        return df

    # 3. 解析数据行
    row_index = 0
    for line in building_lines:
        if row_index >= 7: # 最多7行
            break
        
        parts = line.split()
        data_parts = []
        
        # 找到数据开始的位置 (日期之后)
        found_data_start = False
        for i, part in enumerate(parts):
            if date_regex.search(part):
                # 找到了日期, 检查下一个是不是星期
                if (i + 1) < len(parts) and parts[i+1] in weekdays_zh_map:
                    # 是星期, 数据从 i+2 开始
                    data_parts = parts[i+2:]
                else:
                    # 不是星期 (OCR漏了), 数据从 i+1 开始
                    data_parts = parts[i+1:]
                found_data_start = True
                break
        
        if not found_data_start:
            # st.warning(f"跳过行 (未找到数据): {line}") # 这条警告太吵了
            continue

        # 4. 填充DataFrame (基于V1的硬编码索引)
        # 假设顺序: [预计, 实际, 增, 周一预计, 周一实际, 增百, 房价]
        try:
            if len(data_parts) >= 1:
                df.at[row_index, "当日预计 (%)"] = data_parts[0]
            if len(data_parts) >= 2:
                df.at[row_index, "当日实际 (%)"] = data_parts[1]
            # data_parts[2] (当日增加率) - 忽略
            if len(data_parts) >= 4:
                df.at[row_index, "周一预计 (%)"] = data_parts[3]
            # data_parts[4], data_parts[5] - 忽略
            if len(data_parts) >= 7:
                # 房价可能是第7个 (data_parts[6])
                df.at[row_index, "平均房价"] = data_parts[6]
            
            # 覆盖日期 (使用OCR识别到的)
            date_match = date_regex.search(line)
            if date_match:
                df.at[row_index, "日期"] = date_match.group(0).replace('-', '/')
            
        except IndexError:
            st.warning(f"解析数据行 '{line}' 时索引越界，数据可能不完整。")
        except Exception as e:
            st.error(f"解析数据行 '{line}' 时发生意外错误: {e}")
        
        row_index += 1
        
    st.write(f"成功从Alibaba OCR文本中解析了 '{building_name}' 的 {row_index} 行数据。")
    return df

# ==============================================================================
# --- [核心功能 V1: 计算和Word生成] ---
# (这部分代码和V1/V4完全一样，因为它们只依赖DataFrame)
# ==============================================================================

def get_calc_value(value_str):
    """
    辅助函数：从 'xx.x%/yy.y%' 或 'xx.x' 字符串中提取用于计算的最后一个浮点数。
    """
    if isinstance(value_str, (int, float)):
        return value_str
    
    target_str = str(value_str)
    if '/' in target_str:
        target_str = target_str.split('/')[-1] # 取 '/' 后的部分
        
    # 清理常见的非数字字符
    target_str = target_str.replace('%', '').replace('i', '').strip()
        
    match = re.search(r'(\d+\.\d+)|(\d+)', target_str)
    if match:
        try:
            return float(match.group(1) or match.group(2))
        except (ValueError, TypeError):
            return 0.0
    return 0.0

def calculate_rates(df_in):
    """
    使用提取的浮点数计算“当日增加率”和“增加百分率”。
    """
    df = df_in.copy()
    
    try:
        # 1. 提取用于计算的浮点数列
        calc_expected = df["当日预计 (%)"].apply(get_calc_value)
        calc_actual = df["当日实际 (%)"].apply(get_calc_value)
        calc_monday_expected = df["周一预计 (%)"].apply(get_calc_value)
        
        # 2. 计算增加率
        df["当日增加率 (%)"] = calc_actual - calc_expected
        df["增加百分率 (%)"] = calc_actual - calc_monday_expected
        
        # 3. 格式化为带正负号的字符串
        df["当日增加率 (%)"] = df["当日增加率 (%)"].apply(lambda x: f"{x:+.1f}%")
        df["增加百分率 (%)"] = df["增加百分率 (%)"].apply(lambda x: f"{x:+.1f}%")
        
        # 4. 计算本周总结
        actual_sum = calc_actual.sum()
        monday_sum = calc_monday_expected.sum()
        
        summary = {
            "本周实际": f"{actual_sum:.1f}%",
            "周一预测": f"{monday_sum:.1f}%",
            "实际增加": f"{(actual_sum - monday_sum):+.1f}%" # 使用带符号的格式
        }
        
        return df, summary
    except Exception as e:
        st.error(f"计算比率时出错: {e}")
        st.code(traceback.format_exc())
        return df_in, {} # 返回原始表和空总结

def create_word_doc(jl_df, yt_df, jl_summary, yt_summary):
    """
    将两个DataFrame和它们的总结数据生成一个Word文档。
    """
    try:
        doc = Document()
        # 设置中文字体
        doc.styles['Normal'].font.name = u'宋体'
        doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), u'宋体' )
        doc.styles['Normal'].font.size = Pt(10)
        
        # --- 金陵楼 ---
        doc.add_heading("每日出租率对照表", level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("金陵楼", style='Subtitle').alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # 调整列顺序以匹配原始表格
        jl_cols_ordered = ["日期", "星期", "当日预计 (%)", "当日实际 (%)", "当日增加率 (%)", "周一预计 (%)", "增加百分率 (%)", "平均房价"]
        jl_df_ordered = jl_df[jl_cols_ordered]

        table_jl = doc.add_table(rows=jl_df_ordered.shape[0] + 1, cols=jl_df_ordered.shape[1])
        table_jl.style = 'Table Grid'
        
        # 写表头
        hdr_cells_jl = table_jl.rows[0].cells
        for i, col_name in enumerate(jl_df_ordered.columns):
            hdr_cells_jl[i].text = col_name
            hdr_cells_jl[i].paragraphs[0].runs[0].font.bold = True

        # 写数据
        for index, row in jl_df_ordered.iterrows():
            row_cells = table_jl.rows[index + 1].cells
            for i, col_name in enumerate(jl_df_ordered.columns):
                row_cells[i].text = str(row[col_name])
        
        # 写金陵楼总结
        doc.add_paragraph(
            f"本周实际： {jl_summary.get('本周实际', 'N/A')}     "
            f"周一预测： {jl_summary.get('周一预测', 'N/A')}     "
            f"实际增加： {jl_summary.get('实际增加', 'N/A')}"
        )

        # --- 亚太商务楼 ---
        doc.add_paragraph("亚太商务楼", style='Subtitle').alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        yt_cols_ordered = ["日期", "星期", "当日预计 (%)", "当日实际 (%)", "当日增加率 (%)", "周一预计 (%)", "增加百分率 (%)", "平均房价"]
        yt_df_ordered = yt_df[yt_cols_ordered]

        table_yt = doc.add_table(rows=yt_df_ordered.shape[0] + 1, cols=yt_df_ordered.shape[1])
        table_yt.style = 'Table Grid'
        
        hdr_cells_yt = table_yt.rows[0].cells
        for i, col_name in enumerate(yt_df_ordered.columns):
            hdr_cells_yt[i].text = col_name
            hdr_cells_yt[i].paragraphs[0].runs[0].font.bold = True

        for index, row in yt_df_ordered.iterrows():
            row_cells = table_yt.rows[index + 1].cells
            for i, col_name in enumerate(yt_df_ordered.columns):
                row_cells[i].text = str(row[col_name])
        
        doc.add_paragraph(
            f"本周实际： {yt_summary.get('本周实际', 'N/A')}     "
            f"周一预测： {yt_summary.get('周一预测', 'N/A')}     "
            f"实际增加： {yt_summary.get('实际增加', 'N/A')}"
        )

        # 设置列宽
        widths = [Inches(0.6), Inches(0.5), Inches(0.8), Inches(1.0), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.8)]
        for table in [table_jl, table_yt]:
            for i, width in enumerate(widths):
                if i < len(table.columns):
                    for cell in table.columns[i].cells:
                        cell.width = width
        
        # 存到内存
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)
        return f.getvalue()

    except Exception as e:
        st.error(f"生成Word文档时出错: {e}")
        st.code(traceback.format_exc())
        return None

# ==============================================================================
# --- [Streamlit 界面 V5] ---
# ==============================================================================
def run_ocr_calculator_app():
    st.title("OCR出租率计算器 (V5 - Alibaba Cloud)")
    st.markdown("1. 上传手写表格的照片。")
    st.markdown("2. 使用 **Alibaba Cloud 通用识别 API** 解析表格。")
    st.markdown("3. **人工核对**下方的可编辑表格，修正识别错误的数字。")
    st.markdown("4. 点击“计算”按钮，生成最终报表并下载Word文档。")

    uploaded_file = st.file_uploader("上传图片文件", type=["png", "jpg", "jpeg", "bmp"], key="ocr_calc_uploader_v5") # 新Key

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的图片", width=300)

        if st.button("开始识别 (Alibaba OCR)", type="primary"): # 新按钮
            if not ALIYUN_SDK_AVAILABLE:
                st.error("错误：阿里云SDK未安装。请在 requirements.txt 中添加 alibabacloud_ocr_api20210707")
            else:
                with st.spinner('正在调用 Alibaba Cloud OCR API...'):
                    
                    try:
                        ocr_text = get_aliyun_ocr(image)
                    except Exception as e:
                        st.error(f"运行Alibaba OCR任务时出错: {e}")
                        ocr_text = None
                    
                    if ocr_text:
                        st.session_state.ocr_text = ocr_text
                        st.info("API调用成功，正在解析返回的文本...")
                        
                        st.session_state.jl_df = parse_ocr_to_dataframe(ocr_text, "金陵楼")
                        st.session_state.yt_df = parse_ocr_to_dataframe(ocr_text, "亚太商务楼")
                        st.success("解析完成！请检查下面的表格，手动修正错误。")
                        
                        with st.expander("查看 Alibaba OCR 返回的原始文本"):
                            st.text_area("OCR 纯文本结果", ocr_text, height=300)
                    else:
                        st.error("Alibaba OCR API 未返回有效文本数据。")
                        st.session_state.jl_df = parse_ocr_to_dataframe(None, "金陵楼") # 生成空表
                        st.session_state.yt_df = parse_ocr_to_dataframe(None, "亚太商务楼")
    
    # --- 表格编辑区 ---
    if 'jl_df' in st.session_state:
        st.divider()
        st.subheader("金陵楼 (请在此处编辑)")
        st.session_state.jl_df_edited = st.data_editor(
            st.session_state.jl_df,
            column_config={
                "当日预计 (%)": st.column_config.TextColumn(label="当日预计 (%)", width="small"),
                "当日实际 (%)": st.column_config.TextColumn(label="当日实际 (%)", width="medium"),
                "周一预计 (%)": st.column_config.TextColumn(label="周一预计 (%)", width="small"),
                "平均房价": st.column_config.TextColumn(label="平均房价", width="small"),
                "日期": st.column_config.TextColumn(label="日期", disabled=True),
                "星期": st.column_config.TextColumn(label="星期", disabled=True),
            },
            num_rows="fixed",
            key="editor_jl_v5" # 新Key
        )
        
        st.subheader("亚太商务楼 (请在此处编辑)")
        st.session_state.yt_df_edited = st.data_editor(
            st.session_state.yt_df,
            column_config={
                "当日预计 (%)": st.column_config.TextColumn(label="当日预计 (%)", width="small"),
                "当日实际 (%)": st.column_config.TextColumn(label="当日实际 (%)", width="medium"),
                "周一预计 (%)": st.column_config.TextColumn(label="周一预计 (%)", width="small"),
                "平均房价": st.column_config.TextColumn(label="平均房价", width="small"),
                "日期": st.column_config.TextColumn(label="日期", disabled=True),
                "星期": st.column_config.TextColumn(label="星期", disabled=True),
            },
            num_rows="fixed",
            key="editor_yt_v5" # 新Key
        )

        if st.button("重新计算最终结果", type="primary"):
            # 使用编辑后的数据进行计算
            jl_df_final, jl_summary = calculate_rates(st.session_state.jl_df_edited)
            yt_df_final, yt_summary = calculate_rates(st.session_state.yt_df_edited)
            
            st.session_state.jl_df_final = jl_df_final
            st.session_state.yt_df_final = yt_df_final
            st.session_state.jl_summary = jl_summary
            st.session_state.yt_summary = yt_summary
            
            st.balloons()
            st.success("计算完成！")

    # --- 最终结果展示 ---
    if 'jl_df_final' in st.session_state:
        st.divider()
        st.subheader("最终结果 (金陵楼)")
        
        # 辅助函数，用于安全格式化
        def format_price(x):
            val = get_calc_value(x)
            return f"{val:.2f}" if val is not None else "0.00"

        st.dataframe(st.session_state.jl_df_final.style.format({
           "平均房价": format_price
        }))
        st.markdown(
            f"**本周实际：** `{st.session_state.jl_summary.get('本周实际', 'N/A')}` | "
            f"**周一预测：** `{st.session_state.jl_summary.get('周一预测', 'N/A')}` | "
            f"**实际增加：** `{st.session_state.jl_summary.get('实际增加', 'N/A')}`"
        )
        
        st.subheader("最终结果 (亚太商务楼)")
        st.dataframe(st.session_state.yt_df_final.style.format({
            "平均房价": format_price
        }))
        st.markdown(
            f"**本周实际：** `{st.session_state.yt_summary.get('本周实际', 'N/A')}` | "
            f"**周一预测：** `{st.session_state.yt_summary.get('周一预测', 'N/A')}` | "
            f"**实际增加：** `{st.session_state.yt_summary.get('实际增加', 'N/A')}`"
        )
        
        # 生成Word
        doc_data = create_word_doc(
            st.session_state.jl_df_final, 
            st.session_state.yt_df_final, 
            st.session_state.jl_summary, 
            st.session_state.yt_summary
        )
        
        if doc_data:
            st.download_button(
                label="下载Word文档",
                data=doc_data,
                file_name="每日出租率对照表_V5_Alibaba.docx", # 新文件名
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# --- 主程序入口 ---
if __name__ == "__main__":
    # 设置页面标题
    st.set_page_config(page_title="OCR出租率计算器 V5")
    run_ocr_calculator_app()

