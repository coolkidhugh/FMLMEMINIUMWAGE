import streamlit as st
import pandas as pd
import unicodedata
import re

# ==============================================================================
# --- Helper Functions ---
# ==============================================================================

def forensic_clean_text(text):
    """Deep cleans a string to remove invisible characters and normalize it."""
    if not isinstance(text, str):
        return text
    try:
        # Normalize to NFKC form to handle full-width/half-width characters
        cleaned_text = unicodedata.normalize('NFKC', text)
    except (TypeError, ValueError):
        return text
    # Remove zero-width spaces and other non-printing chars
    cleaned_text = re.sub(r'[\u200B-\u200D\uFEFF\s\xa0]+', '', cleaned_text)
    return cleaned_text.strip()

def process_and_standardize(df, mapping, case_insensitive=False, room_type_equivalents=None):
    """Standardizes a DataFrame based on user-defined column mappings."""
    if not mapping.get('name'):
        return pd.DataFrame() # Name column is mandatory

    standard_df = pd.DataFrame()
    for col_key, col_name in mapping.items():
        if col_name and col_name in df.columns:
            standard_df[col_key] = df[col_name]

    # --- Date Standardization ---
    def robust_date_parser(series):
        def process_date(date_str):
            if pd.isna(date_str): return pd.NaT
            date_str = str(date_str).strip()
            # Handle MM/DD format, assume a future year for sorting if year is missing
            if re.match(r'^\d{1,2}/\d{1,2}', date_str):
                date_part = date_str.split(' ')[0]
                return f"2025-{date_part.replace('/', '-')}" # Use a consistent placeholder year
            return date_str
        return pd.to_datetime(series.apply(process_date), errors='coerce').dt.strftime('%Y-%m-%d')

    if 'start_date' in standard_df:
        standard_df['start_date'] = robust_date_parser(standard_df['start_date'])
    if 'end_date' in standard_df:
        standard_df['end_date'] = robust_date_parser(standard_df['end_date'])

    # --- Room Type Standardization ---
    if 'room_type' in standard_df and room_type_equivalents:
        standard_df['room_type'] = standard_df['room_type'].astype(str).apply(forensic_clean_text)
        direct_map = {}
        for key, values in room_type_equivalents.items():
            for value in values:
                direct_map[forensic_clean_text(value)] = forensic_clean_text(key)
        standard_df['room_type'] = standard_df['room_type'].replace(direct_map)

    # --- Price Standardization ---
    if 'price' in standard_df:
        standard_df['price'] = pd.to_numeric(standard_df['price'].astype(str).str.strip(), errors='coerce')

    # --- Name Standardization and Explosion (for multiple names in one cell) ---
    standard_df['name'] = standard_df['name'].astype(str).str.split(r'[、,，/]')
    standard_df = standard_df.explode('name')
    standard_df['name'] = standard_df['name'].apply(forensic_clean_text)
    if case_insensitive:
        standard_df['name'] = standard_df['name'].str.lower()

    return standard_df[standard_df['name'] != ''].dropna(subset=['name']).reset_index(drop=True)

def highlight_diff(row, col1, col2):
    """Highlights a row in a DataFrame if values in two columns are different."""
    style = 'background-color: #FFC7CE' # Light red for highlighting
    val1, val2 = row.get(col1), row.get(col2)
    # Highlight if values are different, but not if both are NaN/NaT
    if val1 != val2 and not (pd.isna(val1) and pd.isna(val2)):
        return [style] * len(row)
    return [''] * len(row)

# ==============================================================================
# --- Streamlit UI ---
# ==============================================================================

def run_comparison_app():
    """Renders the Streamlit UI for the Data Comparison Platform."""
    st.title("金陵工具箱 - 比对平台")
    st.info("全新模式：结果以独立的标签页展示，并内置智能日期统一引擎，比对更精准！")

    # Initialize session state
    SESSION_DEFAULTS = {
        'df1': None, 'df2': None, 'df1_name': "", 'df2_name': "",
        'ran_comparison': False
    }
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # --- Step 1: File Upload ---
    st.header("第 1 步: 上传文件")
    if st.button("清空并重置"):
        for key in list(st.session_state.keys()):
            if key in SESSION_DEFAULTS or key.startswith('f1_') or key.startswith('f2_'):
                del st.session_state[key]
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file1 = st.file_uploader("上传名单文件 1", type=['csv', 'xlsx'], key="comp_uploader1")
        if uploaded_file1:
            try:
                st.session_state.df1 = pd.read_excel(uploaded_file1) if uploaded_file1.name.endswith('xlsx') else pd.read_csv(uploaded_file1)
                st.session_state.df1_name = uploaded_file1.name
            except Exception as e:
                st.error(f"读取文件1失败: {e}")
                st.session_state.df1 = None

    with col2:
        uploaded_file2 = st.file_uploader("上传名单文件 2", type=['csv', 'xlsx'], key="comp_uploader2")
        if uploaded_file2:
            try:
                st.session_state.df2 = pd.read_excel(uploaded_file2) if uploaded_file2.name.endswith('xlsx') else pd.read_csv(uploaded_file2)
                st.session_state.df2_name = uploaded_file2.name
            except Exception as e:
                st.error(f"读取文件2失败: {e}")
                st.session_state.df2 = None

    if st.session_state.df1 is not None and st.session_state.df2 is not None:
        # --- Step 2: Column Mapping ---
        st.header("第 2 步: 选择要比对的列 (姓名必选)")
        mapping = {'file1': {}, 'file2': {}}
        cols_to_map = ['name', 'start_date', 'end_date', 'room_type', 'price']
        col_names_zh = ['姓名', '入住日期', '离开日期', '房型', '房价']

        cols1, cols2 = st.columns(2)
        with cols1:
            st.subheader(f"文件 1: {st.session_state.df1_name}")
            df1_cols = [None] + list(st.session_state.df1.columns)
            for key, name_zh in zip(cols_to_map, col_names_zh):
                mapping['file1'][key] = st.selectbox(f"{name_zh}", df1_cols, key=f'f1_{key}')
        with cols2:
            st.subheader(f"文件 2: {st.session_state.df2_name}")
            df2_cols = [None] + list(st.session_state.df2.columns)
            for key, name_zh in zip(cols_to_map, col_names_zh):
                mapping['file2'][key] = st.selectbox(f"{name_zh}", df2_cols, key=f'f2_{key}')

        # --- Step 3: Configuration and Execution ---
        st.header("第 3 步: 配置与执行")
        room_type_equivalents = {}
        if mapping['file1'].get('room_type') and mapping['file2'].get('room_type'):
            with st.expander("高级功能：统一不同名称的房型 (例如：让'大床房'='King Room')"):
                unique_rooms1 = st.session_state.df1[mapping['file1']['room_type']].dropna().astype(str).unique()
                unique_rooms2 = list(st.session_state.df2[mapping['file2']['room_type']].dropna().astype(str).unique())
                for room1 in unique_rooms1:
                    room_type_equivalents[room1] = st.multiselect(f"文件1的“{room1}”等同于:", unique_rooms2, key=f"map_{room1}")
        
        case_insensitive = st.checkbox("比对姓名时忽略大小写/全半角", True)

        if st.button("开始比对", type="primary"):
            if not mapping['file1'].get('name') or not mapping['file2'].get('name'):
                st.error("请确保两边文件的“姓名”都已正确选择。")
            else:
                with st.spinner('正在执行终极比对...'):
                    st.session_state.ran_comparison = True
                    std_df1 = process_and_standardize(st.session_state.df1.copy(), mapping['file1'], case_insensitive)
                    std_df2 = process_and_standardize(st.session_state.df2.copy(), mapping['file2'], case_insensitive, room_type_equivalents)
                    
                    merged_df = pd.merge(std_df1, std_df2, on='name', how='outer', suffixes=('_1', '_2'))
                    
                    cols1_for_check = [f"{c}_1" for c in std_df1.columns if c != 'name']
                    cols2_for_check = [f"{c}_2" for c in std_df2.columns if c != 'name']

                    # --- Result Segregation ---
                    both_exist_mask = merged_df[cols1_for_check].notna().any(axis=1) & merged_df[cols2_for_check].notna().any(axis=1)
                    st.session_state.common_rows = merged_df[both_exist_mask].copy().reset_index(drop=True)
                    
                    only_in_1_mask = merged_df[cols1_for_check].notna().any(axis=1) & merged_df[cols2_for_check].isna().all(axis=1)
                    st.session_state.in_file1_only = merged_df[only_in_1_mask].copy().reset_index(drop=True)
                    
                    only_in_2_mask = merged_df[cols1_for_check].isna().all(axis=1) & merged_df[cols2_for_check].notna().any(axis=1)
                    st.session_state.in_file2_only = merged_df[only_in_2_mask].copy().reset_index(drop=True)

                    st.session_state.compare_cols_keys = [key for key in cols_to_map if key != 'name' and mapping['file1'].get(key) and mapping['file2'].get(key)]
                    
                    # --- Find fully matched rows ---
                    if not st.session_state.common_rows.empty and st.session_state.compare_cols_keys:
                        condition = pd.Series(True, index=st.session_state.common_rows.index)
                        for key in st.session_state.compare_cols_keys:
                            col1, col2 = f'{key}_1', f'{key}_2'
                            condition &= (st.session_state.common_rows[col1] == st.session_state.common_rows[col2]) | \
                                         (st.session_state.common_rows[col1].isna() & st.session_state.common_rows[col2].isna())
                        st.session_state.matched_df = st.session_state.common_rows[condition]
                    else:
                        st.session_state.matched_df = st.session_state.common_rows.copy()

    # --- Step 4: Display Results ---
    if st.session_state.ran_comparison:
        st.header("第 4 步: 查看比对结果")
        
        tab_name_map = {'start_date': "入住日期", 'end_date': "离开日期", 'room_type': "房型", 'price': "房价"}
        tab_list = ["结果总览"] + [tab_name_map[key] for key in st.session_state.get('compare_cols_keys', [])]
        tabs = st.tabs(tab_list)

        with tabs[0]: # Overview Tab
            st.subheader("宏观统计")
            stat_cols = st.columns(3)
            matched_count = len(st.session_state.get('matched_df', []))
            only_1_count = len(st.session_state.get('in_file1_only', []))
            only_2_count = len(st.session_state.get('in_file2_only', []))
            
            stat_cols[0].metric("信息完全一致", matched_count)
            stat_cols[1].metric(f"仅 '{st.session_state.df1_name}' 有", only_1_count)
            stat_cols[2].metric(f"仅 '{st.session_state.df2_name}' 有", only_2_count)

            st.subheader("人员名单详情")
            with st.expander(f"查看 {only_1_count} 条仅存在于 '{st.session_state.df1_name}' 的名单"):
                if only_1_count > 0:
                    display_cols = ['name'] + [c for c in cols_to_map if f"{c}_1" in st.session_state.in_file1_only.columns]
                    display_df = st.session_state.in_file1_only[[f"{c}_1" if c != 'name' else 'name' for c in display_cols]]
                    display_df.columns = ['姓名'] + [col_names_zh[cols_to_map.index(c)] for c in display_cols if c != 'name']
                    st.dataframe(display_df)
                else:
                    st.write("没有人员。")
            
            with st.expander(f"查看 {only_2_count} 条仅存在于 '{st.session_state.df2_name}' 的名单"):
                if only_2_count > 0:
                    display_cols = ['name'] + [c for c in cols_to_map if f"{c}_2" in st.session_state.in_file2_only.columns]
                    display_df = st.session_state.in_file2_only[[f"{c}_2" if c != 'name' else 'name' for c in display_cols]]
                    display_df.columns = ['姓名'] + [col_names_zh[cols_to_map.index(c)] for c in display_cols if c != 'name']
                    st.dataframe(display_df)
                else:
                    st.write("没有人员。")

        # Detail Tabs for each compared column
        for i, key in enumerate(st.session_state.get('compare_cols_keys', [])):
            with tabs[i + 1]:
                col1_name, col2_name = f'{key}_1', f'{key}_2'
                display_name = tab_name_map[key]
                st.subheader(f"【{display_name}】比对详情")
                
                common_rows = st.session_state.get('common_rows', pd.DataFrame())
                if not common_rows.empty:
                    compare_df = common_rows[['name', col1_name, col2_name]].copy()
                    compare_df.rename(columns={'name': '姓名', col1_name: f'文件1 - {display_name}', col2_name: f'文件2 - {display_name}'}, inplace=True)
                    
                    # Filter for rows with differences
                    mismatch_df = compare_df[compare_df[f'文件1 - {display_name}'] != compare_df[f'文件2 - {display_name}']]
                    
                    st.metric(f"存在差异的记录数", len(mismatch_df))

                    styled_df = compare_df.style.apply(highlight_diff, col1=f'文件1 - {display_name}', col2=f'文件2 - {display_name}', axis=1)
                    st.dataframe(styled_df, use_container_width=True)
                else:
                    st.info("两个文件中没有共同的人员可供进行细节比对。")

