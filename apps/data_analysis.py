import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import traceback
from datetime import timedelta, date
from utils import to_excel # 操，从 utils 导入 to_excel

# ==============================================================================
# --- [数据分析] 核心逻辑 & UI ---
# ==============================================================================

@st.cache_data
def process_data_analysis(uploaded_file):
    """处理上传的Excel文件，为数据分析做准备。"""
    try:
        df = pd.read_excel(uploaded_file)
        # 操，统一列名为大写并去除空格
        df.columns = [str(col).strip().upper() for col in df.columns]

        # 操，定义需要重命名的列和检查的列
        rename_map = {
            'ROOM CATEGORY': '房类', 'ROOMS': '房数', 'ARRIVAL': '到达',
            'DEPARTURE': '离开', 'RATE': '房价', 'MARKET': '市场码', 'STATUS': '状态'
        }
        # 操，先统一可能的名字
        possible_names = {
            '房类': ['ROOM CATEGORY', '房类', '房型'],
            '房数': ['ROOMS', '房数'],
            '到达': ['ARRIVAL', '到达'],
            '离开': ['DEPARTURE', '离开'],
            '房价': ['RATE', '房价'],
            '市场码': ['MARKET', '市场码'],
            '状态': ['STATUS', '状态']
        }
        actual_rename_map = {}
        required_cols_standard = ['状态', '房类', '房数', '到达', '离开', '房价', '市场码']
        missing_cols = []

        # 操，动态查找列名并准备重命名
        for standard_name in required_cols_standard:
            found = False
            for possible_name in possible_names.get(standard_name, [standard_name]):
                 # 操，更鲁棒地检查列名是否存在（忽略大小写和空格）
                cleaned_possible_name = possible_name.strip().upper()
                matching_cols = [col for col in df.columns if col.strip().upper() == cleaned_possible_name]
                if matching_cols:
                    actual_col_name = matching_cols[0] # 取第一个匹配的
                    if actual_col_name != standard_name:
                         actual_rename_map[actual_col_name] = standard_name
                    found = True
                    break
            if not found:
                missing_cols.append(standard_name)

        if missing_cols:
            st.error(f"上传的文件缺少以下必要的列: {', '.join(missing_cols)}。请检查文件。")
            return None, None

        df.rename(columns=actual_rename_map, inplace=True)

        # --- 操，开始处理数据 ---
        df['到达_str'] = df['到达'].astype(str).str.split(' ').str[0]
        df['离开_str'] = df['离开'].astype(str).str.split(' ').str[0]

        # 操，尝试多种日期格式
        df['到达'] = pd.to_datetime(df['到达_str'], format='%y/%m/%d', errors='coerce')
        df['离开'] = pd.to_datetime(df['离开_str'], format='%y/%m/%d', errors='coerce')
        # 操，如果第一种格式不行，试试 YYYY/MM/DD
        df['到达'] = df['到达'].fillna(pd.to_datetime(df['到达_str'], format='%Y/%m/%d', errors='coerce'))
        df['离开'] = df['离开'].fillna(pd.to_datetime(df['离开_str'], format='%Y/%m/%d', errors='coerce'))
         # 操，再不行，试试 YYYY-MM-DD
        df['到达'] = df['到达'].fillna(pd.to_datetime(df['到达_str'], format='%Y-%m-%d', errors='coerce'))
        df['离开'] = df['离开'].fillna(pd.to_datetime(df['离开_str'], format='%Y-%m-%d', errors='coerce'))

        df['房价'] = pd.to_numeric(df['房价'], errors='coerce')
        df['房数'] = pd.to_numeric(df['房数'], errors='coerce')
        df['市场码'] = df['市场码'].astype(str).str.strip()
        df['状态'] = df['状态'].astype(str).str.strip().str.upper() # 操，状态转大写去空格

        # 操，删除关键列为空的行
        df.dropna(subset=['到达', '离开', '房价', '房数', '房类', '状态'], inplace=True)
        if df.empty:
            st.warning("清理后没有有效的数据行。请检查文件内容。")
            return pd.DataFrame(), pd.DataFrame() # 返回空的DataFrame

        df['房数'] = df['房数'].astype(int)

        # 操，楼层分配（这里可以用 config.py 里的列表，但为了独立先写死）
        jinling_rooms = ['DETN', 'DKN', 'DQN', 'DQS', 'DSKN', 'DSTN', 'DTN', 'EKN', 'EKS', 'ESN', 'ESS', 'ETN', 'ETS', 'FSB', 'FSC', 'FSN', 'OTN', 'PSA', 'PSB', 'RSN', 'SKN', 'SQN', 'SQS', 'SSN', 'SSS', 'STN', 'STS']
        yatai_rooms = ['JDEN', 'JDKN', 'JDKS', 'JEKN', 'JESN', 'JESS', 'JETN', 'JETS', 'JKN', 'JLKN', 'JTN', 'JTS', 'PSC', 'PSD', 'VCKD', 'VCKN']
        room_to_building = {code: "金陵楼" for code in jinling_rooms}
        room_to_building.update({code: "亚太楼" for code in yatai_rooms})

        df['房类'] = df['房类'].astype(str).str.strip().str.upper() # 房类也转大写去空格
        df = df[df['房类'].isin(jinling_rooms + yatai_rooms)].copy() # 只保留已知房型
        if df.empty:
            st.warning("文件中没有找到金陵楼或亚太楼的有效房型记录。")
            return pd.DataFrame(), pd.DataFrame()

        df['楼层'] = df['房类'].map(room_to_building)
        df['入住天数'] = (df['离开'].dt.normalize() - df['到达'].dt.normalize()).dt.days

        df_for_arrivals = df.copy() # 用于到店离店统计的原始数据

        # 操，准备每日在住数据，只选 R 和 I 状态且入住天数大于0
        df_for_stays = df[(df['入住天数'] > 0) & (df['状态'].isin(['R', 'I']))].copy()

        if df_for_stays.empty:
            st.warning("没有找到状态为 'R' 或 'I' 且入住天数大于0的记录，无法生成每日在住矩阵。")
            return df_for_arrivals, pd.DataFrame() # 返回空的在住DataFrame

        # 操，展开数据
        df_repeated = df_for_stays.loc[df_for_stays.index.repeat(df_for_stays['入住天数'])]
        date_offset = df_repeated.groupby(level=0).cumcount()
        df_repeated['住店日'] = df_repeated['到达'].dt.normalize() + pd.to_timedelta(date_offset, unit='D')
        expanded_df = df_repeated.drop(columns=['到达', '离开', '入住天数', '到达_str', '离开_str']).reset_index(drop=True)

        return df_for_arrivals, expanded_df.copy()

    except Exception as e:
        st.error(f"处理Excel文件时发生错误: {e}")
        st.error(f"技术细节: {traceback.format_exc()}")
        return None, None


def run_data_analysis_app():
    """运行数据分析驾驶舱的Streamlit界面。"""
    st.title("金陵工具箱 - 数据分析驾驶舱")
    uploaded_file = st.file_uploader("上传您的Excel文件 (包含状态, 房类, 房数, 到达, 离开, 房价, 市场码)", type=["xlsx", "xls"], key="data_analysis_uploader")

    if not uploaded_file:
        st.info("请上传您的Excel文件以开始分析。")
        return

    original_df, expanded_df = process_data_analysis(uploaded_file)

    if original_df is None: # 操，处理数据时就出错了
        return
    if original_df.empty and (expanded_df is None or expanded_df.empty):
        # st.warning("上传的文件中没有找到有效的数据记录，或未能处理成功。请检查文件内容和格式。") # process_data_analysis 里已经有提示了
        return

    st.success(f"文件 '{uploaded_file.name}' 上传并处理成功！")

    # --- 1. 每日到店/离店房数统计 ---
    st.header("1. 每日到店/离店房数统计")
    with st.expander("点击展开或折叠", expanded=True):
        all_statuses = sorted(original_df['状态'].unique()) if not original_df.empty else []

        # --- 到店 ---
        st.subheader("到店房数统计")
        default_arrival_statuses = [s for s in ['R'] if s in all_statuses] # 操，只把文件里有的 R 作为默认
        selected_arrival_statuses = st.multiselect("选择到店状态", options=all_statuses, default=default_arrival_statuses, key="arrival_status_select")

        # 操，尝试获取最早到达日期作为默认值
        default_arrival_date_str = ""
        if not original_df.empty and '到达' in original_df.columns and not original_df['到达'].isna().all():
             try:
                 default_arrival_date_str = pd.to_datetime(original_df['到达'].min()).strftime('%Y/%m/%d')
             except Exception:
                 default_arrival_date_str = date.today().strftime('%Y/%m/%d') # 出错就用今天

        arrival_dates_str = st.text_input("输入到店日期 (用逗号分隔, 格式: YYYY/MM/DD)", default_arrival_date_str, key="arrival_date_input")

        arrival_summary = pd.DataFrame()
        if arrival_dates_str and selected_arrival_statuses:
            try:
                date_strings = [d.strip() for d in arrival_dates_str.split(',') if d.strip()]
                selected_arrival_dates = [pd.to_datetime(d, format='%Y/%m/%d').date() for d in date_strings]
                arrival_df = original_df[(original_df['状态'].isin(selected_arrival_statuses)) & (original_df['到达'].dt.date.isin(selected_arrival_dates))].copy()
                if not arrival_df.empty:
                    arrival_summary = arrival_df.groupby([arrival_df['到达'].dt.date, '楼层'])['房数'].sum().unstack(fill_value=0)
                    arrival_summary.index.name = "到店日期"
                    st.dataframe(arrival_summary)
                else:
                    st.warning(f"在所选日期和状态内没有找到到店记录。")
            except ValueError:
                st.error("到店日期格式不正确，请输入 YYYY/MM/DD 格式。")
            except Exception as e:
                st.error(f"处理到店数据时出错: {e}")

        # --- 离店 ---
        st.subheader("离店房数统计")
        # 操，这里是出问题的！只把实际存在的作为默认！
        default_departure_statuses = [s for s in ['R', 'I', 'O'] if s in all_statuses]
        # 操，如果文件里一个都没有，默认就是空列表
        selected_departure_statuses = st.multiselect("选择离店状态", options=all_statuses, default=default_departure_statuses, key="departure_status_select")

        # 操，尝试获取最早离开日期作为默认值
        default_departure_date_str = ""
        if not original_df.empty and '离开' in original_df.columns and not original_df['离开'].isna().all():
             try:
                 default_departure_date_str = pd.to_datetime(original_df['离开'].min()).strftime('%Y/%m/%d')
             except Exception:
                 default_departure_date_str = date.today().strftime('%Y/%m/%d')

        departure_dates_str = st.text_input("输入离店日期 (用逗号分隔, 格式: YYYY/MM/DD)", default_departure_date_str, key="departure_date_input")
        departure_summary = pd.DataFrame()
        if departure_dates_str and selected_departure_statuses:
            try:
                date_strings = [d.strip() for d in departure_dates_str.split(',') if d.strip()]
                selected_departure_dates = [pd.to_datetime(d, format='%Y/%m/%d').date() for d in date_strings]
                departure_df = original_df[(original_df['状态'].isin(selected_departure_statuses)) & (original_df['离开'].dt.date.isin(selected_departure_dates))].copy()
                if not departure_df.empty:
                    departure_summary = departure_df.groupby([departure_df['离开'].dt.date, '楼层'])['房数'].sum().unstack(fill_value=0)
                    departure_summary.index.name = "离店日期"
                    st.dataframe(departure_summary)
                else:
                    st.warning(f"在所选日期和状态内没有找到离店记录。")
            except ValueError:
                st.error("离店日期格式不正确，请输入 YYYY/MM/DD 格式。")
            except Exception as e:
                st.error(f"处理离店数据时出错: {e}")

        # --- 下载按钮 ---
        if not arrival_summary.empty or not departure_summary.empty:
            df_to_download_arrival_departure = {}
            if not arrival_summary.empty: df_to_download_arrival_departure["到店统计"] = arrival_summary
            if not departure_summary.empty: df_to_download_arrival_departure["离店统计"] = departure_summary
            excel_data_ad = to_excel(df_to_download_arrival_departure)
            st.download_button(label="下载到店/离店统计结果为 Excel", data=excel_data_ad, file_name="arrival_departure_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_ad")

    # --- 2. 每日在住房间按价格分布矩阵 ---
    st.markdown("---")
    st.header("2. 每日在住房间按价格分布矩阵 (仅统计状态 R 和 I)")
    if expanded_df is None or expanded_df.empty:
        st.warning("没有可用于生成在住价格分布矩阵的数据。请确保上传的文件包含状态为 R 或 I 且入住天数大于0的记录。")
    else:
        with st.expander("点击展开或折叠", expanded=True):
            default_stay_date = ""
            if '住店日' in expanded_df.columns and not expanded_df['住店日'].isna().all():
                try:
                    default_stay_date = pd.to_datetime(expanded_df['住店日'].min()).strftime('%Y/%m/%d')
                except Exception:
                     default_stay_date = date.today().strftime('%Y/%m/%d')

            stay_dates_str = st.text_input("输入住店日期 (用逗号分隔, 格式: YYYY/MM/DD)", default_stay_date, key="stay_date_input")

            selected_stay_dates = []
            if stay_dates_str:
                try:
                    stay_date_strings = [d.strip() for d in stay_dates_str.split(',') if d.strip()]
                    selected_stay_dates = [pd.to_datetime(d, format='%Y/%m/%d').date() for d in stay_date_strings]
                except ValueError:
                    st.error("住店日期格式不正确，请输入 YYYY/MM/DD 格式。")
                    st.stop() # 操，格式错了就别往下跑了
                except Exception as e:
                    st.error(f"处理住店日期时出错: {e}")
                    st.stop()

            all_market_codes_stay = sorted(expanded_df['市场码'].dropna().unique()) if '市场码' in expanded_df.columns else []
            selected_market_codes = st.multiselect("选择市场码 (可多选)", options=all_market_codes_stay, default=all_market_codes_stay, key="market_code_select")

            st.subheader("自定义价格区间")
            col1, col2 = st.columns(2)
            with col1: price_bins_jinling_str = st.text_input("金陵楼价格区间 (例: <401, 401-480, >599)", "<401, 401-480, 481-500, 501-550, 551-599, >599", key="bins_jl")
            with col2: price_bins_yatal_str = st.text_input("亚太楼价格区间 (例: <501, 501-600, >799)", "<501, 501-600, 601-699, 700-749, 750-799, >799", key="bins_yt")

            def parse_price_bins(price_bins_str):
                """解析价格区间字符串"""
                if not price_bins_str or not price_bins_str.strip(): return [], [] # 返回空列表
                intervals = []
                bins_set = set([-np.inf, np.inf]) # 操，包含无穷
                try:
                    for item in price_bins_str.split(','):
                        item = item.strip()
                        if item.startswith('<'):
                            upper = float(re.search(r'\d+(\.\d+)?', item).group())
                            intervals.append({'lower': -np.inf, 'upper': upper, 'label': f'< {upper}'})
                            bins_set.add(upper)
                        elif item.startswith('>'):
                            lower = float(re.search(r'\d+(\.\d+)?', item).group())
                            intervals.append({'lower': lower, 'upper': np.inf, 'label': f'> {lower}'})
                            bins_set.add(lower)
                        elif '-' in item:
                            parts = item.split('-')
                            lower, upper = float(parts[0]), float(parts[1])
                            if lower >= upper: raise ValueError(f"价格区间 '{item}' 无效：下限必须小于上限。")
                            intervals.append({'lower': lower, 'upper': upper, 'label': f'{lower}-{upper}'})
                            bins_set.add(lower)
                            bins_set.add(upper)
                        else:
                            # 操，尝试解析单个数字作为一个区间
                            single_val = float(item)
                            intervals.append({'lower': single_val, 'upper': single_val, 'label': f'{single_val}'})
                            bins_set.add(single_val)

                    # 操，重新排序和生成标签/bins
                    sorted_bins = sorted(list(bins_set))
                    final_bins = []
                    final_labels = []

                    # 处理最低边界
                    if sorted_bins[0] == -np.inf:
                        if len(sorted_bins) > 1 and sorted_bins[1] != np.inf:
                            final_bins.append(sorted_bins[1])
                            final_labels.append(f'< {sorted_bins[1]}')
                        else: # 只有无穷的情况
                           pass
                    else: # 没有负无穷，第一个bin是具体数字
                         final_bins.append(sorted_bins[0])
                         final_labels.append(f'< {sorted_bins[0]}') # 小于等于第一个数字

                    # 处理中间区间
                    for i in range(len(sorted_bins) - 1):
                        lower = sorted_bins[i]
                        upper = sorted_bins[i+1]
                        if lower != -np.inf and upper != np.inf:
                            # 操，检查是否为单个数字区间
                            is_single_value_interval = any(inv for inv in intervals if inv['lower'] == lower and inv['upper'] == lower and inv['lower'] != -np.inf)
                            if lower == upper or is_single_value_interval:
                                 # 如果列表中已经有这个标签，就不加了，避免重复
                                if f'{lower}' not in final_labels:
                                     final_bins.append(lower) # 加一个bin点
                                     final_labels.append(f'{lower}')
                            elif lower < upper:
                                 # 如果bins里已经有upper，就不加了
                                if upper not in final_bins: final_bins.append(upper)
                                final_labels.append(f'{lower}-{upper}')

                    # 处理最高边界
                    if sorted_bins[-1] != np.inf:
                         # 如果最后一个bin不是无穷大，那么添加 > last_bin 的区间
                         # 如果标签里还没加过
                         if f'> {sorted_bins[-1]}' not in final_labels:
                            final_bins.append(np.inf) # 加无穷大作为最后一个bin点
                            final_labels.append(f'> {sorted_bins[-1]}')
                    # else: # 如果最后一个已经是inf，在处理中间区间时应该已经包含了 > xxx

                    # 操，去重 final_bins 并排序
                    final_bins = sorted(list(set(final_bins)))
                     # 操，确保labels数量比bins少一个
                    if len(final_labels) == len(final_bins):
                        # 可能只有一个区间 < inf 或者 > -inf
                         if len(final_bins) == 2 and final_bins[0] == -np.inf and final_bins[1] == np.inf:
                              final_labels = ["所有价格"]
                         elif len(final_bins) > 1 : # 一般情况
                              final_bins = final_bins # 保持不变
                              # 操，尝试根据bins重建labels
                              new_labels = []
                              if final_bins[0] == -np.inf:
                                   if final_bins[1] != np.inf: new_labels.append(f'< {final_bins[1]}')
                                   start_index = 1
                              else:
                                   new_labels.append(f'<= {final_bins[0]}') # 第一个区间
                                   start_index = 0

                              for i in range(start_index, len(final_bins) - 1):
                                   lower_b = final_bins[i]
                                   upper_b = final_bins[i+1]
                                   if upper_b != np.inf:
                                        new_labels.append(f'{lower_b}-{upper_b}')
                                   else:
                                        new_labels.append(f'> {lower_b}')
                                        break # 到无穷大就结束了
                              final_labels = new_labels

                    elif len(final_labels) != len(final_bins) -1 :
                         # 操，数量对不上，可能有问题，返回空
                         st.warning(f"解析价格区间 '{price_bins_str}' 后，标签和边界数量不匹配 ({len(final_labels)} labels, {len(final_bins)} bins)。请检查格式。")
                         return [], []


                    return final_bins, final_labels

                except Exception as e:
                    st.error(f"解析价格区间 '{price_bins_str}' 时出错: {e}。请检查格式。")
                    return [], [] # 返回空列表

            bins_jinling, labels_jinling = parse_price_bins(price_bins_jinling_str)
            bins_yatal, labels_yatal = parse_price_bins(price_bins_yatal_str)

            dfs_to_download_matrix = {}
            if selected_stay_dates and selected_market_codes:
                matrix_df_filtered = expanded_df[(expanded_df['住店日'].dt.date.isin(selected_stay_dates)) & (expanded_df['市场码'].isin(selected_market_codes))].copy()

                if not matrix_df_filtered.empty:
                    buildings = sorted(matrix_df_filtered['楼层'].unique())
                    for building in buildings:
                        st.subheader(f"{building} - 在住房间分布")
                        building_df = matrix_df_filtered[matrix_df_filtered['楼层'] == building].copy()
                        bins, labels = (bins_jinling, labels_jinling) if building == "金陵楼" else (bins_yatal, labels_yatal)

                        if not building_df.empty and bins and labels:
                             # 操，确保房价是数字
                            building_df['房价'] = pd.to_numeric(building_df['房价'], errors='coerce')
                            building_df.dropna(subset=['房价'], inplace=True)

                            if not building_df.empty:
                                # 操，使用 pd.cut 进行分箱
                                # include_lowest=True 确保包含最低值, right=True 表示区间右闭合 (e.g., (401, 480])
                                # 但是第一个区间 (< x) 需要特殊处理，pd.cut默认左开右闭，除非 include_lowest
                                # 最后一个区间 (> y) 也是
                                try:
                                     # 操，根据bins第一个和最后一个是否是无穷大来调整 include_lowest 和 right
                                     _include_lowest = bins[0] == -np.inf
                                     _right = True # 默认右闭合

                                     building_df['价格区间'] = pd.cut(building_df['房价'], bins=bins, labels=labels, right=_right, include_lowest=_include_lowest, ordered=False) # ordered=False 避免后续问题

                                     # 操，处理NaN （价格不在任何区间内）
                                     building_df['价格区间'] = building_df['价格区间'].astype(str).fillna('未分类') # 转成字符串，NaN填'未分类'

                                     pivot_table = pd.pivot_table(building_df,
                                                                 index=building_df['住店日'].dt.date, # 使用dt.date确保按日期聚合
                                                                 columns='价格区间',
                                                                 values='房数',
                                                                 aggfunc='sum',
                                                                 fill_value=0)

                                     if not pivot_table.empty:
                                        # 操，计算每日总计
                                        pivot_table['每日总计'] = pivot_table.sum(axis=1)
                                        # 操，把列按照标签顺序排一下（如果标签是从bins生成的）
                                        ordered_columns = [l for l in labels if l in pivot_table.columns]
                                        if '未分类' in pivot_table.columns: ordered_columns.append('未分类')
                                        ordered_columns.append('每日总计')
                                        pivot_table = pivot_table[ordered_columns]

                                        st.dataframe(pivot_table.sort_index())
                                        dfs_to_download_matrix[f"{building}_在住分布"] = pivot_table
                                     else:
                                        st.info(f"在 {building} 中，没有找到符合所选条件的在住记录。")

                                except ValueError as ve:
                                     if "Overlapping bins" in str(ve):
                                         st.error(f"价格区间设置错误: 区间 '{price_bins_jinling_str if building == '金陵楼' else price_bins_yatal_str}' 存在重叠，请修改。Bins: {bins}")
                                     elif "Bin edges must be unique" in str(ve):
                                          st.error(f"价格区间设置错误: 区间边界 '{price_bins_jinling_str if building == '金陵楼' else price_bins_yatal_str}' 存在重复值，请修改。Bins: {bins}")
                                     else:
                                          st.error(f"为 {building} 生成价格分布时出错: {ve}. Bins: {bins}, Labels: {labels}")

                                except Exception as e:
                                     st.error(f"为 {building} 生成价格分布时发生未知错误: {e}. Bins: {bins}, Labels: {labels}")
                                     st.error(f"Traceback: {traceback.format_exc()}")
                            else:
                                 st.info(f"在 {building} 中，筛选后没有带有效房价的在住记录。")
                        elif not building_df.empty:
                             st.warning(f"未成功解析 {building} 的价格区间，无法生成分布矩阵。请检查区间格式。")
                        else:
                             st.info(f"在 {building} 中，没有找到符合所选条件的在住记录。")
                else:
                    st.warning(f"在所选日期和市场码范围内没有找到状态为 R 或 I 的在住记录。")

            # --- 下载按钮 ---
            if dfs_to_download_matrix:
                excel_data_matrix = to_excel(dfs_to_download_matrix)
                st.download_button(label="下载价格分布矩阵为 Excel", data=excel_data_matrix, file_name="price_matrix_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_matrix")

