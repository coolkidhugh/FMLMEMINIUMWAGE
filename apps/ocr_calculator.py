import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import json # 操，阿里SDK要用
from PIL import Image

# --- 操，导入阿里云的傻逼SDK ---
try:
    from alibabacloud_ocr_api20210707.client import Client as OcrClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_ocr_api20210707 import models as ocr_models
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False

def run_ocr_calculator_app():
    st.title("金陵工具箱 - OCR出租率计算器")
    st.markdown("操，上传你那个手写的破表，老子用**阿里云**给你读出来，你再改，改完老子给你算！")

    # --- 阿里云 OCR 引擎 (带图片压缩) ---
    def get_aliyun_ocr_text(image_bytes: bytes) -> str:
        if not ALIYUN_SDK_AVAILABLE:
            st.error("操！你他妈的没装阿里云SDK！ 'pip install alibabacloud_ocr_api20210707'")
            return None
        if "aliyun_credentials" not in st.secrets:
            st.error("操！阿里云凭证未在 Streamlit 的 Secrets 中配置。")
            return None
        access_key_id = st.secrets.aliyun_credentials.get("access_key_id")
        access_key_secret = st.secrets.aliyun_credentials.get("access_key_secret")
        if not access_key_id or not access_key_secret:
            st.error("操！阿里云 AccessKey ID 或 Secret 未在 Secrets 中正确配置。")
            return None
        
        try:
            config = open_api_models.Config(access_key_id=access_key_id, access_key_secret=access_key_secret, endpoint='ocr-api.cn-hangzhou.aliyuncs.com')
            client = OcrClient(config)
            
            # --- 操，图片压缩逻辑还得留着 ---
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85) # 操，压成85质量的JPG
            buffered.seek(0)
            st.info(f"图片压缩完毕，准备上传阿里云...")
            # --- 压缩结束 ---
            
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
            st.error(f"调用阿里云 OCR API 失败: {e}")
            return None

    # --- 解析文本并填充表格的傻逼逻辑 ---
    def parse_ocr_to_dataframe(ocr_text: str):
        # 操，定义两个空的DataFrame结构
        jl_cols = ["日期", "星期", "当日预计 (%)", "当日实际 (%)", "周一预计 (%)", "平均房价"]
        yt_cols = ["日期", "星期", "当日预计 (%)", "当日实际 (%)", "周一预计 (%)", "平均房价"]
        
        jl_df = pd.DataFrame(np.nan, index=range(7), columns=jl_cols)
        yt_df = pd.DataFrame(np.nan, index=range(7), columns=yt_cols)

        # 操，把文本按行分开
        lines = ocr_text.split('\n')
        
        current_df = None
        jl_row_index = 0
        yt_row_index = 0

        for line in lines:
            line = line.strip()
            if "金陵楼" in line:
                current_df = "JL"
                continue
            if "亚太商务楼" in line:
                current_df = "YT"
                continue
            
            # 操，简化版正则，只抓我们要填的
            pattern = re.compile(r"(\d{1,2}/\d{1,2})\s+([\u4e00-\u9fa5])\s+([\d\.]+)%?\s+([\d\.]+)%?\s+[\d\.\-]+%?\s+([\d\.]+)%?\s+([\d\.]+)%?\s+[\d\.\-]+%?\s+([\d\.]+)$")
            match = pattern.search(line)
            
            if match:
                try:
                    date = match.group(1)
                    weekday = match.group(2)
                    daily_forecast = float(match.group(3))
                    daily_actual_raw = float(match.group(4)) # 这是OCR读的第一个“当日实际”
                    monday_forecast = float(match.group(5))
                    daily_actual_2 = float(match.group(6)) # 这是OCR读的第二个“当日实际”
                    avg_price = float(match.group(7))

                    # 操，用第二个“当日实际”，那个才是对的
                    if current_df == "JL" and jl_row_index < 7:
                        jl_df.iloc[jl_row_index] = [date, weekday, daily_forecast, daily_actual_2, monday_forecast, avg_price]
                        jl_row_index += 1
                    elif current_df == "YT" and yt_row_index < 7:
                        yt_df.iloc[yt_row_index] = [date, weekday, daily_forecast, daily_actual_2, monday_forecast, avg_price]
                        yt_row_index += 1
                except Exception as e:
                    st.warning(f"操，解析这行失败了: '{line}'，错误: {e}")
                    continue
                    
        return jl_df.fillna(0.0), yt_df.fillna(0.0) # 操，没填上的都给老子变成0

    # --- 计算增加率的傻逼逻辑 ---
    def calculate_results(df):
        df_calc = df.copy()
        try:
            # 操，确保这些列都是数字
            num_cols = ["当日预计 (%)", "当日实际 (%)", "周一预计 (%)", "平均房价"]
            for col in num_cols:
                df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0.0)

            df_calc["当日增加率 (%)"] = df_calc["当日实际 (%)"] - df_calc["当日预计 (%)"]
            df_calc["增加百分率 (%)"] = df_calc["当日实际 (%)"] - df_calc["周一预计 (%)"]
            
            # 操，格式化输出
            df_display = df_calc.style.format({
                "当日预计 (%)": "{:.1f}%",
                "当日实际 (%)": "{:.1f}%",
                "当日增加率 (%)": "{:+.1f}%",
                "周一预计 (%)": "{:.1f}%",
                "增加百分率 (%)": "{:+.1f}%",
                "平均房价": "{:.1f}"
            })
            return df_calc, df_display
        except Exception as e:
            st.error(f"操，计算的时候出错了: {e}")
            return df, df

    # --- Streamlit 界面 ---
    uploaded_file = st.file_uploader("上传你那个手写的破表 (JPG, PNG)", type=["png", "jpg", "jpeg"], key="ocr_calc_uploader")

    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="你传的傻逼图片", width=300)

        if st.button("用 阿里云 识别并填表", type="primary"):
            with st.spinner('操，阿里云 正在玩命识别...'):
                ocr_text = get_aliyun_ocr_text(image_bytes)
            
            if ocr_text:
                st.success("操，识别完了！")
                with st.expander("点开看 阿里云 吐出来的原文"):
                    st.text_area("OCR 原始文本", ocr_text, height=300)
                
                jl_df, yt_df = parse_ocr_to_dataframe(ocr_text)
                st.session_state['jl_df'] = jl_df
                st.session_state['yt_df'] = yt_df
            else:
                st.error("操，阿里云 啥也没返回。")

    if 'jl_df' in st.session_state:
        st.markdown("---")
        st.subheader("操，给老子检查一下，识别错了就自己改！")

        st.markdown("#### 金陵楼")
        edited_jl_df = st.data_editor(
            st.session_state['jl_df'],
            num_rows="fixed",
            use_container_width=True,
            key="editor_jl"
        )
        
        st.markdown("#### 亚太商务楼")
        edited_yt_df = st.data_editor(
            st.session_state['yt_df'],
            num_rows="fixed",
            use_container_width=True,
            key="editor_yt"
        )

        st.session_state['final_jl_df'] = edited_jl_df
        st.session_state['final_yt_df'] = edited_yt_df
        
        if st.button("操，改完了，给老子算！", type="primary"):
            st.markdown("---")
            st.subheader("操，这是算完的结果！")
            
            jl_calc, jl_display = calculate_results(edited_jl_df)
            st.markdown("#### 金陵楼 (最终版)")
            st.dataframe(jl_display)

            yt_calc, yt_display = calculate_results(edited_yt_df)
            st.markdown("#### 亚太商务楼 (最终版)")
            st.dataframe(yt_display)
            
            # 操，给你算个总计
            st.markdown("---")
            st.subheader("本周总计 (自己看，老子不给你念)")
            try:
                jl_total_actual = jl_calc['当日实际 (%)'].sum()
                jl_total_forecast = jl_calc['当日预计 (%)'].sum()
                jl_total_increase = jl_total_actual - jl_total_forecast
                
                yt_total_actual = yt_calc['当日实际 (%)'].sum()
                yt_total_forecast = yt_calc['当日预计 (%)'].sum()
                yt_total_increase = yt_total_actual - yt_total_forecast

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("金陵楼 - 实际增加 (点数)", f"{jl_total_increase:+.1f}")
                with col2:
                    st.metric("亚太楼 - 实际增加 (点数)", f"{yt_total_increase:+.1f}")

            except Exception as e:
                st.error(f"操，算总计的时候出错了: {e}")

