"""LINE Bot — 自動推播 + 查詢指令"""
import sys
import os
import json
from datetime import datetime, timedelta
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
#  上周快照管理
# ===================
WEEKLY_FILE = "weekly_snapshot.json"


def load_weekly_snapshot() -> dict | None:
    if os.path.exists(WEEKLY_FILE):
        try:
            with open(WEEKLY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_weekly_snapshot(cv: dict):
    data = {"timestamp": datetime.now().isoformat(), "cv": cv}
    with open(WEEKLY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print("[Weekly] 已儲存本周快照", file=sys.stderr)


def maybe_rotate_weekly(cv: dict):
    """每週一儲存快照作為上周基準"""
    snap = load_weekly_snapshot()
    if snap is None:
        save_weekly_snapshot(cv)
        return
    saved = datetime.fromisoformat(snap["timestamp"])
    # 如果距離上次儲存超過 6 天，更新快照
    if datetime.now() - saved > timedelta(days=6):
        save_weekly_snapshot(cv)


def get_weekly_cv() -> dict | None:
    snap = load_weekly_snapshot()
    if snap:
        return snap.get("cv")
    return None


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


CHECK_COUNT = 0

@app.route("/health", methods=["GET"])
def health():
    import time
    since = f"{time.time() - LAST_CHECK:.0f}秒前" if LAST_CHECK else "尚未執行"
    return {"status": "ok", "checks": CHECK_COUNT, "last": since, "sheets": DEBUG_SHEETS}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    text = event.message.text.strip()
    if text in ("查詢", "狀態", "總覽", "status"):
        try:
            data = fetch_all_data()
            weekly = get_weekly_cv()
            msg = build_status_message(data["cv"], data["msd"], weekly=weekly)
        except Exception as e:
            msg = f"⚠️ 無法取得資料：{e}"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=msg)])
        )


# ===================
#  定期監控
# ===================
def check_for_updates():
    global CHECK_COUNT, DEBUG_SHEETS
    CHECK_COUNT += 1
    try:
        new_fp = compute_cache_fingerprint()
    except Exception as e:
        DEBUG_SHEETS = f"指紋錯誤：{e}"
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
        maybe_rotate_weekly(new_data.get("cv", {}))
        print(f"[Monitor] 快取已更新（{new_fp[:12]}...）", file=sys.stderr)
    except Exception as e:
        print(f"[Monitor] 快取更新失敗：{e}", file=sys.stderr)


LAST_CHECK = None
DEBUG_SHEETS = "未測試"

def _run_loop():
    import time
    global LAST_CHECK
    print(f"[Monitor] 排程器啟動，每 {Config.MONITOR_INTERVAL_SECONDS} 秒檢查一次", file=sys.stderr)
    while True:
        try:
            check_for_updates()
        except Exception as ex:
            print(f"[Monitor] 執行錯誤：{ex}", file=sys.stderr)
        LAST_CHECK = time.time()
        time.sleep(Config.MONITOR_INTERVAL_SECONDS)

def start_scheduler():
    import threading
    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()


start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
