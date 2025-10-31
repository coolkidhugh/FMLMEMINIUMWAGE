import streamlit as st
import pandas as pd
import numpy as np
import re
import requests
import base64
import io
from PIL import Image

def run_ocr_calculator_app():
    st.title("金陵工具箱 - OCR出租率计算器")
    st.markdown("操，上传你那个手写的破表，老子用 DeepSeek 给你读出来，你再改，改完老子给你算！")

    # --- DeepSeek OCR 引擎 (带图片压缩) ---
    def get_deepseek_ocr_text(image_bytes: bytes) -> str:
        if "deepseek_credentials" not in st.secrets or not st.secrets.deepseek_credentials.get("api_key"):
            st.error("操！你他妈的还没在 .streamlit/secrets.toml 里配 DeepSeek API Key！")
            return None
        api_key = st.secrets.deepseek_credentials.get("api_key")

        # --- 操，图片压缩逻辑 ---
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # 保持宽高比，限制最大宽度为 1024
            max_width = 1024
            if img.width > max_width:
                scale = max_width / img.width
                new_height = int(img.height * scale)
                img = img.resize((max_width, new_height), Image.LANCZOS)

            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85) # 操，压成85质量的JPG
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            st.info(f"图片压缩完毕，压缩后大小: {len(img_base64) / 1024:.2f} KB")

        except Exception as e:
            st.error(f"操，压缩图片时出错了: {e}")
            return None
        # --- 压缩结束 ---

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "deepseek-vl",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请精确识别这张表格图片中的所有文字和数字，按从上到下、从左到右的顺序返回纯文本。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
                return content
            else:
                st.error("DeepSeek API 返回了空数据。")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"调用 DeepSeek API 失败: {e}")
            if e.response is not None:
                st.error(f"返回内容: {e.response.text}")
            else:
                st.error("操，DeepSeek 没返回任何东西。")
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
            
            # 操，用正则表达式硬抠数字和日期
            # 匹配 "20/10 一 78.4% 81.9% 6.5% 84.9% 84.9% 6.5% 577.4" 这种格式
            # 或者 "20/10 一 67.4% 81.9% 18.1% 81.9% 82.1% 18.1% 706.9"
            # 或者 "26/10 日 86.9% 60.5% 19.7% 67.5% 76.6% 52.7% 779.2" (操，这个%还可能没有)
            
            # 正则解释:
            # (\d{1,2}/\d{1,2})\s+      # 1. 日期 (20/10)
            # ([\u4e00-\u9fa5])\s+      # 2. 星期 (一)
            # ([\d\.]+)%?\s+           # 3. 当日预计
            # ([\d\.]+)%?\s+           # 4. 当日实际
            # ([\d\.\-]+)%?\s+         # 5. 当日增加率 (妈的这个不填，我们自己算)
            # ([\d\.]+)%?\s+           # 6. 周一预计
            # ([\d\.]+)%?\s+           # 7. 当日实际 (操，又来一个，PDF上是这个)
            # ([\d\.\-]+)%?\s+         # 8. 增加百分率 (这个也不填)
            # ([\d\.]+)$                # 9. 平均房价
            
            # 操，简化版正则，只抓我们要填的
            pattern = re.compile(r"(\d{1,2}/\d{1,2})\s+([\u4e00-\u9fa5])\s+([\d\.]+)%?\s+([\d\.]+)%?\s+[\d\.\-]+%?\s+([\d\.]+)%?\s+([\d\.]+)%?\s+[\d\.\-]+%?\s+([\d\.]+)$")
            match = pattern.search(line)
            
            if match:
                try:
                    date = match.group(1)
                    weekday = match.group(2)
                    daily_forecast = float(match.group(3))
                    daily_actual = float(match.group(4))
                    monday_forecast = float(match.group(5))
                    # 操，第6组 (([\d\.]+)%?) 是亚太楼的 "当日实际"，金陵楼的在第7组
                    # 但你妈的 DeepSeek 可能会把两个当日实际读成一样的
                    # 我们就用第6组吧，反正后面要改
                    # 妈的，看了下你的表，周一预计后面那个才是真的 "当日实际"，操，那就是第6组
                    daily_actual_2 = float(match.group(6)) # 用这个当实际值
                    avg_price = float(match.group(7))

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

        if st.button("用 DeepSeek 识别并填表", type="primary"):
            with st.spinner('操，DeepSeek 正在玩命识别...'):
                ocr_text = get_deepseek_ocr_text(image_bytes)
            
            if ocr_text:
                st.success("操，识别完了！")
                with st.expander("点开看 DeepSeek 吐出来的原文"):
                    st.text_area("OCR 原始文本", ocr_text, height=300)
                
                jl_df, yt_df = parse_ocr_to_dataframe(ocr_text)
                st.session_state['jl_df'] = jl_df
                st.session_state['yt_df'] = yt_df
            else:
                st.error("操，DeepSeek 啥也没返回，是不是 Key 错了或者网断了？")

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

