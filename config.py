# --- Centralized Configuration File for Jinling Toolbox ---

# Building and Room Type Definitions
# Used by Analyzer and Data Analysis apps
JINLING_ROOM_TYPES = [
    'DETN', 'DKN', 'DKS', 'DQN', 'DQS', 'DSKN', 'DSTN', 'DTN', 'EKN', 'EKS',
    'ESN', 'ESS', 'ETN', 'ETS', 'FSB', 'FSC', 'FSN', 'OTN', 'PSA', 'PSB',
    'RSN', 'SKN', 'SQN', 'SQS', 'SSN', 'SSS', 'STN', 'STS'
]

YATAI_ROOM_TYPES = [
    'JDEN', 'JDKN', 'JDKS', 'JEKN', 'JESN', 'JESS', 'JETN', 'JETS', 'JKN',
    'JLKN', 'JTN', 'JTS', 'PSC', 'PSD', 'VCKD', 'VCKN'
]

# Combined list for OCR App validation
ALL_ROOM_CODES = JINLING_ROOM_TYPES + YATAI_ROOM_TYPES + [
    "SITN", "JEN", "JIS", "JTIN" # Additional known codes
]


# OCR Tool Configuration
TEAM_TYPE_MAP = { "CON": "会议团", "FIT": "散客团", "WA": "婚宴团" }
DEFAULT_TEAM_TYPE = "旅游团"


# Common Phrases App Configuration
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


# Ctrip Tools Configuration

# Column mappings for Ctrip Date Comparison App
CTRIP_DATE_COMPARE_SYSTEM_COLS = {'id': '预订号', 'checkin': '到达', 'checkout': '离开'}
CTRIP_DATE_COMPARE_CTRIP_COLS = {'id': '预定号', 'checkin': '入住日期', 'checkout': '离店日期'}


# Column mappings for Ctrip Audit App
CTRIP_AUDIT_CTRIP_COLS_MAP = {
    '订单号': ['订单号', '订单号码'],
    '确认号': ['确认号', '酒店确认号', '确订号'],
    '客人姓名': ['客人姓名', '姓名', '入住人', '宾客姓名'],
    '到达': ['到达', '入住日期', '到店日期'],
    '离开': ['离开', '离店日期']
}
CTRIP_AUDIT_SYSTEM_COLS_MAP = {
    '预订号': ['预订号', '预定号'],
    '第三方预定号': ['第三方预定号', '第三方预订号'],
    '姓名': ['姓名', '名字', '客人姓名', '宾客姓名'],
    '离开': ['离开', '离店日期'],
    '房号': ['房号'],
    '状态': ['状态']
}

