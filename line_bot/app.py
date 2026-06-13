"""
LINE Bot 主程式 — Flask Webhook + 定期監控
"""
import json
import sys
import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .config import Config
from .sheets_monitor import (
    fetch_all_data,
    compute_cache_fingerprint,
    load_cache,
    save_cache,
    build_update_message,
    fetch_core_data,
    fetch_member_summary,
)
from .messages import build_status_message, build_member_detail

# Flask App
app = Flask(__name__)

# LINE Bot 初始化
configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)


def push_message(text: str):
    """主動推播訊息到指定的群組或用戶"""
    if Config.LINE_GROUP_ID:
        messaging_api.push_message(
            PushMessageRequest(
                to=Config.LINE_GROUP_ID,
                messages=[TextMessage(text=text)],
            )
        )
    elif Config.LINE_USER_ID:
        messaging_api.push_message(
            PushMessageRequest(
                to=Config.LINE_USER_ID,
                messages=[TextMessage(text=text)],
            )
        )


# ===================
#  Webhook 路由
# ===================
@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    import sys
    print(f'[Webhook] Body: {body}', file=sys.stderr)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception:
        # 空事件（如 Webhook 驗證）不會有 events 欄位
        pass
    return 'OK'


@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'message': '台股國運基金 LINE Bot 運行中'}


@app.route('/status', methods=['GET'])
def status_endpoint():
    """手動觸發查詢目前狀態（用於測試）"""
    try:
        data = fetch_all_data()
        msg = build_status_message(data['cv'], data['msd'])
        return {'status': 'ok', 'message': msg}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.route('/push', methods=['POST'])
def push_endpoint():
    """手動觸發推播（用於測試或 cron）"""
    try:
        data = fetch_all_data()
        msg = build_status_message(data['cv'], data['msd'])
        push_message(msg)
        return {'status': 'ok', 'message': '已推播'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """處理使用者輸入的文字訊息"""
    text = event.message.text.strip()
    reply_token = event.reply_token

    if text in ('查詢', '狀態', '總覽', 'status'):
        try:
            data = fetch_all_data()
            msg = build_status_message(data['cv'], data['msd'])
        except Exception as e:
            msg = f'⚠️ 無法取得資料：{e}'
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=msg)],
            )
        )
    elif text.startswith('查'):
        # 「查 名字」查詢特定團員
        name = text[1:].strip()
        if name:
            from .config import Config
            if name in Config.MEMBER_GIDS:
                try:
                    from .sheets_monitor import fetch_member_detail, _safe_float
                    records = fetch_member_detail(Config.MEMBER_GIDS[name])
                    total_invest = sum(r['a'] for r in records)
                    total_value = records[-1]['cu'] * (records[-1]['n'] if records else 0) if records else 0
                    roi = ((total_value - total_invest) / total_invest * 100) if total_invest > 0 else 0
                    msg = build_member_detail(name, records, total_invest, total_value, roi)
                except Exception as e:
                    msg = f'⚠️ 查詢 {name} 失敗：{e}'
            else:
                msg = f'⚠️ 找不到團員「{name}」'
        else:
            msg = '請輸入「查 團員名稱」，例如：查 淡定ㄉ圍觀'
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=msg)],
            )
        )
    elif text in ('說明', 'help', '指令'):
        msg = (
            '📋 *台股國運基金 LINE Bot 指令*\n\n'
            '📊 輸入「查詢」或「狀態」→ 基金總覽\n'
            '👤 輸入「查 團員名稱」→ 團員明細\n'
            '   e.g. 查 淡定ㄉ圍觀\n'
            '   e.g. 查 隔壁ㄉ老王\n'
            '❓ 輸入「說明」或「help」→ 此訊息\n\n'
            '🔄 資料更新時會自動推播通知'
        )
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=msg)],
            )
        )
    else:
        msg = '⚠️ 不支援的指令。輸入「說明」查看可用指令。'
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=msg)],
            )
        )


# ===================
#  定期監控（使用 APScheduler）
# ===================
def check_for_updates():
    """定期檢查資料是否有更新，有的話推播通知"""
    try:
        new_fp = compute_cache_fingerprint()
    except Exception as e:
        print(f'[Monitor] 無法取得指紋：{e}', file=sys.stderr)
        return

    cache = load_cache()
    old_fp = cache.get('fingerprint', '')

    if old_fp and old_fp != new_fp:
        print('[Monitor] 偵測到資料變更！', file=sys.stderr)
        try:
            old_data = cache.get('data', {})
            new_data = fetch_all_data()
            msg = build_update_message(old_data, new_data)
            if msg:
                push_message(msg)
                print('[Monitor] 已推播更新通知', file=sys.stderr)
            else:
                print('[Monitor] 無需推播的變更', file=sys.stderr)
        except Exception as e:
            print(f'[Monitor] 推播失敗：{e}', file=sys.stderr)

    # 更新快取
    try:
        new_data = fetch_all_data()
        save_cache({'fingerprint': new_fp, 'data': new_data})
        print(f'[Monitor] 快取已更新（{new_fp[:12]}...）', file=sys.stderr)
    except Exception as e:
        print(f'[Monitor] 快取更新失敗：{e}', file=sys.stderr)


def start_scheduler():
    """啟動 APScheduler 定期檢查"""
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_for_updates,
        'interval',
        seconds=Config.MONITOR_INTERVAL_SECONDS,
        id='sheets_monitor',
        name='Google Sheets 變更偵測',
    )
    scheduler.start()
    print(f'[Monitor] 排程器已啟動，每 {Config.MONITOR_INTERVAL_SECONDS} 秒檢查一次', file=sys.stderr)


# ===================
#  應用程式入口
# ===================
if __name__ == '__main__':
    # 啟動排程器
    start_scheduler()
    # 啟動 Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
