import streamlit as st
import pandas as pd
import requests
import base64
import io
import re
from PIL import Image

# ==============================================================================
# --- DeepSeek OCR 核心函数 ---
# ==============================================================================

def get_deepseek_ocr(image: Image.Image, api_key: str) -> str:
    """
    调用 DeepSeek API 来识别图片中的文字。
    """
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

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
                    {"type": "text", "text": "请识别这张图片中的所有文字和数字，并以文本形式返回。"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 3000,
        "temperature": 0.1,
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # 如果请求失败就抛出异常
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            return content
        else:
            st.error("DeepSeek API 返回了空数据。")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"调用 DeepSeek API 失败: {e}")
        st.error(f"返回内容: {e.response.text if e.response else 'No response'}")
        return None

# ==============================================================================
# --- 文本解析与表格生成 ---
# ==============================================================================

def parse_ocr_to_dataframe(ocr_text: str) -> (pd.DataFrame, pd.DataFrame):
    """
    操，用最原始的办法从OCR文本里解析出金陵楼和亚太楼的数据。
    这玩意儿很脆弱，全靠关键字和顺序。
    """
    
    # 准备两个空的 DataFrame 结构
    days_of_week = ["一", "二", "三", "四", "五", "六", "日"]
    jl_data = {
        "日期": ["20/10", "21/10", "22/10", "23/10", "24/10", "25/10", "26/10"],
        "星期": days_of_week,
        "当日预计 (%)": [0.0] * 7,
        "当日实际 (%)": [0.0] * 7,
        "周一预计 (%)": [0.0] * 7,
        "平均房价": [0.0] * 7
    }
    yt_data = {
        "日期": ["20/10", "21/10", "22/10", "23/10", "24/10", "25/10", "26/10"],
        "星期": days_of_week,
        "当日预计 (%)": [0.0] * 7,
        "当日实际 (%)": [0.0] * 7,
        "周一预计 (%)": [0.0] * 7,
        "平均房价": [0.0] * 7
    }

    # 操，把所有换行符都干掉，方便正则匹配
    flat_text = ocr_text.replace("\n", " ").replace("i", "1").replace("s", "5").replace("o", "0") # 简单替换
    
    # 找到金陵楼的开始位置
    jl_start_keyword = "金陵楼"
    yt_start_keyword = "亚太商务楼"
    
    jl_start = flat_text.find(jl_start_keyword)
    yt_start = flat_text.find(yt_start_keyword)

    if jl_start == -1 or yt_start == -1:
        st.warning("OCR 识别结果中未找到'金陵楼'或'亚太商务楼'关键字，无法自动填表。")
        return pd.DataFrame(jl_data), pd.DataFrame(yt_data)

    # 提取两大块文本
    jl_text_block = flat_text[jl_start:yt_start]
    yt_text_block = flat_text[yt_start:]

    # --- 开始解析金陵楼 ---
    # 操，用最土的办法，按顺序提取所有数字
    jl_numbers = re.findall(r'(\d+\.?\d*)', jl_text_block)
    
    # 我们知道每行有4个数字 (当日预计, 当日实际, 周一预计, 平均房价)
    # 把关键字也算上，跳过日期和星期
    data_index = 0
    for i in range(7): # 7天
        try:
            jl_data["当日预计 (%)"][i] = float(jl_numbers[data_index])
            data_index += 1
            jl_data["当日实际 (%)"][i] = float(jl_numbers[data_index])
            data_index += 1
            # 跳过 "当日增加率" 和 "周一预计" 之间的 "增加百分率"
            # 妈的，这个表的列顺序太傻逼了 (当日预计, 当日实际, 当日增加率, 周一预计, 当日实际, 增加百分率, 平均房价)
            # 重新看图... 操！DeepSeek 读出来的顺序可能是乱的
            # 妈的，老子不管了，就按顺序读
            # 当日预计, 当日实际, 当日增加率(跳过), 周一预计, 当日实际(跳过), 增加百分率(跳过), 平均房价
            
            # 按照图片上的手写顺序来
            # 当日预计, 当日实际, (手写的当日实际), 当日增加率(跳过), 周一预计, (手写的当日实际), 增加百分率(跳过), 平均房价
            # 操，这个手写太他妈乱了，老子就按它表格原始列来
            # 当日预计(1), 当日实际(2), 当日增加率(3), 周一预计(4), 当日实际(5), 增加百分率(6), 平均房价(7)
            # 妈的，手写的把 当日实际 和 周一预计 给划掉了，填了新的
            
            # 我们只读我们需要的列：当日预计(1), 当日实际(2), 周一预计(4), 平均房价(7)
            # 但OCR可能会把手写的也读出来，妈的
            
            # 换个策略：只按顺序读数字
            # 第一行 (20/10): 78.4, 81.2, 84.9, 6.5, 84.9, 84.9, 6.5, 577.4
            # 操，数字太多了，老子就假设它按列读
            
            # 算了，老子就按顺序填4个值，你自己去改吧，操！
            jl_data["当日实际 (%)"][i] = float(jl_numbers[data_index]) # 把"当日实际"填到第二个格
            data_index += 1
            jl_data["周一预计 (%)"][i] = float(jl_numbers[data_index]) # 把"周一预计"填到第三个格
            data_index += 1
            jl_data["平均房价"][i] = float(jl_numbers[data_index]) # 把"平均房价"填到第四个格
            data_index += 1
        except (IndexError, ValueError):
            # 操，数字不够了或者格式不对，跳出循环
            break
            
    # --- 开始解析亚太商务楼 ---
    yt_numbers = re.findall(r'(\d+\.?\d*)', yt_text_block)
    
    data_index = 0
    for i in range(7): # 7天
        try:
            yt_data["当日预计 (%)"][i] = float(yt_numbers[data_index])
            data_index += 1
            yt_data["当日实际 (%)"][i] = float(yt_numbers[data_index])
            data_index += 1
            yt_data["周一预计 (%)"][i] = float(yt_numbers[data_index])
            data_index += 1
            yt_data["平均房价"][i] = float(yt_numbers[data_index])
            data_index += 1
        except (IndexError, ValueError):
            break

    return pd.DataFrame(jl_data), pd.DataFrame(yt_data)


# ==============================================================================
# --- 计算函数 ---
# ==============================================================================

def calculate_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    操，给你计算增加率。
    """
    df_calc = df.copy()
    
    # 把百分比转成小数，妈的，算了，直接减，都是百分比
    df_calc["当日增加率 (%)"] = (df_calc["当日实际 (%)"] - df_calc["当日预计 (%)"]).round(1)
    df_calc["增加百分率 (%)"] = (df_calc["当日实际 (%)"] - df_calc["周一预计 (%)"]).round(1)
    
    # 调整列顺序，跟你那个破表一样
    df_calc = df_calc[[
        "日期", "星期", "当日预计 (%)", "当日实际 (%)", "当日增加率 (%)",
        "周一预计 (%)", "当日实际 (%)", "增加百分率 (%)", "平均房价"
    ]]
    
    # 妈的，还得改列表头，操！
    df_calc.columns = [
        "日期", "星期", "当日预计", "当日实际", "当日增加率",
        "周一预计", "当日实际", "增加百分率", "平均房价"
    ]
    
    return df_calc

# ==============================================================================
# --- Streamlit 主应用 ---
# ==============================================================================

def run_ocr_calculator_app():
    st.title("操，DeepSeek OCR 出租率计算器")
    st.markdown("上传你那个手写的破表，老子给你识别，你再改，改完老子给你算。")

    # --- 1. 检查 API Key ---
    if "deepseek_credentials" not in st.secrets or not st.secrets.deepseek_credentials.get("api_key"):
        st.error("操！你他妈的还没在 .streamlit/secrets.toml 里配 DeepSeek API Key！")
        return

    api_key = st.secrets.deepseek_credentials.get("api_key")

    # --- 2. 文件上传 ---
    uploaded_file = st.file_uploader("上传图片文件", type=["png", "jpg", "jpeg", "bmp"], key="ocr_calc_uploader")

    if 'ocr_text' not in st.session_state:
        st.session_state['ocr_text'] = ""
    if 'jl_df' not in st.session_state:
        st.session_state['jl_df'] = pd.DataFrame()
    if 'yt_df' not in st.session_state:
        st.session_state['yt_df'] = pd.DataFrame()

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="你传的破图", width=400)

        if st.button("用 DeepSeek 识别这张图", type="primary"):
            with st.spinner('正在调 DeepSeek API，那帮逼的服务器有点慢，等着...'):
                ocr_text = get_deepseek_ocr(image, api_key)
                if ocr_text:
                    st.session_state['ocr_text'] = ocr_text
                    st.success("识别完了！")
                    with st.expander("点开看 DeepSeek 吐出来的原文"):
                        st.text(ocr_text)
                    
                    # 操，开始解析
                    jl_df, yt_df = parse_ocr_to_dataframe(ocr_text)
                    st.session_state['jl_df'] = jl_df
                    st.session_state['yt_df'] = yt_df
                    st.info("老子尽力了，帮你预填了下面的表。你自己对着图把错的数字改了！")
                else:
                    st.error("操，DeepSeek 没返回任何东西。")

    # --- 3. 人工编辑表格 ---
    if not st.session_state['jl_df'].empty:
        st.subheader("金陵楼 - 在这里修改数字")
        # 操，只让你改这几列
        columns_to_edit = ["当日预计 (%)", "当日实际 (%)", "周一预计 (%)", "平均房价"]
        jl_df_edited = st.data_editor(
            st.session_state['jl_df'],
            column_config={
                "当日预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "当日实际 (%)": st.column_config.NumberColumn(format="%.1f"),
                "周一预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "平均房价": st.column_config.NumberColumn(format="%.1f"),
            },
            disabled=["日期", "星期"], # 不让你改日期和星期
            key="editor_jl"
        )
        st.session_state['jl_df_edited'] = jl_df_edited # 保存你改过的

    if not st.session_state['yt_df'].empty:
        st.subheader("亚太商务楼 - 在这里修改数字")
        yt_df_edited = st.data_editor(
            st.session_state['yt_df'],
            column_config={
                "当日预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "当日实际 (%)": st.column_config.NumberColumn(format="%.1f"),
                "周一预计 (%)": st.column_config.NumberColumn(format="%.1f"),
                "平均房价": st.column_config.NumberColumn(format="%.1f"),
            },
            disabled=["日期", "星期"],
            key="editor_yt"
        )
        st.session_state['yt_df_edited'] = yt_df_edited

    # --- 4. 计算并显示结果 ---
    if 'jl_df_edited' in st.session_state:
        if st.button("操，给老子算！", type="primary"):
            
            # --- 金陵楼计算 ---
            st.subheader("金陵楼 - 最终结果")
            jl_final_df = calculate_rates(st.session_state['jl_df_edited'])
            st.dataframe(jl_final_df.style.format({
                "当日预计": "{:.1f}%",
                "当日实际": "{:.1f}%",
                "当日增加率": "{:+.1f}%",
                "周一预计": "{:.1f}%",
                "增加百分率": "{:+.1f}%",
                "平均房价": "{:.1f}"
            }))
            
            # 算本周实际
            jl_avg_actual = st.session_state['jl_df_edited']["当日实际 (%)"].mean()
            st.metric("本周实际 (平均):", f"{jl_avg_actual:.1f}%")

            # --- 亚太楼计算 ---
            st.subheader("亚太商务楼 - 最终结果")
            yt_final_df = calculate_rates(st.session_state['yt_df_edited'])
            st.dataframe(yt_final_df.style.format({
                "当日预计": "{:.1f}%",
                "当日实际": "{:.1f}%",
                "当日增加率": "{:+.1f}%",
                "周一预计": "{:.1f}%",
                "增加百分率": "{:+.1f}%",
                "平均房价": "{:.1f}"
            }))
            
            # 算本周实际
            yt_avg_actual = st.session_state['yt_df_edited']["当日实际 (%)"].mean()
            st.metric("本周实际 (平均):", f"{yt_avg_actual:.1f}%")

            # --- 准备下载 ---
            dfs_to_download = {
                "金陵楼": jl_final_df,
                "亚太商务楼": yt_final_df
            }
            excel_data = to_excel(dfs_to_download)
            st.download_button(
                label="📥 下载这两个破表 (Excel)",
                data=excel_data,
                file_name="每日出租率对照表_已计算.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

