import streamlit as st

def run_morning_briefing_app():
    """Renders the Streamlit UI for the Morning Briefing Generator."""
    st.title("金陵工具箱 - 早班话术生成器")
    
    st.subheader("数据输入")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 金陵楼数据")
        jl_occupancy = st.number_input("昨日出租率 (%)", key="jl_occ", format="%.1f", value=82.4)
        jl_revenue = st.number_input("收入 (元)", key="jl_rev", format="%.2f", value=247173.40)
        jl_adr = st.number_input("平均房价 (元)", key="jl_adr", format="%.2f", value=550.50)
        jl_guests = st.number_input("总人数", key="jl_guests", value=673, step=1)
        jl_jinhaiwan = st.number_input("金海湾人数", key="jl_jinhaiwan", value=572, step=1)
    with col2:
        st.markdown("#### 亚太楼数据")
        yt_occupancy = st.number_input("昨日出租率 (%)", key="yt_occ", format="%.1f", value=83.9)
        yt_revenue = st.number_input("收入 (元)", key="yt_rev", format="%.2f", value=232385.50)
        yt_adr = st.number_input("平均房价 (元)", key="yt_adr", format="%.2f", value=719.50)
        yt_guests = st.number_input("总人数", key="yt_guests", value=485, step=1)
        yt_jia = st.number_input("家餐厅人数", key="yt_jia", value=323, step=1)

    st.markdown("---")
    st.subheader("其他数据")
    col3, col4 = st.columns(2)
    with col3:
        onbook_jl = st.number_input("目前On Book出租率 - 金陵楼 (%)", key="ob_jl", format="%.1f", value=65.5)
        onbook_yt = st.number_input("目前On Book出租率 - 亚太楼 (%)", key="ob_yt", format="%.1f", value=57.7)
    with col4:
        mini_prog_yesterday = st.number_input("小程序订房 - 昨日 (间夜)", key="mp_yest", value=26, step=1)
        mini_prog_today = st.number_input("小程序订房 - 今日 (间夜)", key="mp_today", value=19, step=1)
    
    if st.button("生成话术", type="primary"):
        briefing = (
            f"昨日金陵楼出租率{jl_occupancy}%，收入{jl_revenue:,.2f}元，平均房价{jl_adr:,.2f}元，"
            f"总人数{jl_guests}人，金海湾{jl_jinhaiwan}人。"
            f"亚太商务楼出率{yt_occupancy}%，收入{yt_revenue:,.2f}元，平均房价{yt_adr:,.2f}元，"
            f"总人数{yt_guests}人，家餐厅{yt_jia}人。"
            f"目前on book出租率金陵楼{onbook_jl}%，亚太商务楼{onbook_yt}%。"
            f"小程序订房昨日{mini_prog_yesterday}间夜，今日{mini_prog_today}间夜。"
        )
        st.subheader("生成的话术")
        st.success(briefing)
        st.code(briefing)

