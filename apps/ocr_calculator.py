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

# --- SDK 依赖 ---
try:
    from alibabacloud_ocr_api20210707.client import Client as OcrClient
    from alibabacloud_tea_openapi import models as open_api_models
    # 导入 Table Recognize (表格识别) 模型
    from alibabacloud_ocr_api20210707 import models as ocr_models
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False

# ==============================================================================
# --- [核心功能 V2: 表格识别] ---
# ==============================================================================

def get_aliyun_table_ocr(image: Image.Image) -> dict:
    """
    调用阿里云 【表格识别】 (RecognizeTable) API。
    这个API会返回一个结构化的JSON，而不仅仅是纯文本。
    """
    if not ALIYUN_SDK_AVAILABLE:
        st.error("错误：未找到阿里云SDK (alibabacloud_ocr_api20210707)！")
        return None
    
    if "aliyun_credentials" not in st.secrets:
        st.error("错误：未在 .streamlit/secrets.toml 中找到 [aliyun_credentials] 配置！")
        return None
    
    access_key_id = st.secrets.aliyun_credentials.get("access_key_id")
    access_key_secret = st.secrets.aliyun_credentials.get("access_key_secret")

    if not access_key_id or not access_key_secret:
        st.error("错误：阿里云 AccessKeyId 或 AccessKeySecret 未配置！")
        return None

    try:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint='ocr-api.cn-hangzhou.aliyuncs.com'
        )
        client = OcrClient(config)

        buffered = io.BytesIO()
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # 使用JPEG格式保存到内存
        image.save(buffered, format="JPEG")
        buffered.seek(0)
        
        # 1. 创建 RecognizeTableRequest
        # 我们请求JSON格式的输出
        request = ocr_models.RecognizeTableRequest(
            body=buffered,
            output_format="json"
        )
        
        # 2. 调用 recognize_table 方法
        st.write("正在调用阿里云【表格识别】API...")
        response = client.recognize_table(request)
        st.write("API 调用完成。")

        if response.status_code == 200 and response.body and response.body.data:
            # 3. 解析返回的JSON数据
            data = json.loads(response.body.data)
            return data
        else:
            error_message = '无详细信息'
            if response.body and hasattr(response.body, 'message'):
                error_message = response.body.message
            raise Exception(f"阿里云 表格识别 API 返回错误: {error_message}")

    except Exception as e:
        st.error(f"调用阿里云 表格识别 API 失败: {e}")
        st.code(traceback.format_exc())
        return None

def parse_table_ocr_to_dataframe(ocr_data: dict, building_name: str) -> pd.DataFrame:
    """
    V2: 解析 RecognizeTable API 返回的结构化 JSON 数据并填充 DataFrame。
    """
    
    # 1. 准备一个空的默认DataFrame，结构和以前一样
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

    if not ocr_data or 'tables' not in ocr_data:
        st.warning("OCR结果为空或未识别到'tables'结构。")
        return df

    # 2. 查找包含 building_name (例如 '金陵楼') 的表格
    target_table = None
    for table in ocr_data.get('tables', []):
        for cell in table.get('cells', []):
            if building_name in cell.get('text', ''):
                target_table = table
                break
        if target_table:
            break

    if not target_table:
        st.warning(f"在OCR结果中未找到包含 '{building_name}' 的表格。")
        return df

    # 3. 找到表格后，解析数据行
    # 假设表格结构是：[日期, 星期, 预计, 实际, 增, 周一预计, 周一实际, 增百, 房价]
    # 对应的列索引(col_index)是: 0, 1, 2, 3, 4, 5, 6, 7, 8
    
    # 我们需要填充的列
    COLUMN_MAPPING = {
        2: "当日预计 (%)",  # 第3列表格
        3: "当日实际 (%)",  # 第4列表格
        5: "周一预计 (%)",  # 第6列表格
        8: "平均房价"      # 第9列表格
    }
    
    # 用于匹配数据行第一列 (日期) 的正则表达式
    date_regex = re.compile(r'\d{1,2}[/-]\d{1,2}') 
    
    # 记录我们填充到了DataFrame的第几行
    df_row_index = 0
    
    # 遍历表格的所有单元格
    cells = sorted(target_table.get('cells', []), key=lambda c: (c['row_index'], c['col_index']))
    
    current_table_row = -1
    
    for cell in cells:
        row_idx = cell['row_index']
        col_idx = cell['col_index']
        text = cell.get('text', '').strip()

        # 这是一个新行
        if row_idx != current_table_row:
            current_table_row = row_idx
            # 检查这是不是一个数据行 (通过检查第0列是否是日期)
            if col_idx == 0 and date_regex.search(text):
                # 这是一个数据行
                pass
            else:
                # 这不是数据行 (可能是表头, 或者是 '金陵楼' 那一行), 跳过这一整行
                current_table_row = -1 # 标记为无效，直到找到下一个日期行
                continue
        
        # 如果我们正在一个有效的数据行里
        if current_table_row != -1:
            if df_row_index >= 7:
                break # DataFrame 已经填满了
            
            # 检查这个单元格是不是我们需要的列
            if col_idx in COLUMN_MAPPING:
                column_name = COLUMN_MAPPING[col_idx]
                df.at[df_row_index, column_name] = text
        
        # 检查是否该换到DataFrame的下一行
        # (假设 '平均房价' 是表格的最后一列，col_index 8)
        if col_idx == 8 and current_table_row != -1:
            df_row_index += 1

    return df

# ==============================================================================
# --- [核心功能 V1: 计算和Word生成] ---
# (这部分代码和V1完全一样，因为它们只依赖DataFrame)
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
        doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), u'宋体')
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
# --- [Streamlit 界面] ---
# ==============================================================================
def run_ocr_calculator_app():
    st.title("OCR出租率计算器 (V2 - 表格识别版)")
    st.markdown("1. 上传手写表格的照片。")
    st.markdown("2. 使用**阿里云表格识别API**，智能解析表格并填充。")
    st.markdown("3. **人工核对**下方的可编辑表格，修正识别错误的数字。")
    st.markdown("4. 点击“计算”按钮，生成最终报表并下载Word文档。")

    uploaded_file = st.file_uploader("上传图片文件", type=["png", "jpg", "jpeg", "bmp"], key="ocr_calc_uploader_v2")

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的图片", width=300)

        if st.button("开始识别 (表格模式)", type="primary"):
            with st.spinner('正在调用阿里云【表格识别】API...'):
                ocr_data = get_aliyun_table_ocr(image)
                
                if ocr_data:
                    st.session_state.ocr_data = ocr_data
                    st.info("API调用成功，正在解析返回的表格JSON...")
                    st.session_state.jl_df = parse_table_ocr_to_dataframe(ocr_data, "金陵楼")
                    st.session_state.yt_df = parse_table_ocr_to_dataframe(ocr_data, "亚太商务楼")
                    st.success("解析完成！请检查下面的表格，手动修正错误。")
                    
                    with st.expander("查看阿里云返回的原始JSON数据"):
                        st.json(ocr_data)
                else:
                    st.error("表格识别API未返回有效数据。")
                    st.session_state.jl_df = parse_table_ocr_to_dataframe(None, "金陵楼") # 生成空表
                    st.session_state.yt_df = parse_table_ocr_to_dataframe(None, "亚太商务楼")
    
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
            key="editor_jl_v2"
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
            key="editor_yt_v2"
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
                file_name="每日出租率对照表_V2.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# --- 主程序入口 ---
if __name__ == "__main__":
    # 设置页面标题
    st.set_page_config(page_title="OCR出租率计算器 V2")
    run_ocr_calculator_app()
