"""
LINE Bot 訊息模板
"""
from datetime import datetime


def format_number(n: float) -> str:
    """數字格式化，同前端 FN 邏輯"""
    if n is None:
        return '--'
    if abs(n) >= 1_0000_0000:  # 億
        return f'{n / 1_0000_0000:.2f}億'
    if abs(n) >= 1_0000:  # 萬
        return f'{n / 1_0000:.2f}萬'
    return f'{n:.2f}'


def format_pct(n: float) -> str:
    if n is None:
        return '--'
    sign = '+' if n >= 0 else ''
    return f'{sign}{n:.2f}%'


def build_status_message(cv: dict, msd: list, update_time: str = None) -> str:
    """建立基金總覽推播訊息"""
    ts = update_time or datetime.now().strftime('%Y/%m/%d %H:%M')

    total_asset = cv.get('ta', 0)
    cash = cv.get('ca', 0)
    stock_value = cv.get('sv', 0)
    stock_price = cv.get('sp', 0)
    shares = cv.get('sh', 0)

    lines = [
        '📊 *台股國運基金 · 即時總覽*',
        f'🕐 更新時間：{ts}',
        '',
        f'💰 合資總資產：{format_number(total_asset)}',
        f'💵 帳上現金：{format_number(cash)}',
        f'📈 股票市值：{format_number(stock_value)}',
        f'📉 00631L 現價：{format_number(stock_price)}',
        f'📦 總持股：{format_number(shares)} 股',
    ]

    if msd:
        lines.extend(['', '👥 *團員概覽*'])
        for m in msd[:10]:
            name = m.get('n', '?')
            invest = m.get('i', 0)
            value = m.get('v', 0)
            roi = m.get('r', 0)
            lines.append(f'  {name}：投入{format_number(invest)} → {format_number(value)}（{format_pct(roi)}）')

    lines.extend(['', '💡 輸入「查詢」看更多細節'])
    return '\n'.join(lines)


def build_member_detail(name: str, records: list, total_invest: float, total_value: float, roi: float) -> str:
    """建立團員明細訊息"""
    lines = [
        f'👤 *{name} 投資明細*',
        f'總投入：{format_number(total_invest)}',
        f'目前市值：{format_number(total_value)}',
        f'報酬率：{format_pct(roi)}',
        '',
        '*歷次記錄（最近 5 筆）*',
    ]
    for r in records[-5:]:
        lines.append(f'  {r.get('d', '?')}：投入{format_number(r.get('a', 0))}，單位數{r.get('n', 0):.2f}')

    return '\n'.join(lines)


def build_price_alert(old_price: float, new_price: float, change_pct: float) -> str:
    """建立股價變動通知"""
    direction = '📈 上漲' if change_pct > 0 else '📉 下跌'
    return (
        f'🔔 *00631L 股價變動通知*\n'
        f'{direction} {abs(change_pct):.2f}%\n'
        f'原價：{old_price:.2f} → 現價：{new_price:.2f}'
    )


def build_deposit_notification(name: str, amount: float, date: str) -> str:
    """建立入金通知"""
    return (
        f'💰 *入金通知*\n'
        f'團員 {name} 在 {date} 入金 {format_number(amount)}'
    )
