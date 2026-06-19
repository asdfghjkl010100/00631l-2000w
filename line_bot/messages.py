"""LINE Bot 訊息模板"""
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))


def format_number(n):
    if n is None: return "--"
    if abs(n) >= 1_0000_0000: return f"{n / 1_0000_0000:.2f}億"
    if abs(n) >= 1_0000: return f"{n / 1_0000:.2f}萬"
    return f"{n:.2f}"


def format_pct(n):
    if n is None: return "--"
    s = "+" if n >= 0 else ""
    return f"{s}{n:.2f}%"


def build_status_message(cv, msd, update_time=None, weekly=None):
    ts = update_time or datetime.now(TZ).strftime("%Y/%m/%d %H:%M")
    lines = [
        "📊 *台股國運基金 · 即時總覽*",
        f"🕐 {ts}", "",
        f"💰 合資總資產：{format_number(cv.get('ta', 0))}",
        f"💵 帳上現金：{format_number(cv.get('ca', 0))}",
        f"📈 股票市值：{format_number(cv.get('sv', 0))}",
        f"📉 00631L 現價：{format_number(cv.get('sp', 0))}",
        f"📦 總持股：{format_number(cv.get('sh', 0))} 股",
    ]
    if weekly:
        ota, nta = weekly.get("ta", 0), cv.get("ta", 0)
        if ota and nta and ota != nta:
            d = nta - ota; p = (d / ota) * 100
            s1 = "+" if d > 0 else ""; s2 = "+" if p > 0 else ""
            lines.append(f"📊 與上周比：{s1}{format_number(d)}（{s2}{p:.2f}%）")
        osp, nsp = weekly.get("sp", 0), cv.get("sp", 0)
        if osp and nsp and osp != nsp:
            d = nsp - osp; p = (d / osp) * 100
            s1 = "+" if d > 0 else ""; s2 = "+" if p > 0 else ""
            lines.append(f"📉 股價變化：{s1}{format_number(d)}（{s2}{p:.2f}%）")
    lines.extend(["", "💡 輸入「查詢」看更多細節"])
    return "\n".join(lines)


def build_member_detail(name, records, total_invest, total_value, roi):
    lines = [
        f"👤 *{name} 投資明細*",
        f"總投入：{format_number(total_invest)}",
        f"目前市值：{format_number(total_value)}",
        f"報酬率：{format_pct(roi)}", "",
        "*歷次記錄（最近 5 筆）*",
    ]
    for r in records[-5:]:
        lines.append(f"  {r.get('d', '?')}：投入{format_number(r.get('a', 0))}，單位數{r.get('n', 0):.2f}")
    return "\n".join(lines)
