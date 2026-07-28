"""
Google Sheets 資料擷取與變更偵測
"""
import json
import hashlib
import math
import csv
import io
import os
import time
import requests
from datetime import datetime, timezone, timedelta

# 台灣時區
TZ = timezone(timedelta(hours=8))
from .config import Config


def _fetch_csv(url: str) -> str:
    """抓取 CSV 原始文字"""
    last_error = None
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30, headers={'Cache-Control': 'no-cache'})
            resp.raise_for_status()
            content_type = resp.headers.get('Content-Type', '').lower()
            if content_type and not any(t in content_type for t in ('csv', 'text/plain', 'text/html')):
                raise ValueError(f'不支援的 Content-Type：{content_type}')
            text = resp.text
            if not text.strip() or '<html' in text[:500].lower():
                raise ValueError('回應不是有效 CSV')
            resp.encoding = 'utf-8'
            return text
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f'CSV 下載失敗：{last_error}')


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
    found = set()
    for r in rows:
        if len(r) < 2:
            continue
        key = r[0].strip()
        val = _safe_float(r[1])
        if key == '合資總資產':
            cv['ta'] = val
            found.add(key)
        elif key == '帳上現金':
            cv['ca'] = val
            found.add(key)
        elif key == '00631L 現價':
            cv['sp'] = val
            cv['sv'] = val * cv['sh']
            found.add(key)
        elif key == '合資總持股數':
            cv['sh'] = val
            cv['sv'] = cv['sp'] * val
            found.add(key)
    required = {'合資總資產', '帳上現金', '00631L 現價', '合資總持股數'}
    if not required.issubset(found):
        raise ValueError('核心 CSV 缺少必要欄位')
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


def fetch_dashboard_data() -> dict:
    """擷取前端儀表板需要的完整資料。"""
    data = fetch_all_data()
    history = []
    rows = _parse_csv(_fetch_csv(Config.CSV_WN))
    for r in rows:
        if len(r) < 4:
            continue
        try:
            date = datetime.strptime(r[0].strip(), '%Y/%m/%d')
            history.append({
                'd': r[0].strip(),
                'dk': date.strftime('%Y%m%d'),
                'a': _safe_float(r[1]),
                'i': _safe_float(r[2]),
                'n': _safe_float(r[3]),
            })
        except ValueError:
            continue
    data['wn'] = history
    data['md'] = [fetch_member_detail(gid) for gid in Config.MEMBER_GIDS.values()]
    data['p0050'] = fetch_0050_prices(history)
    return data


def fetch_0050_prices(history: list) -> dict:
    """由後端抓取 0050.TW 每日開盤價，避免瀏覽器 CORS 限制。"""
    if not history:
        return {}
    try:
        start = datetime.strptime(history[0]['d'], '%Y/%m/%d')
        end = datetime.now(TZ) + timedelta(days=1)
        params = {
            'period1': int(start.replace(tzinfo=TZ).timestamp()),
            'period2': int(end.timestamp()),
            'interval': '1d',
            'includeAdjustedClose': 'true',
        }
        for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
            response = requests.get(
                f'https://{host}/v8/finance/chart/0050.TW',
                params=params,
                timeout=20,
                headers={'User-Agent': 'Mozilla/5.0'},
            )
            response.raise_for_status()
            result = response.json().get('chart', {}).get('result', [{}])[0]
            timestamps = result.get('timestamp', [])
            opens = result.get('indicators', {}).get('quote', [{}])[0].get('open', [])
            prices = {}
            for timestamp, opening in zip(timestamps, opens):
                if opening is None:
                    continue
                date = datetime.fromtimestamp(timestamp, TZ)
                prices[date.strftime('%Y/%m/%d')] = opening
            if prices:
                return prices
    except (requests.RequestException, ValueError, IndexError, KeyError, TypeError) as exc:
        print(f'[0050] 歷史股價下載失敗：{exc}', file=__import__('sys').stderr)
    return {}


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



def fetch_weekly_comparison():
    """從歷史紀錄 CSV 抓上週 vs 本週的資料，回傳 dict 或 None"""
    import csv, io
    try:
        text = _fetch_csv(Config.CSV_WN)
        rows = _parse_csv(text)
        # 清理、排序後取目前紀錄之前最近一筆
        records = []
        for index, r in enumerate(rows):
            if len(r) >= 3:
                try:
                    date = datetime.strptime(r[0].strip(), '%Y/%m/%d')
                    asset = float(r[1])
                    if not math.isfinite(asset):
                        continue
                    records.append((date, index, asset, float(r[3]) if len(r) > 3 else 0))
                except (ValueError, IndexError):
                    continue
        if len(records) >= 2:
            records.sort(key=lambda item: (item[0], item[1]))
            previous, current = records[-2], records[-1]
            return {"ta": previous[2], "sp": previous[3], "date": previous[0].strftime('%Y/%m/%d')}
    except Exception as e:
        print(f"[Weekly] 無法讀取歷史資料：{e}", file=__import__("sys").stderr)
    return None


def fetch_last_history_date():
    """從歷史紀錄 CSV 讀取最後一筆資料的日期"""
    import csv, io
    from datetime import datetime
    try:
        text = _fetch_csv(Config.CSV_WN)
        rows = _parse_csv(text)
        for r in reversed(rows):
            if len(r) >= 2:
                d = r[0].strip()
                try:
                    return datetime.strptime(d, "%Y/%m/%d").replace(tzinfo=TZ)
                except ValueError:
                    continue
    except:
        pass
    return None


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
    # 檢查最後一筆資料日期是否為當週週日
    last_date = fetch_last_history_date()
    if last_date:
        today = __import__("datetime").datetime.now(TZ)
        # 只允許週日或當天
        diff = (today - last_date).days
        if diff > 7:
            print(f"[Monitor] 最新資料日期 {last_date.date()} 與今天 {today.date()} 差距 {diff} 天，跳過推播", file=__import__("sys").stderr)
            return None
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
