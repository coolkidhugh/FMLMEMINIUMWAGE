import streamlit as st
import pandas as pd
import os
import re
from collections import Counter

# Import configurations from the central config file
from config import JINLING_ROOM_TYPES, YATAI_ROOM_TYPES

# ==============================================================================
# --- [Core Analysis Logic] ---
# ==============================================================================
def analyze_reports_ultimate(file_paths, unknown_codes_collection):
    """
    Analyzes multiple Excel reports, dynamically locating columns and summarizing bookings.
    Modifies the passed unknown_codes_collection in place.
    """
    summary_lines = []
    if not file_paths:
        return ["未上传任何文件进行分析。"]

    for file_path in file_paths:
        file_base_name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            df_raw = pd.read_excel(file_path, header=None, dtype=str)
            all_bookings = []
            current_group_name = "未知团队"
            current_market_code = "无"
            column_map = {}
            header_row_index = -1

            # --- Parsing Loop to find headers and data rows ---
            for index, row in df_raw.iterrows():
                row_str = ' '.join(str(cell).strip() for cell in row.dropna() if str(cell).strip())
                if not row_str:
                    continue

                if '团体名称:' in row_str:
                    match = re.search(r'团体名称:\s*(.*?)(?:\s*市场码：|$)', row_str)
                    current_group_name = match.group(1).strip() if match else "未知团队(解析失败)"
                    
                    market_match = re.search(r'市场码：\s*([\w-]+)', row_str)
                    current_market_code = market_match.group(1).strip() if market_match else "无"
                    
                    # Reset column map for new group
                    column_map, header_row_index = {}, -1
                    continue

                if '房号' in row_str and '姓名' in row_str and '人数' in row_str:
                    header_row_index = index
                    for i, col in enumerate(row):
                        if pd.notna(col):
                            column_map[re.sub(r'\s+', '', str(col))] = i
                    continue

                # If we have a header and the row is not empty, it's data
                if header_row_index != -1 and index > header_row_index and not row.dropna().empty and '小计' not in row_str:
                    all_bookings.append({'团队名称': current_group_name, '市场码': current_market_code, 'data': row})

            if not all_bookings:
                summary_lines.append(f"【{file_base_name}】: 未解析到有效预订数据行。")
                continue

            # --- Data Processing ---
            processed_rows = []
            for item in all_bookings:
                row_data = item['data']
                processed_row = {'团队名称': item['团队名称'], '市场码': item['市场码']}
                for col_name, col_index in column_map.items():
                    processed_row[col_name] = row_data.get(col_index)
                processed_rows.append(processed_row)
            
            df = pd.DataFrame(processed_rows)
            df['状态'] = df['状态'].astype(str).str.strip()
            df['市场码'] = df['市场码'].astype(str).str.strip()

            # Determine valid statuses based on filename
            if '在住' in file_base_name: valid_statuses = ['R', 'I']
            elif '离店' in file_base_name or '次日离店' in file_base_name: valid_statuses = ['I', 'R', 'O']
            else: valid_statuses = ['R']
            
            df_active = df[df['状态'].isin(valid_statuses)].copy()
            df_active['房数'] = pd.to_numeric(df_active['房数'], errors='coerce').fillna(0)
            df_active['人数'] = pd.to_numeric(df_active['人数'], errors='coerce').fillna(0)
            df_active['房类'] = df_active['房类'].astype(str).str.strip()

            total_rooms = int(df_active['房数'].sum())
            total_guests = int(df_active['人数'].sum())

            # --- Building Assignment ---
            def assign_building(room_type):
                if room_type in YATAI_ROOM_TYPES: return '亚太楼'
                if room_type in JINLING_ROOM_TYPES: return '金陵楼'
                if room_type and room_type.lower() != 'nan':
                    unknown_codes_collection.update([room_type])
                return '其他楼'
            
            df_active['准确楼栋'] = df_active['房类'].apply(assign_building)

            # --- Summarization by Market Code ---
            meeting_df = df_active[df_active['市场码'].str.startswith(('MGM', 'MTC'), na=False)]
            gto_df = df_active[df_active['市场码'].str.startswith('GTO', na=False)]

            summary_parts = [f"【{file_base_name}】: 有效总房数 {total_rooms} 间 (共 {total_guests} 人)"]

            if not meeting_df.empty:
                meeting_summary = meeting_df.groupby('准确楼栋')['房数'].sum()
                meeting_report = f"会议/公司团队房({meeting_df['团队名称'].nunique()}个团, {int(meeting_df['房数'].sum())}间): " + \
                                 f"金陵楼 {int(meeting_summary.get('金陵楼', 0))} 间, 亚太楼 {int(meeting_summary.get('亚太楼', 0))} 间"
                if '其他楼' in meeting_summary and meeting_summary['其他楼'] > 0:
                    meeting_report += f", 其他楼 {int(meeting_summary.get('其他楼', 0))} 间"
                summary_parts.append(f"，其中{meeting_report}。")
            else:
                summary_parts.append("，(无会议/公司团队房)。")

            if not gto_df.empty:
                gto_summary = gto_df.groupby('准确楼栋')['房数'].sum()
                gto_report = f"旅行社(GTO)房({gto_df['团队名称'].nunique()}个团, {int(gto_df['房数'].sum())}间, 共{int(gto_df['人数'].sum())}人): " + \
                             f"金陵楼 {int(gto_summary.get('金陵楼', 0))} 间, 亚太楼 {int(gto_summary.get('亚太楼', 0))} 间"
                if '其他楼' in gto_summary and gto_summary['其他楼'] > 0:
                    gto_report += f", 其他楼 {int(gto_summary.get('其他楼', 0))} 间"
                summary_parts.append(f" | {gto_report}。")
            else:
                summary_parts.append(" | (无GTO旅行社房)。")

            summary_lines.append("".join(summary_parts))

        except Exception as e:
            summary_lines.append(f"【{file_base_name}】处理失败，错误: {e}")

    return summary_lines

# ==============================================================================
# --- Streamlit UI ---
# ==============================================================================
def run_analyzer_app():
    """Renders the Streamlit UI for the Team Arrival Statistics Analyzer."""
    st.title("📈 团队到店统计")
    st.markdown("---团队报表分析工具---")

    uploaded_files = st.file_uploader(
        "请上传您的 Excel 报告文件 (.xlsx)", 
        type=["xlsx"], 
        accept_multiple_files=True, 
        key="analyzer_uploader"
    )

    if uploaded_files:
        if st.button("开始分析", type="primary"):
            temp_dir = "./temp_uploaded_files"
            os.makedirs(temp_dir, exist_ok=True)
            
            file_paths = []
            for uploaded_file in uploaded_files:
                temp_file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_paths.append(temp_file_path)

            # Sort files for ordered display
            desired_order = ["次日到达", "次日在住", "次日离店", "后天到达"]
            file_paths.sort(key=lambda p: next((i for i, k in enumerate(desired_order) if k in os.path.basename(p)), len(desired_order)))

            with st.spinner("正在分析中，请稍候..."):
                unknown_codes = Counter()
                summaries = analyze_reports_ultimate(file_paths, unknown_codes)
            
            st.subheader("分析结果")
            for summary in summaries:
                st.write(summary)

            if unknown_codes:
                st.subheader("侦测到的未知房型代码 (请检查是否需要更新规则)")
                for code, count in unknown_codes.items():
                    st.write(f"代码: '{code}' (出现了 {count} 次)")
            
            # --- Cleanup Temporary Files ---
            for f_path in file_paths:
                try:
                    os.remove(f_path)
                except OSError:
                    pass # Ignore errors if file can't be removed
            try:
                if not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except OSError:
                pass

    else:
        st.info("请上传一个或多个 Excel 文件以开始分析。")

    st.markdown("""
    --- 
    #### 使用说明：
    1. 点击 "Browse files" 上传您的 Excel 报告。可以同时上传多个文件。
    2. 文件上传后，点击 "开始分析" 按钮。
    3. 分析结果将按 "次日到达" -> "次日在住" -> "次日离店" 的顺序显示。
    """)

