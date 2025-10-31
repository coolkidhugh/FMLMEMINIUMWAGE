# ==============================================================================
# --- [全局配置] ---
# ==============================================================================
APP_VERSION = "2.7.1" # 操，又他妈的升一次版本号
APP_NAME = "金陵工具箱"

# --- [OCR工具] 配置 ---
TEAM_TYPE_MAP = {
    "CON": "会议团",
    "FIT": "散客团",
    "WA": "婚宴团"
}
DEFAULT_TEAM_TYPE = "旅游团"
ALL_ROOM_CODES = [
    "DETN", "DKN", "DQN", "DQS", "DSKN", "DSTN", "DTN", "EKN", "EKS", "ESN", "ESS",
    "ETN", "ETS", "FSN", "FSB", "FSC", "OTN", "PSA", "PSB", "RSN", "SKN",
    "SQN", "SQS", "SSN", "SSS", "STN", "STS", "JDEN", "JDKN", "JDKS", "JEKN",
    "JESN", "JESS", "JETN", "JETS", "JKN", "JLKN", "JTN", "JTS", "PSC", "PSD",
    "VCKN", "VCKD", "SITN", "JEN", "JIS", "JTIN"
]

# --- [团队到店统计] 配置 ---
JINLING_ROOM_TYPES = [
    'DETN', 'DKN', 'DKS', 'DQN', 'DQS', 'DSKN', 'DSTN', 'DTN',
    'EKN', 'EKS', 'ESN', 'ESS', 'ETN', 'ETS', 'FSB', 'FSC', 'FSN',
    'STN', 'STS', 'SKN', 'RSN', 'SQS', 'SQN'
]
YATAI_ROOM_TYPES = [
    'JDEN', 'JDKN', 'JDKS', 'JEKN', 'JESN', 'JESS', 'JETN', 'JETS',
    'JKN', 'JLKN', 'JTN', 'JTS', 'VCKD', 'VCKN'
]

# --- [携程审单 & 对日期] 配置 ---
CTRIP_AUDIT_COLUMN_MAP_CTRIP = {
    '订单号': ['订单号', '订单号码'],
    '确认号': ['确认号', '酒店确认号', '确订号'],
    '客人姓名': ['客人姓名', '姓名', '入住人', '宾客姓名'],
    '到达': ['到达', '入住日期', '到店日期'],
    '离开': ['离开', '离店日期']
}
CTRIP_AUDIT_COLUMN_MAP_SYSTEM = {
    '预订号': ['预订号', '预定号'],
    '第三方预定号': ['第三方预定号', '第三方预订号'],
    '姓名': ['姓名', '名字', '客人姓名', '宾客姓名'],
    '离开': ['离开', '离店日期'],
    '房号': ['房号'],
    '状态': ['状态']
}
CTRIP_DATE_COMPARE_SYSTEM_COLS = {'id': '预订号', 'checkin': '到达', 'checkout': '离开'}
CTRIP_DATE_COMPARE_CTRIP_COLS = {'id': '预定号', 'checkin': '入住日期', 'checkout': '离店日期'}

# --- [连住权益审核] 配置 ---
PROMO_CHECKER_COLUMN_MAP = {
    '订单号': ['确认号', '订单号', '预订号', '预定号'],
    '备注': ['备注', 'Remark', '备注信息'],
    '房类': ['房类', '房型', 'Room Type']
}

# --- [美团邮件审核] 配置 ---
MEITUAN_SYSTEM_COLUMN_MAP = {
    '预订号': ['预订号', '预定号'],
    '第三方预定号': ['第三方预定号', '第三方预订号'],
    '姓名': ['姓名', '名字', '客人姓名', '宾客姓名'],
    '到达': ['到达', '入住日期', '到店日期'],
    '离开': ['离开', '离店日期'],
    '房号': ['房号'],
    '状态': ['状态']
}

# --- [备注关键字查找] 配置 ---
UPGRADE_FINDER_COLUMN_MAP = {
    '预订号': ['预订号', '预定号'],
    '第三方预定号': ['第三方预定号', '第三方预订号'],
    '最近修改人': ['最近修改人', '修改人', 'Last Modifier', '操作员'],
    '备注': ['备注', 'Remark', '备注信息']
}

# --- [携程PDF审单] 配置 (操，新加的) ---
CTRIP_PDF_SYSTEM_COLUMN_MAP = {
    '姓名': ['姓名', '名字', '客人姓名', '宾客姓名'],
    '房类': ['房类', '房型', 'Room Type'],
    '到达': ['到达', '入住日期', '到店日期'],
    '离开': ['离开', '离店日期'],
    '预订号': ['预订号', '预定号'],
    '第三方预订号': ['第三方预定号', '第三方预订号']
}

# --- [常用话术] 配置 ---
COMMON_PHRASES = [
    "CA RM TO CREDIT FM",
    "免预付,房费及3000元以内杂费转淘宝 FM",
    "房费转携程宏睿 FM",
    "房价保密,房费转华为 FM",
    "房费转淘宝 FM",
    "CA RM TO 兰艳(109789242)金陵卡 FM",
    "CA RM TO AGODA FM",
    "CA RM TO CREDIT CARD FM XX-XX/XX(卡号/有效期XX/XX)",
    "房费转微信 FM",
    "房费预付杂费自理FM"
]

