import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """LINE Bot 設定"""
    # LINE Messaging API
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')

    # 推播目標（群組或用戶 ID）
    # 如果設定，會推播到此目標；否則只回應 Webhook 事件
    LINE_GROUP_ID = os.getenv('LINE_GROUP_ID', '')
    LINE_USER_ID = os.getenv('LINE_USER_ID', '')

    # Google Sheets CSV 網址（與 index.html 同步）
    CSV_CORE = os.getenv(
        'CSV_CORE',
        'https://docs.google.com/spreadsheets/d/e/2PACX-1vTd2t7A2bMmI5cPucJcWiQ93stLTWs1Kmho_3hu_lXkT1uono0NkGMF0tPfW5c9UhEoJvKczPLJ0o82/pub?gid=1130608596&single=true&output=csv'
    )
    CSV_MS = os.getenv(
        'CSV_MS',
        'https://docs.google.com/spreadsheets/d/e/2PACX-1vTd2t7A2bMmI5cPucJcWiQ93stLTWs1Kmho_3hu_lXkT1uono0NkGMF0tPfW5c9UhEoJvKczPLJ0o82/pub?gid=284048808&single=true&output=csv'
    )
    CSV_WN = os.getenv(
        'CSV_WN',
        'https://docs.google.com/spreadsheets/d/e/2PACX-1vTd2t7A2bMmI5cPucJcWiQ93stLTWs1Kmho_3hu_lXkT1uono0NkGMF0tPfW5c9UhEoJvKczPLJ0o82/pub?gid=1167489800&single=true&output=csv'
    )

    # 成員 CSV（gid 列表）
    MEMBER_GIDS = {
        '淡定ㄉ圍觀': '1138157330',
        '隔壁ㄉ老王': '22779118',
        '真的很敷衍': '1862214689',
        '樂天小腳腳': '2107206751',
        '太空軍校生': '1339484185',
        '育仔': '330914372',
    }

    # 監控間隔（秒）
    MONITOR_INTERVAL_SECONDS = int(os.getenv('MONITOR_INTERVAL', '300'))
    SCHEDULE_TOKEN = os.getenv('SCHEDULE_TOKEN', '')

    # 快取檔（記錄上次的資料指紋，用來偵測變更）
    CACHE_FILE = os.getenv('CACHE_FILE', 'data_cache.json')
