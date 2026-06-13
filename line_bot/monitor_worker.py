"""
獨立監控 Worker — 在伺服器背景執行定期檢查
使用方式：python -m linebot.monitor_worker
"""
import time
import sys
from .config import Config
from .sheets_monitor import (
    compute_cache_fingerprint,
    load_cache,
    save_cache,
    fetch_all_data,
    build_update_message,
)
from .app import push_message, check_for_updates


def run():
    print('[Worker] 監控 Worker 啟動', file=sys.stderr)
    # 先執行一次
    check_for_updates()
    while True:
        time.sleep(Config.MONITOR_INTERVAL_SECONDS)
        check_for_updates()


if __name__ == '__main__':
    run()
