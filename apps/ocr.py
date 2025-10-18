import streamlit as st
import pandas as pd
import re
import io
import json
from PIL import Image

# Import configurations from the central config file
from config import TEAM_TYPE_MAP, DEFAULT_TEAM_TYPE, ALL_ROOM_CODES

# --- SDK Dependency Check ---
try:
    from alibabacloud_ocr_api20210707.client import Client as OcrClient
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_ocr_api20210707 import models as ocr_models
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False

# --- Core OCR and Parsing Logic ---

def get_ocr_text_from_aliyun(image: Image.Image) -> str:
    """
    Calls the Aliyun OCR API to extract text from an image.
    Handles credential checking and error reporting within the Streamlit app.
    """
    if not ALIYUN_SDK_AVAILABLE:
        st.error("错误：阿里云 SDK 未安装。请运行 'pip install alibabacloud_ocr_api20210707' 进行安装。")
        return None
    
    if "aliyun_credentials" not in st.secrets:
        st.error("错误：阿里云凭证未在 .streamlit/secrets.toml 中配置。")
        return None
    
    access_key_id = st.secrets.aliyun_credentials.get("access_key_id")
    access_key_secret = st.secrets.aliyun_credentials.get("access_key_secret")

    if not access_key_id or not access_key_secret:
        st.error("错误：阿里云 AccessKey ID 或 Secret 未在 Secrets 中正确配置。")
        return None
        
    try:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint='ocr-api.cn-hangzhou.aliyuncs.com'
        )
        client = OcrClient(config)

        buffered = io.BytesIO()
        # Ensure image is in RGB format, as RGBA can cause issues
        image_to_save = image.convert('RGB') if image.mode == 'RGBA' else image
        
        image_format = "JPEG"
        image_to_save.save(buffered, format=image_format)
        buffered.seek(0)
        
        request = ocr_models.RecognizeGeneralRequest(body=buffered)
        response = client.recognize_general(request)

        if response.status_code == 200 and response.body and response.body.data:
            data = json.loads(response.body.data)
            return data.get('content', '')
        else:
            error_message = response.body.message if response.body and hasattr(response.body, 'message') else '无详细信息'
            raise Exception(f"阿里云 OCR API 返回错误: {error_message}")

    except Exception as e:
        st.error(f"调用阿里云 OCR API 失败: {e}")
        return None

def extract_booking_info(ocr_text: str):
    """
    Parses the raw OCR text to extract structured booking information.
    """
    team_name_pattern = re.compile(r'((?:CON|FIT|WA)\d+\s*/\s*[\u4e00-\u9fa5\w]+)', re.IGNORECASE)
    date_pattern = re.compile(r'(\d{1,2}/\d{1,2})')

    team_name_match = team_name_pattern.search(ocr_text)
    if not team_name_match:
        return "错误：无法识别出团队名称。"
    team_name = re.sub(r'\s*/\s*', '/', team_name_match.group(1).strip())

    all_dates = date_pattern.findall(ocr_text)
    unique_dates = sorted(list(set(all_dates)))
    if not unique_dates:
        return "错误：无法识别出有效的日期。"
    arrival_date, departure_date = unique_dates[0], unique_dates[-1]

    room_codes_pattern_str = '|'.join(ALL_ROOM_CODES)
    room_finder_pattern = re.compile(f'({room_codes_pattern_str})\\s*(\\d+)', re.IGNORECASE)
    price_finder_pattern = re.compile(r'\b(\d+\.\d{2})\b')

    found_rooms = [(m.group(1).upper(), int(m.group(2)), m.span()) for m in room_finder_pattern.finditer(ocr_text)]
    found_prices = [(float(m.group(1)), m.span()) for m in price_finder_pattern.finditer(ocr_text)]

    room_details = []
    available_prices = list(found_prices)

    # Associate rooms with the closest price found after them
    for room_type, num_rooms, room_span in found_rooms:
        best_price, best_price_index, min_distance = None, -1, float('inf')
        for i, (price_val, price_span) in enumerate(available_prices):
            if price_span[0] > room_span[1]:
                distance = price_span[0] - room_span[1]
                if distance < min_distance:
                    min_distance, best_price, best_price_index = distance, price_val, i
        
        if best_price is not None and best_price > 0:
            room_details.append((room_type, num_rooms, int(best_price)))
            if best_price_index != -1:
                available_prices.pop(best_price_index)

    if not room_details:
        return f"提示：找到了团队 {team_name}，但未能自动匹配任何有效的房型和价格。请检查原始文本并手动填写。"

    team_prefix = team_name[:3].upper()
    team_type = TEAM_TYPE_MAP.get(team_prefix, DEFAULT_TEAM_TYPE)
    room_details.sort(key=lambda x: x[1])

    try:
        arr_month, arr_day = map(int, arrival_date.split('/'))
        dep_month, dep_day = map(int, departure_date.split('/'))
        formatted_arrival = f"{arr_month}月{arr_day}日"
        formatted_departure = f"{dep_month}月{dep_day}日"
    except (ValueError, IndexError):
        return "错误：日期格式无法解析。"

    df = pd.DataFrame(room_details, columns=['房型', '房数', '定价'])
    return {
        "team_name": team_name,
        "team_type": team_type,
        "arrival_date": formatted_arrival,
        "departure_date": formatted_departure,
        "room_dataframe": df
    }

def format_notification_speech(team_name, team_type, arrival_date, departure_date, room_df):
    """Formats the final notification string."""
    date_range_string = f"{arrival_date}至{departure_date}"
    room_details = room_df.to_dict('records')
    formatted_rooms = [f"{item['房数']}间{item['房型']}({item['定价']})" for item in room_details]
    room_string = " ".join(formatted_rooms) if formatted_rooms else "无房间详情"
    return f"新增{team_type} {team_name} {date_range_string} {room_string}。销售通知"


# --- Streamlit UI ---

def run_ocr_app():
    """Renders the Streamlit UI for the OCR Tool."""
    st.title("金陵工具箱 - OCR 工具")
    
    st.markdown("""
    **全新工作流**：
    1.  **上传图片，点击提取**：程序将调用阿里云 OCR 并将**原始识别文本**显示在下方。
    2.  **自动填充与人工修正**：程序会尝试自动填充结构化信息。您可以**参照原始文本**，直接在表格中修改，确保信息完全准确。
    3.  **生成话术**：确认无误后，生成最终话术。
    """)

    uploaded_file = st.file_uploader("上传图片文件", type=["png", "jpg", "jpeg", "bmp"], key="ocr_uploader")

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的图片", width=300)

        if st.button("从图片提取信息 (阿里云 OCR)", type="primary"):
            # Clear old state before processing a new image
            st.session_state.pop('raw_ocr_text', None)
            st.session_state.pop('booking_info', None)
            
            with st.spinner('正在调用阿里云 OCR API 识别中...'):
                ocr_text = get_ocr_text_from_aliyun(image)
                if ocr_text:
                    st.session_state['raw_ocr_text'] = ocr_text
                    result = extract_booking_info(ocr_text)
                    if isinstance(result, str):
                        st.warning(f"自动解析提示：{result}")
                        st.info("请参考下方识别出的原始文本，手动填写信息。")
                        # Prepare an empty structure for manual input
                        empty_df = pd.DataFrame(columns=['房型', '房数', '定价'])
                        st.session_state['booking_info'] = {
                            "team_name": "", "team_type": DEFAULT_TEAM_TYPE,
                            "arrival_date": "", "departure_date": "", "room_dataframe": empty_df
                        }
                    else:
                        st.session_state['booking_info'] = result
                        st.success("信息提取成功！请在下方核对并编辑。")

    # Display editor UI if booking_info exists in session state
    if 'booking_info' in st.session_state:
        info = st.session_state['booking_info']
        
        if 'raw_ocr_text' in st.session_state:
            with st.expander("原始识别结果 (供参考)", expanded=False):
                st.text_area("您可以从这里复制内容来修正下面的表格", st.session_state['raw_ocr_text'], height=200)

        st.markdown("---")
        st.subheader("核对与编辑信息")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            info['team_name'] = st.text_input("团队名称", value=info['team_name'])
        with col2:
            team_type_options = list(TEAM_TYPE_MAP.values()) + [DEFAULT_TEAM_TYPE]
            try:
                current_index = team_type_options.index(info['team_type'])
            except ValueError:
                current_index = len(team_type_options) - 1 # Default to the last one
            info['team_type'] = st.selectbox("团队类型", options=team_type_options, index=current_index)
        with col3:
            arrival = st.text_input("到达日期", value=info['arrival_date'])
        with col4:
            departure = st.text_input("离开日期", value=info['departure_date'])
        
        st.markdown("##### 房间详情 (可直接在表格中编辑)")
        edited_df = st.data_editor(info['room_dataframe'], num_rows="dynamic", use_container_width=True)
        
        if st.button("生成最终话术"):
            final_speech = format_notification_speech(info['team_name'], info['team_type'], arrival, departure, edited_df)
            st.subheader("生成成功！")
            st.success(final_speech)
            st.code(final_speech, language=None)

