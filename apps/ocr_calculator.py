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
    操，调用阿里云OCR识别图片中的文字。
    注意：这个函数不压缩图片，直接用原图上！
    """
    if not ALIYUN_SDK_AVAILABLE:
        st.error("操！阿里云 SDK 没装上，你让老子怎么识别？")
        return None
    if "aliyun_credentials" not in st.secrets:
        st.error("操！你他妈的还没在 .streamlit/secrets.toml 里配阿里云 Key！")
        return None
    
    access_key_id = st.secrets.aliyun_credentials.get("access_key_id")
    access_key_secret = st.secrets.aliyun_credentials.get("access_key_secret")
    
    if not access_key_id or not access_key_secret:
        st.error("操！阿里云 Key ID 或 Secret 没配对！")
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
        
        # 操，不压缩，直接用高质量JPEG怼上去
        image.save(buffered, format="JPEG", quality=95)
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
    """
    # 妈的，先定义好表格结构
    today = date.today()
    days = [(today + timedelta(days=i)) for i in range(7)]
    weekdays_zh = ["一", "二", "三", "四", "五", "六", "日"]
    
    initial_data = {
        "日期": [d.strftime("%m/%d") for d in days],
        "星期": [weekdays_zh[d.weekday()] for d in days],
        "当日预计 (%)": [0.0] * 7,
        "当日实际 (%)": [0.0] * 7,
        "周一预计 (%)": [0.0] * 7,
        "平均房价": [0.0] * 7
    }
    df = pd.DataFrame(initial_data)

    if not ocr_text:
        return df # 操，空的文本还想让老子解析？

    # 操，把所有文本行按楼名分开
    lines = ocr_text.split('\n')
    building_lines = []
    found_building = False
    
    for line in lines:
        if building_name in line:
            found_building = True
            continue
        if "亚太商务楼" in line or "金陵楼" in line:
            if found_building: # 碰到下一个楼名了，停
                break
        
        if found_building:
            building_lines.append(line)

    if not building_lines:
        st.warning(f"操，在OCR结果里没找到 '{building_name}' 的数据。")
        return df

    # 操，开始解析数据行
    row_index = 0
    for line in building_lines:
        if row_index >= 7: # 表格只有7行，多了不要
            break
        
        # 妈的，用最简单的正则，把所有像数字和百分号的都抠出来
        # 匹配 "xx.x%" "xx.x" "xxxx" 这种
        numbers = re.findall(r'(\d+\.\d+)%?|(\d+)', line)
        
        # numbers 会是 [('78.4', ''), ('81.2', ''), ('6.5', ''), ('84.9', ''), ('6.5', ''), ('5774', '')] 这种狗屎
        cleaned_numbers = []
        for num_tuple in numbers:
            num_str = num_tuple[0] if num_tuple[0] else num_tuple[1]
            try:
                cleaned_numbers.append(float(num_str))
            except ValueError:
                pass # 操，转不成数字的滚蛋
        
        # st.write(f"调试: 行 '{line}' -> 抠出: {cleaned_numbers}") # 调试用

        # 操，按顺序填进去
        # 假设顺序是：日期 星期 预计 实际 增加率(跳过) 周一预计 增加率(跳过) 房价
        # 我们只要：预计, 实际, 周一预计, 房价
        data_indices = {
            "当日预计 (%)": 0,
            "当日实际 (%)": 1,
            "周一预计 (%)": 3,
            "平均房价": 5
        }
        
        # 妈的，这垃圾OCR识别率太低，换个策略
        # 我们只要前4个数字，按顺序填
        try:
            if len(cleaned_numbers) >= 1:
                df.at[row_index, "当日预计 (%)"] = cleaned_numbers[0]
            if len(cleaned_numbers) >= 2:
                df.at[row_index, "当日实际 (%)"] = cleaned_numbers[1]
            # 第三个（当日增加率）跳过，因为我们要重算
            if len(cleaned_numbers) >= 4: # 跳过第3个，拿第4个
                df.at[row_index, "周一预计 (%)"] = cleaned_numbers[3]
            if len(cleaned_numbers) >= 6: # 跳过第5个，拿第6个
                df.at[row_index, "平均房价"] = cleaned_numbers[5]
        except Exception as e:
            st.warning(f"操，解析行 '{line}' 出错了: {e}")
            
        row_index += 1
        
    return df

def calculate_rates(df):
    """操，填完表了，给老子算结果！"""
    df_result = df.copy()
    try:
        # 确保数据是数字
        for col in ["当日预计 (%)", "当日实际 (%)", "周一预计 (%)", "平均房价"]:
            df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0)

        # 操，开始计算
        df_result["当日增加率 (%)"] = df_result["当日实际 (%)"] - df_result["当日预计 (%)"]
        df_result["增加百分率 (%)"] = df_result["当日实际 (%)"] - df_result["周一预计 (%)"]
        
        return df_result
    except Exception as e:
        st.error(f"操，计算的时候出错了: {e}")
        return df # 返回原始表

def create_word_doc(jl_df, yt_df, jl_summary, yt_summary):
    """
    操，给你生成那个破Word文档
    """
    try:
        document = Document()
        # 设置中文字体
        document.styles['Normal'].font.name = '宋体'
        document.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        document.styles['Normal'].font.size = Pt(11)

        # 标题
        title = document.add_heading('每日出租率对照表', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # --- 金陵楼 ---
        p_jl = document.add_paragraph('金陵楼', style='Heading 2')
        table_jl = document.add_table(rows=jl_df.shape[0] + 1, cols=jl_df.shape[1])
        table_jl.style = 'Table Grid'
        
        # 写表头
        hdr_cells = table_jl.rows[0].cells
        for i, col_name in enumerate(jl_df.columns):
            hdr_cells[i].text = col_name
            hdr_cells[i].paragraphs[0].runs[0].font.bold = True

        # 写数据
        for index, row in jl_df.iterrows():
            row_cells = table_jl.rows[index + 1].cells
            for i, col_name in enumerate(jl_df.columns):
                val = row[col_name]
                if isinstance(val, float):
                    if "%" in col_name:
                        row_cells[i].text = f"{val:+.1f}%" if "增加" in col_name else f"{val:.1f}%"
                    else:
                        row_cells[i].text = f"{val:.1f}"
                else:
                    row_cells[i].text = str(val)
        
        document.add_paragraph(jl_summary) # 本周实际

        # --- 亚太商务楼 ---
        document.add_paragraph('亚太商务楼', style='Heading 2')
        table_yt = document.add_table(rows=yt_df.shape[0] + 1, cols=yt_df.shape[1])
        table_yt.style = 'Table Grid'

        # 写表头
        hdr_cells_yt = table_yt.rows[0].cells
        for i, col_name in enumerate(yt_df.columns):
            hdr_cells_yt[i].text = col_name
            hdr_cells_yt[i].paragraphs[0].runs[0].font.bold = True

        # 写数据
        for index, row in yt_df.iterrows():
            row_cells_yt = table_yt.rows[index + 1].cells
            for i, col_name in enumerate(yt_df.columns):
                val = row[col_name]
                if isinstance(val, float):
                    if "%" in col_name:
                        row_cells_yt[i].text = f"{val:+.1f}%" if "增加" in col_name else f"{val:.1f}%"
                    else:
                        row_cells_yt[i].text = f"{val:.1f}"
                else:
                    row_cells_yt[i].text = str(val)

        document.add_paragraph(yt_summary) # 本周实际

        # 操，保存到内存里
        f = io.BytesIO()
        document.save(f)
        f.seek(0)
        return f.read()

    except Exception as e:
        st.error(f"操，生成Word的时候出错了: {e}")
        st.code(traceback.format_exc())
        return None

# ==============================================================================
# --- [Streamlit 界面] ---
# ==============================================================================
def run_ocr_calculator_app():
    st.title("操！OCR出租率计算器 (阿里云版)")
    st.markdown("1. **上传图片** -> 2. **自动识别** -> 3. **人工修正** -> 4. **计算 & 下载Word**")

    # 初始化 session_state
    if 'jl_df' not in st.session_state:
        st.session_state.jl_df = pd.DataFrame()
    if 'yt_df' not in st.session_state:
        st.session_state.yt_df = pd.DataFrame()
    if 'ocr_text' not in st.session_state:
        st.session_state.ocr_text = ""

    uploaded_file = st.file_uploader("上传你那张手写的破纸 (JPG, PNG)", type=["png", "jpg", "jpeg"], key="ocr_calc_uploader")

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="就是这张破纸", width=300)

        if st.button("操，给老子识别！", type="primary"):
            with st.spinner('正在调阿里云...'):
                ocr_text = get_aliyun_ocr(image)
                if ocr_text:
                    st.session_state.ocr_text = ocr_text
                    st.success("操，识别完了！")
                    with st.expander("点开看识别原文（一坨屎）"):
                        st.text(ocr_text)
                    
                    st.info("操，老子正在试着把原文填进表里...")
                    st.session_state.jl_df = parse_ocr_to_dataframe(ocr_text, "金陵楼")
                    st.session_state.yt_df = parse_ocr_to_dataframe(ocr_text, "亚太商务楼")
                    st.success("操，填完了！你自己检查下，不对的给老子改过来！")
                else:
                    st.error("操，阿里云啥也没返回！")

    if not st.session_state.jl_df.empty or not st.session_state.yt_df.empty:
        st.markdown("---")
        st.subheader("金陵楼 (给老子使劲改！)")
        edited_jl_df = st.data_editor(
            st.session_state.jl_df, 
            key="editor_jl",
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "当日预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "当日实际 (%)": st.column_config.NumberColumn(format="%.1f"),
                "周一预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "平均房价": st.column_config.NumberColumn(format="%.1f"),
            }
        )
        
        st.subheader("亚太商务楼 (给老子使劲改！)")
        edited_yt_df = st.data_editor(
            st.session_state.yt_df, 
            key="editor_yt",
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "当日预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "当日实际 (%)": st.column_config.NumberColumn(format="%.1f"),
                "周一预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "平均房价": st.column_config.NumberColumn(format="%.1f"),
            }
        )
        
        st.markdown("---")
        if st.button("操，改完了，给老子算！", type="primary"):
            st.session_state.jl_result_df = calculate_rates(edited_jl_df)
            st.session_state.yt_result_df = calculate_rates(edited_yt_df)
            st.balloons()
            st.success("操，算完了！看下面！")

    if 'jl_result_df' in st.session_state and not st.session_state.jl_result_df.empty:
        st.subheader("金陵楼 - 最终结果")
        st.dataframe(st.session_state.jl_result_df.style.format({
            "当日预计 (%)": "{:.1f}%",
            "当日实际 (%)": "{:.1f}%",
            "当日增加率 (%)": "{:+.1f}%",
            "周一预计 (%)": "{:.1f}%",
            "增加百分率 (%)": "{:+.1f}%",
            "平均房价": "{:.1f}"
        }))
        
        # 操，算总和
        jl_actual_total = st.session_state.jl_result_df["当日实际 (%)"].mean()
        jl_summary = f"本周实际: {jl_actual_total:.1f}%"
        st.metric("本周实际 (平均)", f"{jl_actual_total:.1f}%")

        st.subheader("亚太商务楼 - 最终结果")
        st.dataframe(st.session_state.yt_result_df.style.format({
            "当日预计 (%)": "{:.1f}%",
            "当日实际 (%)": "{:.1f}%",
            "当日增加率 (%)": "{:+.1f}%",
            "周一预计 (%)": "{:.1f}%",
            "增加百分率 (%)": "{:+.1f}%",
            "平均房价": "{:.1f}"
        }))
        
        yt_actual_total = st.session_state.yt_result_df["当日实际 (%)"].mean()
        yt_summary = f"本周实际: {yt_actual_total:.1f}%"
        st.metric("本周实际 (平均)", f"{yt_actual_total:.1f}%")
        
        # 操，生成Word的按钮
        st.markdown("---")
        st.subheader("下载报告")
        
        # 准备最终给Word的数据
        jl_doc_df = st.session_state.jl_result_df[[
            "日期", "星期", "当日预计 (%)", "当日实际 (%)", "当日增加率 (%)", 
            "周一预计 (%)", "增加百分率 (%)", "平均房价"
        ]]
        yt_doc_df = st.session_state.yt_result_df[[
            "日期", "星期", "当日预计 (%)", "当日实际 (%)", "当日增加率 (%)", 
            "周一预计 (%)", "增加百分率 (%)", "平均房价"
        ]]

        word_data = create_word_doc(jl_doc_df, yt_doc_df, jl_summary, yt_summary)
        
        if word_data:
            st.download_button(
                label="操，点这里下载Word文档！",
                data=word_data,
                file_name=f"每日出租率对照表_{date.today().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

