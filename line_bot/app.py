"""LINE Bot — 自動推播 + 查詢指令"""
import sys
import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, PushMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .config import Config
from .sheets_monitor import fetch_all_data, compute_cache_fingerprint, load_cache, save_cache, build_update_message
from .messages import build_status_message

app = Flask(__name__)

configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)


def push_message(text: str):
    to = Config.LINE_GROUP_ID or Config.LINE_USER_ID
    if to:
        messaging_api.push_message(PushMessageRequest(to=to, messages=[TextMessage(text=text)]))


# ===================
#  Webhook
# ===================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    try:
        handler.handle(request.get_data(as_text=True), signature)
    except InvalidSignatureError:
        abort(400)
    except Exception:
        pass
    return "OK"


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "台股國運基金 LINE Bot 運行中"}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """只處理「查詢」指令"""
    text = event.message.text.strip()
    if text in ("查詢", "狀態", "總覽", "status"):
        try:
            data = fetch_all_data()
            msg = build_status_message(data["cv"], data["msd"])
        except Exception as e:
            msg = f"⚠️ 無法取得資料：{e}"
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=msg)],
            )
        )


# ===================
#  定期監控
# ===================
def check_for_updates():
    try:
        new_fp = compute_cache_fingerprint()
    except Exception as e:
        print(f"[Monitor] 無法取得指紋：{e}", file=sys.stderr)
        return
    cache = load_cache()
    old_fp = cache.get("fingerprint", "")
    if old_fp and old_fp != new_fp:
        print("[Monitor] 偵測到資料變更！", file=sys.stderr)
        try:
            new_data = fetch_all_data()
            msg = build_update_message(cache.get("data", {}), new_data)
            if msg:
                push_message(msg)
                print("[Monitor] 已推播更新通知", file=sys.stderr)
        except Exception as e:
            print(f"[Monitor] 推播失敗：{e}", file=sys.stderr)
    try:
        new_data = fetch_all_data()
        save_cache({"fingerprint": new_fp, "data": new_data})
        print(f"[Monitor] 快取已更新（{new_fp[:12]}...）", file=sys.stderr)
    except Exception as e:
        print(f"[Monitor] 快取更新失敗：{e}", file=sys.stderr)


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    sched = BackgroundScheduler()
    sched.add_job(check_for_updates, "interval", seconds=Config.MONITOR_INTERVAL_SECONDS, id="sheets_monitor")
    sched.start()
    print(f"[Monitor] 排程器啟動，每 {Config.MONITOR_INTERVAL_SECONDS} 秒檢查一次", file=sys.stderr)


# 啟動排程器（gunicorn 匯入時一併啟動）
start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
