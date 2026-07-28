"""共享的資產快照與淨值績效計算。"""
from datetime import datetime
from math import sqrt

def build_snapshot(cv, history, details, names):
    latest = max(history, key=lambda row: row['dk']) if history else {}
    nav = float(cv.get('nav') or latest.get('n') or 0)
    members = []
    for name, records in zip(names, details):
        invested = sum(r['a'] for r in records)
        units = sum(r['u'] for r in records)
        value = units * nav
        members.append({'name': name, 'invested': invested, 'units': units, 'value': value,
                        'return': (value / invested - 1) if invested else None})
    total_assets = float(cv.get('ta') or 0)
    member_total = sum(m['value'] for m in members)
    invested = latest.get('i', sum(m['invested'] for m in members))
    checks = {
        'cashPlusStock': abs(float(cv.get('ca') or 0) + float(cv.get('sv') or 0) - total_assets) <= 1,
        'membersEqualTotal': abs(member_total - total_assets) <= 1,
        'investedEqualMembers': abs(sum(m['invested'] for m in members) - invested) <= 1,
        'unitsEqualTotal': abs(sum(m['units'] for m in members) - float(cv.get('units') or 0)) <= .01,
    }
    return {'asOf': latest.get('d'), 'totalInvested': invested, 'cash': float(cv.get('ca') or 0),
            'stockExposure': float(cv.get('sv') or 0), 'totalAssets': total_assets, 'latestNav': nav,
            'totalUnits': float(cv.get('units') or sum(m['units'] for m in members)),
            'members': members, 'checks': checks,
            'sources': {'core': cv.get('sourceUpdatedAt'), 'history': latest.get('d'), 'members': cv.get('sourceUpdatedAt')}}

def nav_metrics(history, risk_free=.015):
    rows = sorted((r for r in history if r.get('n', 0) > 0), key=lambda r: r['dk'])
    if len(rows) < 3: return None
    returns = [rows[i]['n'] / rows[i - 1]['n'] - 1 for i in range(1, len(rows))]
    mean = sum(returns) / len(returns)
    vol = sqrt(sum((r - mean) ** 2 for r in returns) / len(returns)) * sqrt(52)
    peak, mdd = rows[0]['n'], 0
    for row in rows:
        peak = max(peak, row['n']); mdd = max(mdd, (peak - row['n']) / peak)
    first = datetime.strptime(rows[0]['d'], '%Y/%m/%d'); last = datetime.strptime(rows[-1]['d'], '%Y/%m/%d')
    years = (last - first).total_seconds() / (365.2425 * 24 * 3600)
    annual = (rows[-1]['n'] / rows[0]['n']) ** (1 / years) - 1 if years > 0 else 0
    return {'mdd': -mdd, 'volatility': vol, 'annualReturn': annual, 'sharpe': (annual-risk_free)/vol if vol else 0,
            'riskFree': risk_free, 'years': years, 'count': len(rows), 'warning': years < 1}
