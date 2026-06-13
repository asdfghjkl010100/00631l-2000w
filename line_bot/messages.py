"""LINE Bot ????"""
from datetime import datetime, timezone, timedelta

def format_number(n):
    if n is None: return "--"
    if abs(n) >= 1_0000_0000: return f"{n / 1_0000_0000:.2f}?"
    if abs(n) >= 1_0000: return f"{n / 1_0000:.2f}?"
    return f"{n:.2f}"

def format_pct(n):
    if n is None: return "--"
    s = "+" if n >= 0 else ""
    return f"{s}{n:.2f}%"

def build_status_message(cv, msd, update_time=None, weekly=None):
    ts = update_time or datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    lines = [
        "?? *?????? ? ????*",
        f"?? {ts}", "",
        f"?? ??????{format_number(cv.get('ta', 0))}",
        f"?? ?????{format_number(cv.get('ca', 0))}",
        f"?? ?????{format_number(cv.get('sv', 0))}",
        f"?? 00631L ???{format_number(cv.get('sp', 0))}",
        f"?? ????{format_number(cv.get('sh', 0))} ?",
    ]
    if weekly:
        ota, nta = weekly.get("ta", 0), cv.get("ta", 0)
        if ota and nta and ota != nta:
            d = nta - ota
            p = (d / ota) * 100
            s1 = "+" if d > 0 else ""
            s2 = "+" if p > 0 else ""
            lines.append(f"?? ?????{s1}{format_number(d)}?{s2}{p:.2f}%?")
        osp, nsp = weekly.get("sp", 0), cv.get("sp", 0)
        if osp and nsp and osp != nsp:
            d = nsp - osp
            p = (d / osp) * 100
            s1 = "+" if d > 0 else ""
            s2 = "+" if p > 0 else ""
            lines.append(f"?? ?????{s1}{format_number(d)}?{s2}{p:.2f}%?")
    lines.extend(["", "?? ???????????"])
    return "\n".join(lines)

def build_member_detail(name, records, total_invest, total_value, roi):
    lines = [
        f"?? *{name} ????*",
        f"????{format_number(total_invest)}",
        f"?????{format_number(total_value)}",
        f"????{format_pct(roi)}", "",
        "*??????? 5 ??*",
    ]
    for r in records[-5:]:
        lines.append(f"  {r.get('d', '?')}???{format_number(r.get('a', 0))}????{r.get('n', 0):.2f}")
    return "\n".join(lines)
