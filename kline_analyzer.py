"""
K线自动分析脚本
功能：获取K线数据 → 计算技术指标 → 趋势分析 → 给出操作建议
用法：python kline_analyzer.py [symbol] [scale] [datalen]
示例：python kline_analyzer.py sh600519 60 60
"""

import json
import sys
import urllib.request
from datetime import datetime


# ─────────────────────────────────────────────
# 1. 数据获取
# ─────────────────────────────────────────────

def fetch_kline(symbol='sh600519', scale=60, datalen=60):
    """从本地代理获取K线数据"""
    url = f'http://localhost:9600/sina/kline?symbol={symbol}&scale={scale}&datalen={datalen}'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn/',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        rows = []
        for d in reversed(data):
            rows.append({
                'date': d['day'],
                'open': float(d['open']),
                'close': float(d['close']),
                'high': float(d['high']),
                'low': float(d['low']),
                'volume': float(d['volume']),
            })
        return rows
    except Exception as e:
        print(f'数据获取失败: {e}')
        sys.exit(1)


# ─────────────────────────────────────────────
# 2. 基础指标计算
# ─────────────────────────────────────────────

def calc_ma(closes, period):
    """移动平均线"""
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(round(sum(closes[i - period + 1:i + 1]) / period, 3))
    return result


def calc_ema(closes, period):
    """指数移动平均线"""
    k = 2 / (period + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(round(closes[i] * k + ema[-1] * (1 - k), 3))
    return ema


def calc_macd(closes, fast=12, slow=26, signal=9):
    """MACD: DIF / DEA / MACD柱"""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [round(ema_fast[i] - ema_slow[i], 3) for i in range(len(closes))]
    dea = calc_ema(dif, signal)
    hist = [round((dif[i] - dea[i]) * 2, 3) if dea[i] is not None else 0 for i in range(len(closes))]
    return dif, dea, hist


def calc_rsi(closes, period=14):
    """RSI 相对强弱指数"""
    rsi = [None] * (period - 1)
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    for i in range(len(gains)):
        if i < period - 1:
            rsi.append(None)
        else:
            avg_gain = sum(gains[i - period + 1:i + 1]) / period
            avg_loss = sum(losses[i - period + 1:i + 1]) / period
            if avg_loss == 0:
                rsi.append(100)
            else:
                rsi.append(round(100 - 100 / (1 + avg_gain / avg_loss), 2))
    return rsi


def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """KDJ 随机指标"""
    k = [50.0]
    d = [50.0]
    j = [50.0]
    for i in range(1, len(closes)):
        if i < n - 1:
            k.append(None)
            d.append(None)
            j.append(None)
            continue
        low_n = min(lows[i - n + 1:i + 1])
        high_n = max(highs[i - n + 1:i + 1])
        rsv = (closes[i] - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
        k_val = (m1 - 1) / m1 * (k[-1] or 50) + 1 / m1 * rsv
        d_val = (m2 - 1) / m2 * (d[-1] or 50) + 1 / m2 * k_val
        j_val = 3 * k_val - 2 * d_val
        k.append(round(k_val, 2))
        d.append(round(d_val, 2))
        j.append(round(j_val, 2))
    return k, d, j


def calc_bollinger(closes, period=20, mult=2):
    """布林带：中轨 MA20，上轨 +2σ，下轨 -2σ"""
    mid = calc_ma(closes, period)
    upper, lower = [], []
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(None)
            lower.append(None)
        else:
            segment = closes[i - period + 1:i + 1]
            std = (sum((x - mid[i]) ** 2 for x in segment) / period) ** 0.5
            upper.append(round(mid[i] + mult * std, 3))
            lower.append(round(mid[i] - mult * std, 3))
    return upper, mid, lower


def calc_atr(highs, lows, closes, period=14):
    """ATR 平均真实波幅"""
    tr = []
    for i in range(len(highs)):
        if i == 0:
            tr.append(highs[0] - lows[0])
        else:
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            tr.append(max(tr1, tr2, tr3))
    result = [None] * (period - 1)
    for i in range(period - 1, len(tr)):
        if i == period - 1:
            result.append(round(sum(tr[:period]) / period, 3))
        else:
            result.append(round((result[-1] * (period - 1) + tr[i]) / period, 3))
    return result


# ─────────────────────────────────────────────
# 3. 趋势与信号判断
# ─────────────────────────────────────────────

def detect_trend(closes, ma5, ma10, ma20):
    """均线系统判断趋势"""
    if None in (ma5[-1], ma10[-1], ma20[-1]):
        return '数据不足'
    m5, m10, m20 = ma5[-1], ma10[-1], ma20[-1]
    c = closes[-1]

    if m5 > m10 > m20:
        return '上升趋势 ↑↑'
    elif m5 < m10 < m20:
        return '下降趋势 ↓↓'
    elif m5 > m10 and m10 < m20:
        return '震荡偏强 ↗'
    elif m5 < m10 and m10 > m20:
        return '震荡偏弱 ↘'
    else:
        return '震荡横盘 →'


def detect_pattern(closes, highs, lows):
    """简单形态识别"""
    if len(closes) < 5:
        return '数据不足'
    c = closes
    # 最近5根
    last5_open = [c[i]['open'] for i in range(-5, 0)]
    last5_close = [c[i]['close'] for i in range(-5, 0)]
    last5_high = [c[i]['high'] for i in range(-5, 0)]
    last5_low = [c[i]['low'] for i in range(-5, 0)]

    patterns = []

    # 阳线数量
    red = sum(1 for i in range(-5, 0) if closes[i]['close'] >= closes[i]['open'])
    if red >= 4:
        patterns.append('连续阳线强势')

    # 上下影线分析
    last = closes[-1]
    body = abs(last['close'] - last['open'])
    upper_shadow = last['high'] - max(last['open'], last['close'])
    lower_shadow = min(last['open'], last['close']) - last['low']

    if upper_shadow > body * 2 and lower_shadow < body * 0.5:
        patterns.append('长上影线 ★压力')
    if lower_shadow > body * 2 and upper_shadow < body * 0.5:
        patterns.append('长下影线 ★支撑')
    if upper_shadow < body * 0.3 and lower_shadow < body * 0.3 and body > 0:
        patterns.append('实体阳线 强势')

    # 成交量趋势
    vols = [c[i]['volume'] for i in range(-5, 0)]
    if vols[-1] > vols[-2] * 1.5:
        patterns.append('放量异动 ⚠')

    # 创新高/新低
    if last['close'] >= max(h['close'] for h in c[-20:-1]):
        patterns.append('20日新高 强势信号 🔥')
    if last['close'] <= min(h['close'] for h in c[-20:-1]):
        patterns.append('20日新低 弱势信号 💧')

    return ' / '.join(patterns) if patterns else '无明显形态'


def macd_signal(dif, dea, hist):
    """MACD 信号"""
    if None in (dif[-1], dea[-1], hist[-1]):
        return '数据不足'
    d0, d1, h0 = dif[-1], dif[-2] if dif[-2] is not None else 0, hist[-1]
    # 金叉/死叉
    cross = ''
    if dif[-2] is not None and dea[-2] is not None:
        if dif[-2] < dea[-2] and dif[-1] > dea[-1]:
            cross = 'MACD金叉 ★买入信号'
        elif dif[-2] > dea[-2] and dif[-1] < dea[-1]:
            cross = 'MACD死叉 ★卖出信号'
    # 柱状图
    bar = '红柱扩张' if h0 > 0 and (hist[-2] if hist[-2] is not None else 0) < h0 else ('绿柱收缩' if h0 < 0 and abs(h0) < abs(hist[-2] if hist[-2] is not None else 0) else '')
    return (cross + ' | ' + bar) if cross else bar


def rsi_signal(rsi_vals):
    """RSI 信号"""
    if None in (rsi_vals[-1], rsi_vals[-5]):
        return '数据不足'
    r = rsi_vals[-1]
    if r > 80:
        return f'RSI={r:.1f} 超买区域 ⚠'
    elif r < 20:
        return f'RSI={r:.1f} 超卖区域 ★'
    elif r > 65:
        return f'RSI={r:.1f} 强势区域'
    elif r < 35:
        return f'RSI={r:.1f} 弱势区域'
    else:
        return f'RSI={r:.1f} 正常区域'


def kdj_signal(k, d, j):
    """KDJ 信号"""
    if None in (k[-1], d[-1], j[-1]):
        return '数据不足'
    k0, d0, j0 = k[-1], d[-1], j[-1]
    k1 = k[-2] if k[-2] is not None else 50
    d1 = d[-2] if d[-2] is not None else 50
    sig = f'K={k0:.1f} D={d0:.1f} J={j0:.1f}'
    # 金叉死叉
    if k1 < d1 and k0 > d0:
        sig += ' | KDJ金叉 ★'
    elif k1 > d1 and k0 < d0:
        sig += ' | KDJ死叉 ★'
    if j0 > 90:
        sig += ' | J值超买 ⚠'
    elif j0 < 10:
        sig += ' | J值超卖 ★'
    return sig


def boll_signal(upper, mid, lower, close):
    """布林带信号"""
    if None in (upper[-1], mid[-1], lower[-1]):
        return '数据不足'
    u, m, l = upper[-1], mid[-1], lower[-1]
    c = close[-1]
    bandwidth = (u - l) / m * 100
    pos = (c - l) / (u - l) * 100 if u != l else 50
    sig = f'上轨={u} 中轨={m} 下轨={l}'
    if c > u:
        sig += ' | 价格突破上轨 ⚠短线超买'
    elif c < l:
        sig += ' | 价格跌破下轨 ★短线超卖'
    elif pos > 80:
        sig += f' | 处于带上部({pos:.0f}%) 偏强'
    elif pos < 20:
        sig += f' | 处于带下部({pos:.0f}%) 偏弱'
    else:
        sig += f' | 处于带中部({pos:.0f}%) 正常'
    sig += f' | 带宽={bandwidth:.1f}%'
    return sig


# ─────────────────────────────────────────────
# 4. 综合评分与操作建议
# ─────────────────────────────────────────────

def comprehensive_score(data, ma5, ma10, ma20, dif, dea, hist, rsi_vals, k, d, j, upper, lower, atr_vals):
    """多维度综合评分（满分100）"""
    score = 50  # 基础分

    c = data[-1]['close']
    o = data[-1]['open']
    c_prev = data[-2]['close'] if len(data) > 1 else c

    # 1. 价格位置 (15分)
    if None not in (ma5[-1], ma20[-1]):
        if c > ma5[-1] > ma20[-1]:
            score += 10
        elif c < ma5[-1] < ma20[-1]:
            score -= 10
        elif c > ma5[-1] or c > ma20[-1]:
            score += 3

    # 2. 均线多头/空头排列 (15分)
    if None not in (ma5[-1], ma10[-1], ma20[-1]):
        if ma5[-1] > ma10[-1] > ma20[-1]:
            score += 12
        elif ma5[-1] < ma10[-1] < ma20[-1]:
            score -= 12

    # 3. MACD (15分)
    if None not in (dif[-1], dea[-1], hist[-1]):
        if hist[-1] > 0 and (hist[-2] if hist[-2] is not None else 0) < hist[-1]:
            score += 10
        elif hist[-1] < 0 and (hist[-2] if hist[-2] is not None else 0) > hist[-1]:
            score -= 10
        if dif[-1] > dea[-1]:
            score += 5
        else:
            score -= 5

    # 4. RSI (10分)
    if rsi_vals[-1] is not None:
        r = rsi_vals[-1]
        if 45 <= r <= 65:
            score += 3
        elif r > 80 or r < 20:
            score -= 5
        elif r > 65:
            score -= 2
        elif r < 35:
            score += 2

    # 5. KDJ (10分)
    if None not in (k[-1], d[-1]):
        if k[-1] > d[-1] and (k[-2] if k[-2] is not None else 50) <= (d[-2] if d[-2] is not None else 50):
            score += 8
        elif k[-1] < d[-1] and (k[-2] if k[-2] is not None else 50) >= (d[-2] if d[-2] is not None else 50):
            score -= 8
        if 20 <= k[-1] <= 80:
            score += 2

    # 6. 成交量 (10分)
    vols = [d['volume'] for d in data[-10:]]
    avg_vol = sum(vols) / len(vols)
    if vols[-1] > avg_vol * 1.5:
        if c > c_prev:
            score += 8
        else:
            score -= 5
    elif vols[-1] < avg_vol * 0.5:
        score -= 2

    # 7. 涨跌幅度 (10分)
    change = (c - c_prev) / c_prev * 100 if c_prev else 0
    if change > 2:
        score += 5
    elif change < -2:
        score -= 5

    # 8. 布林带 (10分)
    if None not in (upper[-1], lower[-1]):
        if c > upper[-1]:
            score -= 3
        elif c < lower[-1]:
            score += 5

    # 9. ATR波动率 (5分)
    if atr_vals[-1] is not None and atr_vals[-5] is not None:
        if atr_vals[-1] > atr_vals[-5] * 1.3:
            score += 3  # 波动加大

    return max(0, min(100, score))


def action_recommendation(score, trend, pattern, macd_sig, rsi_sig, kdj_sig):
    """给出操作建议"""
    strong_buy = '★ 强烈买入'
    buy = '↑ 建议买入'
    hold = '→ 继续观望'
    sell = '↓ 建议减仓'
    strong_sell = '★★ 建议清仓'

    buy_signals = ['金叉', '超卖', '新低', '超卖区域', '实体阳线', '连续阳线']
    sell_signals = ['死叉', '超买', '新高', '超买区域', '长上影线']
    strong_buy_signals = ['金叉', '连续阳线', '放量异动', 'KDJ金叉']
    strong_sell_signals = ['死叉', 'KDJ死叉', '20日新高']

    sig_text = ' '.join([macd_sig, rsi_sig, kdj_sig, pattern])
    strong_buy_count = sum(1 for s in strong_buy_signals if s in sig_text)
    strong_sell_count = sum(1 for s in strong_sell_signals if s in sig_text)

    if score >= 75 or strong_buy_count >= 2:
        action = strong_buy
    elif score >= 60 or '金叉' in sig_text:
        action = buy
    elif score <= 25 or strong_sell_count >= 2:
        action = strong_sell
    elif score <= 40:
        action = sell
    else:
        action = hold

    return action


# ─────────────────────────────────────────────
# 5. 支撑位 / 压力位
# ─────────────────────────────────────────────

def support_resistance(data, period=20):
    """计算最近N日的支撑压力位"""
    highs = [d['high'] for d in data[-period:]]
    lows = [d['low'] for d in data[-period:]]
    closes = [d['close'] for d in data[-period:]]

    # 压力位：近期高点
    recent_high = max(highs)
    second_high = sorted(highs)[-2]

    # 支撑位：近期低点
    recent_low = min(lows)
    second_low = sorted(lows)[1]

    # 布林带计算
    ma20 = calc_ma(closes, 20)
    boll_mid = ma20[-1] if ma20[-1] else sum(closes) / len(closes)

    # 心理关口：取整
    c = closes[-1]
    p1 = round(c / 10) * 10
    p2 = p1 + 10 if c >= p1 + 5 else p1 - 10

    return {
        'r1': round(recent_high, 2),
        'r2': round(second_high, 2),
        's1': round(recent_low, 2),
        's2': round(second_low, 2),
        'boll_mid': round(boll_mid, 2),
        'psych': p1,
    }


# ─────────────────────────────────────────────
# 6. 主报告生成
# ─────────────────────────────────────────────

def print_report(symbol, scale_name, data, ma5, ma10, ma20, ma60,
                  dif, dea, hist, rsi_vals, k, d, j,
                  upper, boll_mid, lower, atr_vals):
    c = data[-1]
    c_prev = data[-2] if len(data) > 1 else c
    change = (c['close'] - c_prev['close']) / c_prev['close'] * 100

    trend = detect_trend([d['close'] for d in data], ma5, ma10, ma20)
    pattern = detect_pattern(data, [d['high'] for d in data], [d['low'] for d in data])
    macd_sig = macd_signal(dif, dea, hist)
    rsi_sig = rsi_signal(rsi_vals)
    kdj_sig = kdj_signal(k, d, j)
    boll_sig = boll_signal(upper, boll_mid, lower, [d['close'] for d in data])

    score = comprehensive_score(data, ma5, ma10, ma20, dif, dea, hist, rsi_vals, k, d, j, upper, lower, atr_vals)
    action = action_recommendation(score, trend, pattern, macd_sig, rsi_sig, kdj_sig)

    sr = support_resistance(data)

    bar_len = int(score / 5)
    bar = '█' * bar_len + '░' * (20 - bar_len)
    score_color = '🟢' if score >= 60 else ('🔴' if score <= 40 else '🟡')

    print()
    print('═' * 62)
    print(f'  📈 K线自动分析报告  |  {symbol.upper()}  |  {scale_name}')
    print(f'  生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('═' * 62)
    print()
    print(f'  ┌─ 📌 最新数据 ({c["date"]})')
    print(f'  │  开盘: {c["open"]}  收盘: {c["close"]}  最高: {c["high"]}  最低: {c["low"]}')
    print(f'  │  涨跌: {change:+.2f}%  成交量: {c["volume"]:,.0f}')
    print(f'  │')
    print(f'  │  MA5:  {ma5[-1]}   MA10: {ma10[-1]}   MA20: {ma20[-1]}')
    if ma60[-1]:
        print(f'  │  MA60: {ma60[-1]}')
    print(f'  │  ATR:  {atr_vals[-1]}')
    print(f'  └')

    print()
    print(f'  ┌─ 🎯 综合评分')
    print(f'  │  {score_color} [{bar}] {score}/100')
    print(f'  └')

    print()
    print(f'  ┌─ 📊 技术指标')
    print(f'  │  趋势:       {trend}')
    print(f'  │  MACD:       {macd_sig}')
    print(f'  │  RSI:        {rsi_sig}')
    print(f'  │  KDJ:        {kdj_sig}')
    print(f'  │  布林带:     {boll_sig}')
    print(f'  │  形态:       {pattern}')
    print(f'  └')

    print()
    print(f'  ┌─ 📍 支撑位 / 压力位')
    print(f'  │  压力1: {sr["r1"]}   压力2: {sr["r2"]}')
    print(f'  │  布林中: {sr["boll_mid"]}  心理关: {sr["psych"]}')
    print(f'  │  支撑1: {sr["s1"]}   支撑2: {sr["s2"]}')
    print(f'  └')

    print()
    action_emoji = {'★ 强烈买入': '🟢', '↑ 建议买入': '🔵', '→ 继续观望': '⚪',
                    '↓ 建议减仓': '🟠', '★★ 建议清仓': '🔴'}
    print(f'  ╔══════════════════════════════════════╗')
    print(f'  ║  操作建议: {action_emoji.get(action, "⚪")} {action}         ║')
    print(f'  ╚══════════════════════════════════════╝')

    # 近10日行情简表
    print()
    print(f'  ┌─ 📋 近10日行情（最新在上）')
    print(f'  │  {"日期":<18} {"开":>8} {"收":>8} {"高":>8} {"低":>8} {"量":>12}')
    print(f'  │  {"-"*18} {"-"*8} {"-"*8} {"-"*8} {"-"*8} {"-"*12}')
    for d in reversed(data[-10:]):
        cls = '🔴' if d['close'] < d['open'] else '🟢'
        vol = f"{d['volume']:,.0f}"
        print(f'  │  {d["date"]:<18} {d["open"]:>8.2f} {d["close"]:>8.2f} {d["high"]:>8.2f} {d["low"]:>8.2f} {vol:>12}')
    print(f'  └')

    print()
    print('═' * 62)

    # 保存报告到文件
    report_file = f'/Users/jjjj/Documents/股票/kline_report_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f'K线分析报告 - {symbol.upper()} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write('=' * 50 + '\n')
        f.write(f'评分: {score}/100 | 趋势: {trend}\n')
        f.write(f'MACD: {macd_sig}\n')
        f.write(f'RSI: {rsi_sig}\n')
        f.write(f'KDJ: {kdj_sig}\n')
        f.write(f'布林带: {boll_sig}\n')
        f.write(f'形态: {pattern}\n')
        f.write(f'压力: {sr["r1"]} / {sr["r2"]}  支撑: {sr["s1"]} / {sr["s2"]}\n')
        f.write(f'操作建议: {action}\n')
        f.write('=' * 50 + '\n')
        f.write(f'{"日期":<18} {"开":>8} {"收":>8} {"高":>8} {"低":>8} {"量":>12}\n')
        for d in data:
            f.write(f'{d["date"]:<18} {d["open"]:>8.2f} {d["close"]:>8.2f} {d["high"]:>8.2f} {d["low"]:>8.2f} {d["volume"]:>12,.0f}\n')
    print(f'  📄 报告已保存: {report_file}')


# ─────────────────────────────────────────────
# 7. 主程序入口
# ─────────────────────────────────────────────

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'sh600519'
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    datalen = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    scale_names = {5: '5分钟', 15: '15分钟', 30: '30分钟',
                   60: '60分钟', 240: '日K', 1440: '周K'}
    scale_name = scale_names.get(scale, f'{scale}分钟')

    print(f'正在获取 {symbol} 的 {scale_name} K线数据...')

    data = fetch_kline(symbol, scale, datalen)
    if len(data) < 5:
        print(f'数据不足，仅获取 {len(data)} 条')
        return

    print(f'获取成功，共 {len(data)} 条数据，开始分析...')

    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]

    ma5 = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    ma60 = calc_ma(closes, 60) if len(closes) >= 60 else [None] * len(closes)

    dif, dea, hist = calc_macd(closes)
    rsi_vals = calc_rsi(closes)
    k, d, j = calc_kdj(highs, lows, closes)
    upper, boll_mid_list, lower = calc_bollinger(closes)
    atr_vals = calc_atr(highs, lows, closes)

    print_report(symbol, scale_name, data, ma5, ma10, ma20, ma60,
                 dif, dea, hist, rsi_vals, k, d, j,
                 upper, boll_mid_list, lower, atr_vals)


if __name__ == '__main__':
    main()
