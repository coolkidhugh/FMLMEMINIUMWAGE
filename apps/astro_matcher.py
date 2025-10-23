import streamlit as st
import datetime
import random

# ==============================================================================
# --- 星座匹配 & 温柔寄语生成器 ---
# ==============================================================================

# 嘻嘻，敬爱的总经理是这个星座哦~
GM_SIGN = "天蝎座"
GM_BIRTH_MONTH = 10 # 备注一下月份~

# 可爱的星座宝宝们的日期范围~ (月, 日)
ZODIAC_SIGNS = {
    "白羊座": ((3, 21), (4, 19)), "金牛座": ((4, 20), (5, 20)),
    "双子座": ((5, 21), (6, 21)), "巨蟹座": ((6, 22), (7, 22)),
    "狮子座": ((7, 23), (8, 22)), "处女座": ((8, 23), (9, 22)),
    "天秤座": ((9, 23), (10, 23)), "天蝎座": ((10, 24), (11, 22)),
    "射手座": ((11, 23), (12, 21)), "摩羯座": ((12, 22), (1, 19)),
    "水瓶座": ((1, 20), (2, 18)), "双鱼座": ((2, 19), (3, 20))
}

# 哇~ 您和天蝎座总经理的缘分指数~ (仅供参考哦，开心就好~)
COMPATIBILITY_WITH_SCORPIO = {
    "天蝎座": {"level": "灵魂的契合~", "desc": "哇哦！同为天蝎座的你们，仿佛能读懂彼此的心声呢！一起携手并进，一定能创造无限可能！和总经理真是天造地设的伙伴呀！"},
    "双鱼座": {"level": "梦幻般的组合~", "desc": "同为水象星座，真是心有灵犀一点通！您能理解总经理深邃的内心，他也能欣赏您的善良与温柔。好好加油，未来可期哦！"},
    "巨蟹座": {"level": "温暖的依靠~", "desc": "水象星座的默契真是太棒啦！您能给予总经理踏实的温暖，他也能成为您坚实的后盾。共同努力，一定能成就一番事业！"},
    "摩羯座": {"level": "可靠的伙伴~", "desc": "土象与水象的结合，稳稳的幸福！你们都那么务实且有追求，目标高度一致。紧跟总经理的步伐，美好的未来在招手哦！"},
    "处女座": {"level": "细致的和谐~", "desc": "土与水的交融，追求完美的您遇上富有洞察力的他，简直太棒了！您可以帮助总经理把工作做得尽善尽美。用心表现，他会看到的！"},
    "金牛座": {"level": "需要磨合的缘分~", "desc": "两位都是很有原则的小可爱呢。都着眼于实际，但也可能需要更多沟通来避免小小的固执。多倾听总经理的想法，关系会更融洽哒~"},
    "天秤座": {"level": "需要磨合的缘分~", "desc": "风象的灵动遇上水象的深沉，需要用心经营哦。您向往和谐，总经理则很有主见。多主动沟通，表达您的真诚，关系会越来越好的！"},
    "双子座": {"level": "有趣的挑战~", "desc": "深沉的他遇上多变的您，像是来自不同星球的小王子呢。在总经理面前，展现您沉稳可靠的一面，用努力证明自己吧！"},
    "射手座": {"level": "有趣的挑战~", "desc": "热情如火的您遇上深邃如水的他，需要找到平衡点哦。您热爱自由，总经理则有规划。在他面前多展现稳重，一起为目标奋斗吧！"},
    "白羊座": {"level": "有趣的挑战~", "desc": "直率的您遇上心思深邃的他，或许会碰撞出不一样的火花。收敛一点点冲动，多学习总经理的智慧，会收获很多哦！"},
    "狮子座": {"level": "需要互相欣赏~", "desc": "两位都是闪闪发光的存在呢！都很有领导力。在总经理面前，适当展现您的尊重与配合，强强联合才能更厉害呀！"},
    "水瓶座": {"level": "需要互相欣赏~", "desc": "神秘的他遇上独特的您，思维方式都很特别呢！在总经理面前展现您务实合作的一面，求同存异也很棒哦！"}
}

# 温柔的每日寄语~ 分级别的哦，还有通用的祝福~
FLATTERY_PHRASES = {
    "灵魂的契合~": [
        "心有灵犀一点通！和总经理如此默契，今天({date})的合作一定会超级顺利，成果满满！",
        "真是最佳拍档！总经理的远见卓识加上您的聪慧，今天({date})定能乘风破浪！",
        "一个眼神就能明白彼此！和总经理这份难得的默契，让今天({date})的任何挑战都变得轻松起来！"
    ],
    "梦幻般的组合~": [
        "简直是完美的组合！和总经理这么合拍，今天({date})一定会充满幸运和喜悦，事半功倍！",
        "感觉太棒啦！和总经理的气场如此和谐，今天({date})一定能心想事成，万事如意！",
        "能得到总经理({gm_sign})这样优秀领导的青睐，真是太荣幸了！今天({date})也要元气满满，不负这份默契！"
    ],
     "温暖的依靠~": [
        "温暖又可靠的组合！和总经理一起努力，今天({date})一定能互相支持，共同进步！",
        "默契十足，合作无间！今天({date})也要和总经理一起，为了共同的目标加油！",
        "能与总经理({gm_sign})这样体贴的领导共事，感觉真好！今天({date})也要努力贡献自己的力量！"
    ],
    "可靠的伙伴~": [
        "目标一致，步调统一！和总经理这么合拍，今天({date})的工作效率一定超级高！",
        "感觉跟着总经理，浑身充满了力量！今天({date})也要努力跟上总经理({gm_sign})的步伐，一起加油！",
        "踏实的组合最让人安心！和总经理一起，今天({date})一定能够稳扎稳打，收获满满！"
    ],
     "细致的和谐~": [
        "细心加持，事半功倍！和总经理一起工作，总能把细节做到极致，今天({date})也要继续保持！",
        "能为总经理({gm_sign})分忧解难，是我的荣幸！今天({date})要更加细心，做好每一件事！",
        "追求完美的路上有您真好！和总经理一起，今天({date})一定能把工作完成得漂漂亮亮！"
    ],
    "需要磨合的缘分~": [
        "虽然思考方式略有不同，但我们目标相同呀！今天({date})要更多地向总经理({gm_sign})请教，共同进步！",
        "沟通是桥梁~ 今天({date})要更积极地和总经理交流想法，相信一定能找到最佳方案！",
        "互相学习，共同成长！今天({date})要努力发挥自己的长处，全力支持总经理的工作！"
    ],
    "有趣的挑战~": [
        "保持谦逊，不断学习！总经理({gm_sign})身上有太多值得学习的地方，今天({date})也要认真观察，努力提升！",
        "差异也能带来启发！今天({date})要虚心领会总经理的指导，让自己变得更优秀！",
        "努力将是最好的证明！今天({date})要更加专注和投入，用出色的工作成果来回应总经理的期待！"
    ],
    "需要互相欣赏~": [
        "保持敬佩，努力追赶！总经理({gm_sign})的气场真是让人敬佩，今天({date})要更加努力，向榜样看齐！",
        "团队协作最重要！今天({date})一定紧密配合总经理的安排，贡献自己的一份力！",
        "换位思考，增进理解！今天({date})要多尝试理解总经理的决策思路，更好地完成工作！"
    ],
    "通用": [ # 嘻嘻，不知道说什么的时候可以用这些~
        "今天({date})又是充满希望的一天！要和总经理一起加油鸭！",
        "今天({date})阳光真好，心情美美的~ 努力工作，不辜负总经理({gm_sign})的期望哦！",
        "新的一天({date})，新的起点！在总经理的带领下，我们一定能越来越棒！",
        "感受总经理({gm_sign})的榜样力量，今天({date})也要努力发光发热！"
    ]
}

def get_zodiac_sign(month, day):
    """根据月份和日期，温柔地找出您的星座~"""
    for sign, ((start_m, start_d), (end_m, end_d)) in ZODIAC_SIGNS.items():
        if (month == start_m and day >= start_d) or (month == end_m and day <= end_d):
            return sign
        # 跨年的摩羯座宝宝要特殊照顾一下~
        if sign == "摩羯座" and (month == 12 or month == 1):
             if month == 12 and day >= 22: return sign
             if month == 1 and day <= 19: return sign
    return None # 如果日期不太对，就先空着哦~

def run_astro_matcher_app():
    """运行温柔的星座匹配器界面~"""
    st.title(f"金陵工具箱 - 星座情缘小助手") # 改个更可爱的名字~
    st.caption(f"偷偷看看您和总经理 ({GM_SIGN}) 的星座小秘密~ 再送您几句暖心寄语哦...")

    input_type = st.radio("请选择您的输入方式哦:", ("直接选星座", "输入生日(月/日)"), key="astro_input_type")

    user_sign = None
    if input_type == "直接选星座":
        sign_list = list(ZODIAC_SIGNS.keys())
        # 加一个可爱的提示~
        user_sign = st.selectbox("请选择您的星座吧~:", ["请选择..."] + sign_list, key="astro_sign_select")
        if user_sign == "请选择...":
            user_sign = None
    else:
        col1, col2 = st.columns(2)
        with col1:
            # 默认值设为0，提示用户输入
            month = st.number_input("您的出生月份是几月呀?", min_value=0, max_value=12, value=0, step=1, key="astro_month_input", format="%d")
        with col2:
            day = st.number_input("您的出生日期是几号呢?", min_value=0, max_value=31, value=0, step=1, key="astro_day_input", format="%d")

        # 只有在输入有效月份和日期时才计算
        if month > 0 and day > 0:
            try:
                # 随便找个年份（比如2000年，闰年）来验证日期是否存在
                 datetime.date(2000, month, day)
                 user_sign = get_zodiac_sign(month, day)
                 if user_sign:
                     st.info(f"哇~ 根据您的生日，您是可爱的 **{user_sign}** 呢！")
                 else:
                     # 这个情况理论上很少见，除非日期正好在边界外
                     st.warning("哎呀，好像日期有点特别，没找到对应的星座呢，请再检查一下哦~")
            except ValueError:
                st.error("呜呜，输入的日期好像不太对呢，月份和日期的组合有问题哦~")
                user_sign = None # 日期无效就清空星座

    # 只有在获取到星座后才显示按钮
    if user_sign:
        if st.button("看看我们的缘分 & 今日份鼓励~", type="primary"):
            st.markdown("---")
            st.subheader(f"您 ({user_sign}) 与 总经理 ({GM_SIGN}) 的星座情缘~")

            compatibility = COMPATIBILITY_WITH_SCORPIO.get(user_sign)
            if compatibility:
                level = compatibility["level"]
                desc = compatibility["desc"]

                # 根据匹配度用不同的颜色和图标~
                if "契合" in level or "组合" in level or "依靠" in level:
                    st.success(f"**缘分指数: {level}** ✨")
                elif "伙伴" in level or "和谐" in level:
                    st.info(f"**缘分指数: {level}** 😊")
                elif "磨合" in level:
                    st.warning(f"**缘分指数: {level}** 🤔")
                else: # 挑战 or 欣赏
                    st.error(f"**缘分指数: {level}** 💖") # 用爱心表示需要更多理解~

                st.write(desc)

                # --- 开始生成温柔的寄语 ---
                today_str = datetime.date.today().strftime("%Y年%m月%d日") # 获取当天日期
                possible_phrases = FLATTERY_PHRASES.get(level, []) + FLATTERY_PHRASES["通用"] # 获取对应级别和通用的
                if possible_phrases:
                    # 随机选1-2句~
                    num_phrases = random.randint(1, 2)
                    selected_phrases = random.sample(possible_phrases, min(num_phrases, len(possible_phrases)))

                    st.markdown("---")
                    st.subheader("给您今天的温柔鼓励:")
                    for phrase in selected_phrases:
                        # 替换里面的占位符~
                        formatted_phrase = phrase.format(date=today_str, gm_sign=GM_SIGN)
                        st.markdown(f"- {formatted_phrase}")
                else:
                     st.write("（哎呀，今天好像没有特别的寄语呢...）")

            else:
                st.error("呜呜，好像出了一点小问题，找不到您的星座匹配信息呢。")
    # 如果没选星座或日期无效，给个提示
    elif input_type == "直接选星座" and not user_sign:
        st.info("请先在上面选择您的星座哦~")
    elif input_type != "直接选星座" and not user_sign:
        st.info("请输入您的生日月份和日期，才能看到匹配结果哦~")

