"""
Google Sheets 資料擷取與變更偵測
"""
import json
import hashlib
import csv
import io
import os
import requests
from datetime import datetime, timezone, timedelta

# 台灣時區
TZ = timezone(timedelta(hours=8))
from .config import Config


def _fetch_csv(url: str) -> str:
    """抓取 CSV 原始文字"""
    resp = requests.get(url, timeout=30, headers={'Cache-Control': 'no-cache'})
    resp.encoding = 'utf-8'
    return resp.text


def _parse_csv(text: str) -> list:
    """解析 CSV 回傳二維陣列"""
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader]


def _fingerprint(text: str) -> str:
    """計算內容指紋（SHA256）"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fetch_core_data() -> dict:
    """擷取核心資料（合資總資產、現金、股價、持股數）"""
    text = _fetch_csv(Config.CSV_CORE)
    rows = _parse_csv(text)
    cv = {'ta': 0, 'ca': 0, 'sv': 0, 'sp': 0, 'sh': 0}
    for r in rows:
        if len(r) < 2:
            continue
        key = r[0].strip()
        val = _safe_float(r[1])
        if key == '合資總資產':
            cv['ta'] = val
        elif key == '帳上現金':
            cv['ca'] = val
        elif key == '00631L 現價':
            cv['sp'] = val
            cv['sv'] = val * cv['sh']
        elif key == '合資總持股數':
            cv['sh'] = val
            cv['sv'] = cv['sp'] * val
    return cv


def fetch_member_summary() -> list:
    """擷取團員摘要資料"""
    text = _fetch_csv(Config.CSV_MS)
    rows = _parse_csv(text)
    members = []
    for i, r in enumerate(rows):
        if i == 0 or len(r) < 6:
            continue
        members.append({
            'n': r[0].strip(),
            'i': _safe_float(r[1]),
            'u': _safe_float(r[2]),
            'v': _safe_float(r[3]),
            'r': _safe_float(r[4]),
            'm': _safe_float(r[5]),
        })
    return members


def fetch_member_detail(gid: str) -> list:
    """擷取單一團員詳細投資記錄"""
    base = Config.CSV_CORE.rsplit('gid=', 1)[0]
    url = f'{base}gid={gid}&single=true&output=csv'
    text = _fetch_csv(url)
    rows = _parse_csv(text)
    records = []
    cum = 0.0
    for i, r in enumerate(rows):
        if i == 0:
            continue
        if len(r) < 4:
            continue
        ds = r[0].strip()
        amount = _safe_float(r[1])
        if amount <= 0:
            continue
        nav = _safe_float(r[2])
        units = _safe_float(r[3])
        cum += units
        records.append({
            'd': ds,
            'a': amount,
            'n': nav,
            'u': units,
            'cu': cum,
        })
    return records


def fetch_all_data() -> dict:
    """一次擷取所有資料"""
    cv = fetch_core_data()
    msd = fetch_member_summary()
    return {'cv': cv, 'msd': msd}


def compute_cache_fingerprint() -> str:
    """計算所有 CSV 的整體指紋（用來偵測是否有任何變更）"""
    texts = []
    try:
        texts.append(_fetch_csv(Config.CSV_CORE))
        texts.append(_fetch_csv(Config.CSV_MS))
        texts.append(_fetch_csv(Config.CSV_WN))
    except Exception as e:
        raise RuntimeError(f'無法取得 CSV 資料：{e}')
    combined = '|'.join(texts)
    return _fingerprint(combined)


def load_cache() -> dict:
    """載入上次的快取資料"""
    if os.path.exists(Config.CACHE_FILE):
        try:
            with open(Config.CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(data: dict):
    """儲存快取資料"""
    with open(Config.CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _safe_float(v) -> float:
    """安全轉換數值"""
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0


def build_update_message(old: dict, new: dict) -> str | None:
    """比對新舊資料，產出更新訊息。沒有變更則回傳 None"""
    parts = []
    ocv = old.get('cv', {})
    ncv = new.get('cv', {})

    # 檢查總資產變動
    ota = ocv.get('ta', 0)
    nta = ncv.get('ta', 0)
    if ota != nta:
        diff = nta - ota
        sign = '+' if diff > 0 else ''
        parts.append(f'💰 總資產變動：{sign}{diff:,.0f}（{ota:,.0f} → {nta:,.0f}）')

    # 檢查股價變動
    osp = ocv.get('sp', 0)
    nsp = ncv.get('sp', 0)
    if osp > 0 and nsp > 0 and abs(nsp - osp) / osp > 0.001:
        pct = (nsp - osp) / osp * 100
        direction = '📈 上漲' if pct > 0 else '📉 下跌'
        parts.append(f'{direction} {abs(pct):.2f}%（{osp:.2f} → {nsp:.2f}）')

    if not parts:
        return None

    now_str = datetime.now(TZ).strftime('%Y/%m/%d %H:%M')
    header = f'📢 *台股國運基金 更新通知*\n🕐 {now_str}'
    return header + '\n' + '\n'.join(parts)
