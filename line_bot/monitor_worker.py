"""外部 Cron 使用的單次監控入口。"""
import sys
from .app import check_for_updates


def run():
    print('[Worker] 執行單次監控', file=sys.stderr)
    check_for_updates()


if __name__ == '__main__':
    run()
