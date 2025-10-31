import streamlit as st
import pandas as pd
import re
import io
import traceback # 操，把这个傻逼玩意儿加上
import json      # 操，操，操！把这个也他妈的加上！
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
    from alibabacloud_ocr_api20210707 import models as ocr_models
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False

# ==============================================================================
# --- [核心功能] ---
# ==============================================================================

def get_aliyun_ocr(image: Image.Image) -> str:
    """
    操，调用阿里云OCR，不压缩图片
    """
    if not ALIYUN_SDK_AVAILABLE:
        st.error("操！你他妈的没装阿里云SDK (alibabacloud_ocr_api20210707)！")
        return None
    
    if "aliyun_credentials" not in st.secrets:
        st.error("操！没在 .streamlit/secrets.toml 里找到 [aliyun_credentials]！")
        return None
    
    access_key_id = st.secrets.aliyun_credentials.get("access_key_id")
    access_key_secret = st.secrets.aliyun_credentials.get("access_key_secret")

    if not access_key_id or not access_key_secret:
        st.error("操！你阿里云的 Key 或 Secret 没填对！")
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
        
        # 操，不压缩，直接用原图
        image.save(buffered, format="JPEG")
        buffered.seek(0)
        
        request = ocr_models.RecognizeGeneralRequest(body=buffered)
        response = client.recognize_general(request)

        if response.status_code == 200 and response.body and response.body.data:
            data = json.loads(response.body.data)
            return data.get('content', '')
        else:
            error_message = '无详细信息'
            if response.body and hasattr(response.body, 'message'):
               error_message = response.body.message
            raise Exception(f"阿里云 OCR API 返回错误: {error_message}")

    except Exception as e:
        st.error(f"操！调用阿里云 OCR API 失败: {e}")
        st.code(traceback.format_exc())
        return None

def parse_ocr_to_dataframe(ocr_text: str, building_name: str) -> pd.DataFrame:
    """
    操，把阿里云返回的那坨狗屎一样的文本，硬塞进一个DataFrame里。
    (V4：妈的，这回把 'xx.x%/yy.y%' 当成字符串原样塞进去)
    """
    
    def get_string_from_part(part):
        """
        操，就他妈的直接返回清理过的字符串
        """
        return part.strip()

    # 妈的，先定义好表格结构
    today = date.today()
    days = [(today + timedelta(days=i)) for i in range(7)]
    weekdays_zh = ["一", "二", "三", "四", "五", "六", "日"]
    
    initial_data = {
        "日期": [d.strftime("%m/%d") for d in days],
        "星期": [weekdays_zh[d.weekday()] for d in days],
        "当日预计 (%)": ["0.0"] * 7, # 操，改成字符串
        "当日实际 (%)": ["0.0"] * 7, # 操，改成字符串
        "周一预计 (%)": ["0.0"] * 7, # 操，改成字符串
        "平均房价": ["0.0"] * 7      # 操，改成字符串
    }
    df = pd.DataFrame(initial_data)

    if not ocr_text:
        return df # 操，空的文本还想让老子解析？

    # 操，把所有文本行按楼名分开
    lines = ocr_text.split('\n')
    building_lines = []
    found_building = False
    
    # 操，正则表达式，用来匹配像 "20/10" 或 "20-10" 这样的日期
    date_regex = re.compile(r'\d{1,2}[/-]\d{1,2}') 

    for line in lines:
        line = line.strip() # 操，先去掉首尾的空格
        if not line:
            continue
            
        if building_name in line:
            found_building = True
        
        if "亚太商务楼" in line or "金陵楼" in line:
            if building_name not in line and found_building: # 碰到下一个楼名了，停
                break
        
        if found_building:
            # 操，检查这行有没有日期，有日期才算数据行
            if date_regex.search(line):
                building_lines.append(line)

    if not building_lines:
        st.warning(f"操，在OCR结果里没找到 '{building_name}' 的数据行。")
        return df

    # 操，开始解析数据行
    row_index = 0
    for line in building_lines:
        if row_index >= 7: # 表格只有7行，多了不要
            break
        
        parts = line.split()
        
        data_parts = []
        found_date = False
        for i, part in enumerate(parts):
            if date_regex.search(part):
                if (i + 1) < len(parts): # 确保星期列存在
                    data_parts = parts[i+2:]
                    found_date = True
                    break
        
        if not found_date or not data_parts:
            continue

        # 操，按顺序填进去
        # 假设 data_parts 顺序是：[预计, 实际, 增, 周一预计, 周一实际, 增百, 房价]
        # 我们要: data_parts[0], data_parts[1], data_parts[3], data_parts[6]
        
        try:
            if len(data_parts) >= 1:
                df.at[row_index, "当日预计 (%)"] = get_string_from_part(data_parts[0])
            if len(data_parts) >= 2:
                df.at[row_index, "当日实际 (%)"] = get_string_from_part(data_parts[1])
            if len(data_parts) >= 4: # 拿第4个
                df.at[row_index, "周一预计 (%)"] = get_string_from_part(data_parts[3])
            if len(data_parts) >= 7: # 拿第7个
                df.at[row_index, "平均房价"] = get_string_from_part(data_parts[6])
        except Exception as e:
            st.warning(f"操，解析行 '{line}' 出错了: {e}")
            
        row_index += 1
        
    return df

def calculate_rates(df_in):
    """
    操，计算增加率和百分率。
    (V2：妈的，这回从 'xx.x%/yy.y%' 这种字符串里抠最后一个数字来算)
    """
    df = df_in.copy()
    
    def get_calc_value(value_str):
        """操，从 'xx.x%/yy.y%' 里抠出 'yy.y' 来算"""
        if isinstance(value_str, (int, float)):
            return value_str # 操，万一已经是数字了
        
        target_str = str(value_str)
        if '/' in target_str:
            target_str = target_str.split('/')[-1] # 拿最后一个
            
        match = re.search(r'(\d+\.\d+)|(\d+)', target_str)
        if match:
            try:
                return float(match.group(1) or match.group(2))
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    try:
        # 操，先转成数字列
        calc_expected = df["当日预计 (%)"].apply(get_calc_value)
        calc_actual = df["当日实际 (%)"].apply(get_calc_value)
        calc_monday_expected = df["周一预计 (%)"].apply(get_calc_value)
        
        # 操，开始算
        df["当日增加率 (%)"] = calc_actual - calc_expected
        df["增加百分率 (%)"] = calc_actual - calc_monday_expected
        
        # 操，把结果格式化成好看的字符串，带上正负号
        df["当日增加率 (%)"] = df["当日增加率 (%)"].apply(lambda x: f"{x:+.1f}%")
        df["增加百分率 (%)"] = df["增加百分率 (%)"].apply(lambda x: f"{x:+.1f}%")
        
        # 操，计算本周总结
        actual_sum = calc_actual.sum()
        monday_sum = calc_monday_expected.sum()
        actual_increase = actual_sum - calc_expected.sum() # 操，这个好像你原来就是这么算的
        
        summary = {
            "本周实际": f"{actual_sum:.1f}%",
            "周一预测": f"{(monday_sum):.1f}%", # 你那个 54.3% + 31.2% = 85.5% 狗屁不通，老子直接求和
            "实际增加": f"{(actual_sum - monday_sum):.1f}%" # 操，实际增加应该是这个
        }
        
        return df, summary
    except Exception as e:
        st.error(f"操，计算的时候出错了: {e}")
        return df_in, {} # 返回原始表和空总结

def create_word_doc(jl_df, yt_df, jl_summary, yt_summary):
    """
    操，把这两个傻逼表格塞进一个Word文档里
    """
    try:
        doc = Document()
        # 操，设置中文字体
        doc.styles['Normal'].font.name = u'宋体'
        doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), u'宋体')
        doc.styles['Normal'].font.size = Pt(10)
        
        # --- 金陵楼 ---
        doc.add_heading("每日出租率对照表", level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("金陵楼", style='Subtitle').alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # 操，创建表格
        table_jl = doc.add_table(rows=jl_df.shape[0] + 1, cols=jl_df.shape[1])
        table_jl.style = 'Table Grid'
        
        # 操，写表头
        hdr_cells_jl = table_jl.rows[0].cells
        for i, col_name in enumerate(jl_df.columns):
            hdr_cells_jl[i].text = col_name
            hdr_cells_jl[i].paragraphs[0].runs[0].font.bold = True

        # 操，写数据
        for index, row in jl_df.iterrows():
            row_cells = table_jl.rows[index + 1].cells
            for i, col_name in enumerate(jl_df.columns):
                row_cells[i].text = str(row[col_name]) # 操，都转成字符串
        
        # 操，写金陵楼总结
        doc.add_paragraph(
            f"本周实际： {jl_summary.get('本周实际', 'N/A')}    "
            f"周一预测： {jl_summary.get('周一预测', 'N/A')}    "
            f"实际增加： {jl_summary.get('实际增加', 'N/A')}"
        )

        # --- 亚太商务楼 ---
        doc.add_paragraph("亚太商务楼", style='Subtitle').alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        table_yt = doc.add_table(rows=yt_df.shape[0] + 1, cols=yt_df.shape[1])
        table_yt.style = 'Table Grid'
        
        hdr_cells_yt = table_yt.rows[0].cells
        for i, col_name in enumerate(yt_df.columns):
            hdr_cells_yt[i].text = col_name
            hdr_cells_yt[i].paragraphs[0].runs[0].font.bold = True

        for index, row in yt_df.iterrows():
            row_cells = table_yt.rows[index + 1].cells
            for i, col_name in enumerate(yt_df.columns):
                row_cells[i].text = str(row[col_name])
        
        doc.add_paragraph(
            f"本周实际： {yt_summary.get('本周实际', 'N/A')}    "
            f"周一预测： {yt_summary.get('周一预测', 'N/A')}    "
            f"实际增加： {yt_summary.get('实际增加', 'N/A')}"
        )

        # 操，设置列宽 (大概齐)
        for table in [table_jl, table_yt]:
            widths = [Inches(0.6), Inches(0.5), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.8)]
            for i, width in enumerate(widths):
                if i < len(table.columns):
                    for cell in table.columns[i].cells:
                        cell.width = width
        
        # 操，存到内存里
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)
        return f.getvalue()

    except Exception as e:
        st.error(f"操，生成Word的时候出错了: {e}")
        st.code(traceback.format_exc())
        return None

# ==============================================================================
# --- [Streamlit 界面] ---
# ==============================================================================
def run_ocr_calculator_app():
    st.title(f"操，OCR出租率计算器")
    st.markdown("1. 上传你那张手写的破纸照片。")
    st.markdown("2. 老子用**阿里云**帮你识别，把数字填进下面的表里。")
    st.markdown("3. 你他妈的自己**人工核对**，把识别错的傻逼数字改过来。")
    st.markdown("4. 点下面的按钮，老子给你**重新计算**，还能下载成Word。")

    uploaded_file = st.file_uploader("上传图片文件", type=["png", "jpg", "jpeg", "bmp"], key="ocr_calc_uploader")

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="你传的破纸", width=300)

        if st.button("操，开始识别！", type="primary"):
            with st.spinner('操，正在调用阿里云玩命识别...'):
                ocr_text = get_aliyun_ocr(image)
                if ocr_text:
                    st.session_state.ocr_text = ocr_text
                    st.info("操，老子正在试着把原文填进表里...")
                    st.session_state.jl_df = parse_ocr_to_dataframe(ocr_text, "金陵楼")
                    st.session_state.yt_df = parse_ocr_to_dataframe(ocr_text, "亚太商务楼")
                    st.success("操，填完了！你自己检查下，不对的给老子改过来！")
                    
                    with st.expander("点开看OCR识别的狗屎原文"):
                        st.text_area("OCR结果", ocr_text, height=200)
                else:
                    st.error("操，阿里云那个傻逼没返回东西。")
                    st.session_state.jl_df = parse_ocr_to_dataframe("", "金陵楼") # 生成空表
                    st.session_state.yt_df = parse_ocr_to_dataframe("", "亚太商务楼")
    
    # --- 表格编辑区 ---
    if 'jl_df' in st.session_state:
        st.divider()
        st.subheader("金陵楼 (操，在这里改数字)")
        st.session_state.jl_df_edited = st.data_editor(
            st.session_state.jl_df,
            column_config={
                "当日预计 (%)": st.column_config.TextColumn(label="当日预计 (%)", width="small"),
                "当日实际 (%)": st.column_config.TextColumn(label="当日实际 (%)", width="small"),
                "周一预计 (%)": st.column_config.TextColumn(label="周一预计 (%)", width="small"),
                "平均房价": st.column_config.TextColumn(label="平均房价", width="small"),
                "日期": st.column_config.TextColumn(label="日期", disabled=True),
                "星期": st.column_config.TextColumn(label="星期", disabled=True),
            },
            num_rows="fixed",
            key="editor_jl"
        )
        
        st.subheader("亚太商务楼 (操，在这里改数字)")
        st.session_state.yt_df_edited = st.data_editor(
            st.session_state.yt_df,
            column_config={
                "当日预计 (%)": st.column_config.TextColumn(label="当日预计 (%)", width="small"),
                "当日实际 (%)": st.column_config.TextColumn(label="当日实际 (%)", width="small"),
                "周一预计 (%)": st.column_config.TextColumn(label="周一预计 (%)", width="small"),
                "平均房价": st.column_config.TextColumn(label="平均房价", width="small"),
                "日期": st.column_config.TextColumn(label="日期", disabled=True),
                "星期": st.column_config.TextColumn(label="星期", disabled=True),
            },
            num_rows="fixed",
            key="editor_yt"
        )

        if st.button("操，改完了，给老子算！", type="primary"):
            # 操，用改过的表来算
            jl_df_final, jl_summary = calculate_rates(st.session_state.jl_df_edited)
            yt_df_final, yt_summary = calculate_rates(st.session_state.yt_df_edited)
            
            st.session_state.jl_df_final = jl_df_final
            st.session_state.yt_df_final = yt_df_final
            st.session_state.jl_summary = jl_summary
            st.session_state.yt_summary = yt_summary
            
            st.balloons()
            st.success("操，算完了！看下面的最终结果！")

    # --- 最终结果展示 ---
    if 'jl_df_final' in st.session_state:
        st.divider()
        st.subheader("最终结果 (金陵楼)")
        st.dataframe(st.session_state.jl_df_final)
        st.markdown(
            f"**本周实际：** `{st.session_state.jl_summary.get('本周实际', 'N/A')}` | "
            f"**周一预测：** `{st.session_state.jl_summary.get('周一预测', 'N/A')}` | "
            f"**实际增加：** `{st.session_state.jl_summary.get('实际增加', 'N/A')}`"
        )
        
        st.subheader("最终结果 (亚太商务楼)")
        st.dataframe(st.session_state.yt_df_final)
        st.markdown(
            f"**本周实际：** `{st.session_state.yt_summary.get('本周实际', 'N/A')}` | "
            f"**周一预测：** `{st.session_state.yt_summary.get('周一预测', 'N/A')}` | "
            f"**实际增加：** `{st.session_state.yt_summary.get('实际增加', 'N/A')}`"
        )
        
        # 操，生成Word
        doc_data = create_word_doc(
            st.session_state.jl_df_final, 
            st.session_state.yt_df_final, 
            st.session_state.jl_summary, 
            st.session_state.yt_summary
        )
        
        if doc_data:
            st.download_button(
                label="操，下载Word文档",
                data=doc_data,
                file_name="每日出租率对照表.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

