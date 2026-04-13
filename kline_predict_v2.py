"""
股票明日涨跌预测系统 v5（个股+大盘联动版）
核心思路：
  - 同时获取「个股」和「上证指数」的历史K线
  - 构建大盘技术指标（RSI/KDJ/MACD/均线/波动率）
  - 构建跨市场特征（相对强弱、Alpha、Beta、市场领先滞后、资金轮动）
  - 用「个股特征 + 大盘特征 + 联动特征」联合预测次日涨跌

回测策略：
  - Walk-Forward 时序严格回测
  - 对比「仅个股」vs「个股+大盘」两种配置的准确率
"""

import sys
import os
import json
import math
import warnings
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.pip_libs'))
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# 1. 数据获取
# ─────────────────────────────────────────────

def fetch_kline(symbol='sh600519', scale=240, datalen=900):
    url = f'http://localhost:9600/sina/kline?symbol={symbol}&scale={scale}&datalen={datalen}'
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn/',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        rows = []
        for d in reversed(data):
            rows.append({
                'date':   d['day'],
                'open':   float(d['open']),
                'close':  float(d['close']),
                'high':   float(d['high']),
                'low':    float(d['low']),
                'volume': float(d['volume']),
            })
        return rows
    except Exception as e:
        print(f'  数据获取失败: {e}')
        return []


# ─────────────────────────────────────────────
# 2. 技术指标计算工具
# ─────────────────────────────────────────────

def _ema(series, period):
    k = 2 / (period + 1)
    result = [series.iloc[0]]
    for i in range(1, len(series)):
        result.append(series.iloc[i] * k + result[-1] * (1 - k))
    return pd.Series(result, index=series.index)


def _rsi(series, period):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + gain / (loss + 1e-10))


def _atr(df, period):
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low']  - df['close'].shift(1)).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _kdj(df):
    n = len(df)
    k_list = [None] * n
    d_list = [None] * n
    for i in range(9, n):
        ln = df['low'].iloc[i-9:i+1].min()
        hn = df['high'].iloc[i-9:i+1].max()
        rsv = (df['close'].iloc[i] - ln) / (hn - ln) * 100 if hn != ln else 50
        k_prev = k_list[i-1] if k_list[i-1] is not None else 50
        d_prev = d_list[i-1] if d_list[i-1] is not None else 50
        k_list[i] = 2/3 * k_prev + 1/3 * rsv
        d_list[i] = 2/3 * d_prev + 1/3 * k_list[i]
    return pd.Series(k_list, index=df.index), pd.Series(d_list, index=df.index)


def _macd(df, fast=12, slow=26, signal=9):
    e_fast = _ema(df['close'], fast)
    e_slow = _ema(df['close'], slow)
    dif    = e_fast - e_slow
    dea    = _ema(dif, signal)
    hist   = (dif - dea) * 2
    return dif, dea, hist


def _boll(df, period=20):
    mid  = df['close'].rolling(period).mean()
    std  = df['close'].rolling(period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    ratio = (df['close'] - lower) / (upper - lower + 1e-10)
    width = (upper - lower) / mid
    return ratio, width


# ─────────────────────────────────────────────
# 3. 单品种特征构建
# ─────────────────────────────────────────────

def build_symbol_features(df, prefix=''):
    """对一个品种构建完整技术指标，prefix用于区分个股和指数"""
    df = df.copy().reset_index(drop=True)
    n  = len(df)

    out = pd.DataFrame(index=df.index)

    # 基础收益率
    for d in [1, 2, 3, 5, 10]:
        out[f'{prefix}ret{d}d'] = df['close'].pct_change(d)

    # 移动平均
    for w in [5, 10, 20, 60]:
        ma = df['close'].rolling(w).mean()
        out[f'{prefix}ma{w}rat'] = df['close'] / ma - 1
        out[f'{prefix}ma{w}dir'] = (ma > ma.shift(1)).astype(int)

    # 大周期均线方向
    out[f'{prefix}ma_bull']  = ((out[f'{prefix}ma5dir'] == 1) & (out[f'{prefix}ma10dir'] == 1)).astype(int)
    out[f'{prefix}ma_bear']  = ((out[f'{prefix}ma5dir'] == 0) & (out[f'{prefix}ma10dir'] == 0)).astype(int)
    out[f'{prefix}ma5_20']   = (out[f'{prefix}ma5rat'] > out[f'{prefix}ma20rat']).astype(int)

    # 波动率
    for w in [5, 10, 20]:
        out[f'{prefix}vol{w}d'] = df['close'].pct_change().rolling(w).std()

    # ATR
    out[f'{prefix}atr14'] = _atr(df, 14)
    out[f'{prefix}atr_r'] = out[f'{prefix}atr14'] / (df['close'] + 1e-10)

    # RSI
    for p in [6, 14]:
        out[f'{prefix}rsi{p}'] = _rsi(df['close'], p)

    # KDJ
    k, d = _kdj(df)
    out[f'{prefix}kdj_k']   = k
    out[f'{prefix}kdj_d']   = d
    out[f'{prefix}kdj_j']   = 3*k - 2*d
    out[f'{prefix}kdj_diff'] = k - d

    # MACD
    dif, dea, hist = _macd(df)
    out[f'{prefix}macd_dif']  = dif
    out[f'{prefix}macd_dea']  = dea
    out[f'{prefix}macd_hist'] = hist
    out[f'{prefix}macd_cross'] = ((dif > dea) & (dif.shift(1) <= dea.shift(1))).astype(int)

    # 布林带
    ratio, width = _boll(df)
    out[f'{prefix}boll_r']   = ratio
    out[f'{prefix}boll_w']   = width

    # Williams%R
    rh = df['high'].rolling(14).max()
    rl = df['low'].rolling(14).min()
    out[f'{prefix}wr'] = -100 * (rh - df['close']) / (rh - rl + 1e-10)

    # OBV
    obv = [0.0] * n
    for i in range(1, n):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv[i] = obv[i-1] + df['volume'].iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv[i] = obv[i-1] - df['volume'].iloc[i]
        else:
            obv[i] = obv[i-1]
    out[f'{prefix}obv_r'] = pd.Series(obv, index=df.index) / (pd.Series(obv, index=df.index).rolling(5).mean() + 1e-10)

    # 成交量
    vol_ma5 = df['volume'].rolling(5).mean()
    out[f'{prefix}vol_r']   = df['volume'] / (vol_ma5 + 1)
    out[f'{prefix}vol_up']  = (df['close'] > df['open']).astype(int)
    out[f'{prefix}vol_up3'] = out[f'{prefix}vol_up'].rolling(3).sum()

    # 价格位置
    hi20 = df['high'].rolling(20).max()
    lo20 = df['low'].rolling(20).min()
    out[f'{prefix}price_pos'] = (df['close'] - lo20) / (hi20 - lo20 + 1e-10)
    out[f'{prefix}price_pos5'] = (df['close'] - df['close'].rolling(5).min()) / \
                                   (df['close'].rolling(5).max() - df['close'].rolling(5).min() + 1e-10)

    # 日内结构
    body     = df['close'] - df['open']
    amplitude = (df['high'] - df['low']) / df['close']
    out[f'{prefix}body_r']    = body / (df['high'] - df['low'] + 1e-10)
    out[f'{prefix}u_shadow']  = (df['high'] - df[['open','close']].max(axis=1)) / (df['high'] - df['low'] + 1e-10)
    out[f'{prefix}l_shadow']  = (df[['open','close']].min(axis=1) - df['low']) / (df['high'] - df['low'] + 1e-10)
    out[f'{prefix}amplitude'] = amplitude

    # 动量
    out[f'{prefix}roc5']  = df['close'] / df['close'].shift(5) - 1
    out[f'{prefix}roc10'] = df['close'] / df['close'].shift(10) - 1
    out[f'{prefix}momentum'] = df['close'] - df['close'].shift(5)

    # 连续涨跌
    streak_up = [0] * n
    streak_dn = [0] * n
    cu, cd = 0, 0
    for i in range(1, n):
        if df['close'].iloc[i] >= df['close'].iloc[i-1]:
            cu = cu + 1 if cu > 0 else 1; cd = 0
        else:
            cd = cd + 1 if cd > 0 else 1; cu = 0
        streak_up[i] = cu
        streak_dn[i] = cd
    out[f'{prefix}streak_up'] = streak_up
    out[f'{prefix}streak_dn'] = streak_dn

    return out


# ─────────────────────────────────────────────
# 4. 大盘 + 个股联动特征（核心新增）
# ─────────────────────────────────────────────

def build_cross_features(sdf, mdf):
    """
    构建个股(sdf)与大盘(mdf)的联动特征
    这些特征代表「个股相对于大盘的表现」，是预测的关键
    """
    out = pd.DataFrame(index=sdf.index)

    # ── 相对收益率（Alpha = 个股收益 - 大盘收益）──
    for d in [1, 2, 3, 5, 10]:
        s_ret = sdf[f'stk_ret{d}d']
        m_ret = mdf[f'mkt_ret{d}d']
        out[f'alpha{d}d']    = s_ret - m_ret
        out[f'strong_mkt']  = ((s_ret > 0) & (m_ret > 0)).astype(int)
        out[f'strong_stk']  = ((s_ret > 0) & (m_ret <= 0)).astype(int)
        out[f'weak_mkt']    = ((s_ret <= 0) & (m_ret > 0)).astype(int)
        out[f'weak_stk']    = ((s_ret <= 0) & (m_ret <= 0)).astype(int)
        out[f'both_up']     = ((s_ret > 0) & (m_ret > 0)).astype(int)
        out[f'both_down']   = ((s_ret <= 0) & (m_ret <= 0)).astype(int)
        out[f'divergence']  = ((s_ret * m_ret) < 0).astype(int)

    # ── 相对动量差（个股动量 - 大盘动量）──
    for d in [3, 5, 10]:
        out[f'mom_diff{d}d'] = (sdf[f'stk_ret{d}d'] - mdf[f'mkt_ret{d}d'])

    # ── 相对RSI（个股RSI - 大盘RSI）──
    for p in [6, 14]:
        sk = f'stk_rsi{p}'
        mk = f'mkt_rsi{p}'
        if sk in sdf.columns and mk in mdf.columns:
            out[f'rsi_diff{p}'] = sdf[sk] - mdf[mk]

    # ── 相对MACD（个股MACD - 大盘MACD）──
    if 'stk_macd_hist' in sdf.columns and 'mkt_macd_hist' in mdf.columns:
        out['macd_diff']     = sdf['stk_macd_hist'] - mdf['mkt_macd_hist']
        out['macd_diff_chg'] = out['macd_diff'] - out['macd_diff'].shift(1)
        out['macd_both_up']  = ((sdf['stk_macd_hist'] > 0) & (mdf['mkt_macd_hist'] > 0)).astype(int)
        out['macd_div']      = (((sdf['stk_macd_hist'] > 0) & (mdf['mkt_macd_hist'] < 0)) |
                                 ((sdf['stk_macd_hist'] < 0) & (mdf['mkt_macd_hist'] > 0))).astype(int)

    # ── 相对布林带位置 ──
    if 'stk_boll_r' in sdf.columns and 'mkt_boll_r' in mdf.columns:
        out['boll_diff'] = sdf['stk_boll_r'] - mdf['mkt_boll_r']

    # ── 大盘涨跌模式（用于判断市场整体情绪）──
    for d in [1, 3, 5]:
        out[f'mkt_up{d}d']   = (mdf[f'mkt_ret{d}d'] > 0).astype(int)
        out[f'mkt_str{d}d']  = (mdf[f'mkt_ret{d}d'] > 0.02).astype(int)
        out[f'mkt_weak{d}d'] = (mdf[f'mkt_ret{d}d'] < -0.02).astype(int)

    # ── 市场趋势 ──
    if 'mkt_ma_bull' in mdf.columns:
        out['mkt_bull'] = mdf['mkt_ma_bull']
        out['mkt_bear'] = mdf['mkt_ma_bear']
        out['mkt_5_20'] = mdf['mkt_ma5_20']

    # ── 相对市场强度（个股涨幅 / 大盘涨幅）──
    for d in [1, 3, 5]:
        s_ret = sdf[f'stk_ret{d}d']
        m_ret = mdf[f'mkt_ret{d}d'].replace(0, 1e-10)
        out[f'rel_str{d}d'] = s_ret / m_ret.replace(0, np.nan)

    # ── Beta（个股对大盘的敏感度，滚动20天）──
    n = len(sdf)
    betas = []
    for i in range(n):
        if i < 25:
            betas.append(np.nan)
        else:
            srets = sdf['stk_ret1d'].iloc[i-20:i].values
            mrets = mdf['mkt_ret1d'].iloc[i-20:i].values
            mask  = ~(np.isnan(srets) | np.isnan(mrets))
            if mask.sum() >= 10:
                cov = np.cov(srets[mask], mrets[mask])[0, 1]
                var = np.var(mrets[mask])
                betas.append(cov / var if var > 1e-10 else 1.0)
            else:
                betas.append(1.0)
    out['beta20'] = betas

    # ── 市场情绪：连涨/连跌天数 ──
    mkt_up = (mdf['mkt_ret1d'] > 0).astype(int)
    streak_up = [0] * n
    streak_dn = [0] * n
    cu, cd = 0, 0
    for i in range(1, n):
        if mkt_up.iloc[i] == 1:
            cu = cu + 1 if cu > 0 else 1; cd = 0
        else:
            cd = cd + 1 if cd > 0 else 1; cu = 0
        streak_up[i] = cu
        streak_dn[i] = cd
    out['mkt_streak_up'] = streak_up
    out['mkt_streak_dn'] = streak_dn

    # ── 滞后大盘特征（今日大盘状态，对明日个股有预测价值）──
    for d in [1, 2, 3]:
        out[f'mkt_ret_lag{d}'] = mdf[f'mkt_ret{d}d'].shift(1)
        if 'mkt_rsi14' in mdf.columns:
            out[f'mkt_rsi_lag{d}'] = mdf['mkt_rsi14'].shift(d)

    return out


# ─────────────────────────────────────────────
# 5. 合并大盘 + 个股特征
# ─────────────────────────────────────────────

def merge_features(stock_df, index_df):
    """合并个股、大盘、联动特征"""
    # 保留日期用于后续显示
    dates = stock_df['date'].reset_index(drop=True)

    sdf = build_symbol_features(stock_df, prefix='stk_')
    mdf = build_symbol_features(index_df, prefix='mkt_')
    crs = build_cross_features(sdf, mdf)

    # 合并
    merged = pd.concat([sdf, mdf, crs], axis=1)
    merged['date']         = dates.values  # 保留日期
    merged['stk_close']    = stock_df['close'].values  # 个股收盘价
    merged['mkt_close']    = index_df['close'].values  # 大盘收盘价

    # 目标：次日个股涨跌
    merged['next_ret'] = stock_df['close'].shift(-1).values / stock_df['close'].values - 1
    merged['target']   = (merged['next_ret'] > 0).astype(int)

    return merged, sdf, mdf, crs


# ─────────────────────────────────────────────
# 6. 特征列表
# ─────────────────────────────────────────────

def get_feature_cols(sdf, mdf, crs):
    """从特征DataFrame中提取所有列名"""
    cols = []
    for df_feat in [sdf, mdf, crs]:
        for c in df_feat.columns:
            if not c.startswith('next_') and c != 'target':
                cols.append(c)
    return cols


# ─────────────────────────────────────────────
# 7. 模型
# ─────────────────────────────────────────────

def get_models():
    return [
        ('RF1', RandomForestClassifier(
            n_estimators=300, max_depth=4, min_samples_leaf=50,
            min_samples_split=80, class_weight='balanced_subsample',
            random_state=42, n_jobs=-1
        )),
        ('RF2', RandomForestClassifier(
            n_estimators=300, max_depth=3, min_samples_leaf=60,
            min_samples_split=100, class_weight='balanced_subsample',
            random_state=123, n_jobs=-1
        )),
        ('ET1', ExtraTreesClassifier(
            n_estimators=300, max_depth=4, min_samples_leaf=50,
            class_weight='balanced_subsample', random_state=42, n_jobs=-1
        )),
        ('ET2', ExtraTreesClassifier(
            n_estimators=300, max_depth=3, min_samples_leaf=60,
            class_weight='balanced_subsample', random_state=123, n_jobs=-1
        )),
        ('GBM', GradientBoostingClassifier(
            n_estimators=200, max_depth=2, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=50, random_state=42
        )),
        ('LR', LogisticRegression(
            max_iter=2000, class_weight='balanced', C=0.05, random_state=42
        )),
    ]


def train_ensemble(X, y, feature_names=None):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    up_ratio = y.mean()
    threshold = 1.0 - up_ratio
    threshold = max(0.38, min(0.62, threshold))

    trained = {}
    for name, model in get_models():
        m = model.__class__(**model.get_params())
        m.fit(Xs, y)
        trained[name] = m

    weights = {'RF1': 1.0, 'RF2': 1.0, 'ET1': 1.0, 'ET2': 1.0, 'GBM': 2.0, 'LR': 1.0}

    def predict_fn(X_new):
        X_new_s = scaler.transform(X_new)
        probs = np.array([m.predict_proba(X_new_s)[:, 1] for m in trained.values()])
        w = np.array([weights.get(n, 1.0) for n in trained.keys()])
        avg_prob = np.average(probs, axis=0, weights=w)
        preds = (avg_prob > threshold).astype(int)
        return preds, avg_prob

    # 特征重要性
    importance = None
    for name, m in trained.items():
        if hasattr(m, 'feature_importances_'):
            fi = sorted(zip(feature_names, m.feature_importances_), key=lambda x: x[1], reverse=True)
            importance = fi[:15]
            break

    return predict_fn, scaler, trained, threshold, importance


# ─────────────────────────────────────────────
# 8. Walk-Forward 回测
# ─────────────────────────────────────────────

def walkforward(merged, feature_cols, name_tag, train_w=250, test_w=30, step=10):
    """Walk-Forward时序回测"""
    X = merged[feature_cols].values
    y = merged['target'].values
    dates = merged.index
    n = len(merged)

    if n < train_w + test_w:
        return None, '数据不足'

    results  = []
    equity   = 1.0

    i = train_w
    while i + test_w <= n:
        X_train = X[i - train_w:i]
        y_train = y[i - train_w:i]

        if y_train.sum() < 10 or (len(y_train) - y_train.sum()) < 10:
            i += step; continue

        try:
            predict_fn, _, _, _, _ = train_ensemble(X_train, y_train, feature_cols)
        except Exception:
            i += step; continue

        for j in range(i, min(i + test_w, n)):
            Xj   = X[j].reshape(1, -1)
            pred, prob_up = predict_fn(Xj)
            real = int(y[j])
            ret  = merged['next_ret'].iloc[j] if not pd.isna(merged['next_ret'].iloc[j]) else 0

            pos_ret = ret if pred[0] == 1 else 0
            equity *= (1 + pos_ret)

            # 从merged的date列获取真实日期
            date_str = str(merged['date'].iloc[j])[:10]

            results.append({
                'date':    date_str,
                'close':   round(merged['stk_close'].iloc[j], 2),
                'predict': '涨↑' if pred[0] else '跌↓',
                'prob_up': round(prob_up[0] * 100, 1),
                'real':    '涨↑' if real else '跌↓',
                'correct': '✓' if pred[0] == real else '✗',
                'ret':     f'{ret*100:+.2f}%',
                'equity':  round(equity, 4),
                'idx':     j,
            })
        i += step

    if not results:
        return None, '无结果'
    return pd.DataFrame(results), None


def compute_stats(res_df):
    n       = len(res_df)
    correct = (res_df['correct'] == '✓').sum()
    acc     = correct / n * 100 if n else 0

    up_df  = res_df[res_df['predict'] == '涨↑']
    dn_df  = res_df[res_df['predict'] == '跌↓']
    win_up = (up_df['correct'] == '✓').sum() / max(len(up_df), 1) * 100
    win_dn = (dn_df['correct'] == '✓').sum() / max(len(dn_df), 1) * 100

    equity  = res_df['equity'].iloc[-1]
    total_r = (equity - 1) * 100

    daily_rets = []
    for _, r in res_df.iterrows():
        v = float(r['ret'].replace('%','').replace('+','')) / 100
        daily_rets.append(v if r['predict'] == '涨↑' else 0)
    ann_vol = np.std(daily_rets) * math.sqrt(252) * 100
    sharpe  = total_r * 365 / max(len(res_df), 1) / ann_vol if ann_vol > 0.01 else 0

    peak, max_dd = 1.0, 0
    for eq in res_df['equity']:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd: max_dd = dd

    return {
        'total': n, 'correct': int(correct), 'accuracy': round(acc, 2),
        'win_up': round(win_up, 2), 'win_dn': round(win_dn, 2),
        'equity': round(equity, 4), 'total_ret': round(total_r, 2),
        'sharpe': round(sharpe, 3), 'max_dd': round(max_dd, 2),
        'up_preds': len(up_df), 'dn_preds': len(dn_df),
    }


# ─────────────────────────────────────────────
# 9. 今日预测
# ─────────────────────────────────────────────

def predict_today(merged, feature_cols):
    X_all = merged[feature_cols].values
    y_all = merged['target'].values
    predict_fn, _, _, threshold, importance = train_ensemble(X_all, y_all, feature_cols)
    X_last = X_all[-1].reshape(1, -1)
    pred, prob_up = predict_fn(X_last)
    return pred, prob_up, threshold, importance


# ─────────────────────────────────────────────
# 10. 报告打印
# ─────────────────────────────────────────────

def print_banner():
    print()
    print('═' * 70)
    print('  📊 个股+大盘联动预测系统 v5')
    print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('═' * 70)


def print_prediction_result(symbol, merged, pred, prob_up, threshold, importance,
                             stats_cross, stats_stock_only, feature_cols, sdf, mdf, crs):
    last_close = merged.iloc[-1]['next_ret'] * 0  # placeholder
    print()
    last_date   = str(merged['date'].iloc[-1])[:10]
    last_close  = merged['stk_close'].iloc[-1]
    print('═' * 70)
    print(f'  🔮 明日涨跌预测  |  {symbol.upper()}  |  数据日: {last_date}')
    print(f'  今日收盘: {last_close}')
    print('═' * 70)

    emoji = '🟢' if '涨' in pred else '🔴'
    conf  = round(abs(prob_up[0] - 0.5) * 200, 1)
    print(f'\n  🎯 综合预测: {emoji} {pred[0]}  涨:{prob_up[0]*100:.1f}%  跌:{(1-prob_up[0])*100:.1f}%  置信度:{conf}%')

    if importance:
        print(f'\n  ┌─ 📌 关键影响因子 Top-10')
        for fname, imp in importance[:10]:
            bar = '█' * int(imp * 500)
            prefix = ''
            if fname.startswith('stk_'): prefix = '[个股]'
            elif fname.startswith('mkt_'): prefix = '[大盘]'
            elif fname.startswith('alpha') or fname.startswith('mom_diff') or \
                 fname.startswith('rsi_diff') or fname.startswith('mkt_') or \
                 fname.startswith('rel_str') or fname.startswith('divergence') or \
                 fname.startswith('both_') or fname.startswith('strong') or \
                 fname.startswith('weak') or fname.startswith('macd_diff') or \
                 fname.startswith('boll_diff') or fname.startswith('beta'):
                prefix = '[联动]'
            print(f'  │  {prefix}{fname:<28} {bar} {imp:.4f}')
        print(f'  └')

    # 准确率对比
    print(f'\n  ┌─ 📈 回测准确率对比')
    acc_cross   = stats_cross['accuracy']
    acc_stock   = stats_stock_only['accuracy']
    improvement = acc_cross - acc_stock
    e_improve  = '🟢' if improvement > 0 else ('🔴' if improvement < 0 else '⚪')
    acc_cross_c = stats_cross['correct']
    acc_cross_t = stats_cross['total']
    acc_stock_c = stats_stock_only['correct']
    acc_stock_t = stats_stock_only['total']
    print(f'  │  个股+大盘 准确率: {acc_cross:.1f}%  ({acc_cross_c}/{acc_cross_t})')
    print(f'  │  仅个股     准确率: {acc_stock:.1f}%  ({acc_stock_c}/{acc_stock_t})')
    print(f'  │  {e_improve} 大盘特征贡献: {improvement:+.1f}%')
    print(f'  └')

    # 详细对比
    print(f'\n  ┌─ 📊 详细指标对比')
    print(f'  │  {"指标":<12} {"个股+大盘":>12} {"仅个股":>12} {"变化":>8}')
    print(f'  │  {"-"*12} {"-"*12} {"-"*12} {"-"*8}')
    rows = [
        ('准确率',   f'{acc_cross:.1f}%',    f'{acc_stock:.1f}%',    f'{improvement:+.1f}%'),
        ('预测涨胜率', f'{stats_cross["win_up"]:.1f}%', f'{stats_stock_only["win_up"]:.1f}%', f'{stats_cross["win_up"]-stats_stock_only["win_up"]:+.1f}%'),
        ('预测跌胜率', f'{stats_cross["win_dn"]:.1f}%', f'{stats_stock_only["win_dn"]:.1f}%', f'{stats_cross["win_dn"]-stats_stock_only["win_dn"]:+.1f}%'),
        ('模拟收益', f'{stats_cross["total_ret"]:+.1f}%', f'{stats_stock_only["total_ret"]:+.1f}%', f'{stats_cross["total_ret"]-stats_stock_only["total_ret"]:+.1f}%'),
        ('夏普比率', f'{stats_cross["sharpe"]:.3f}',   f'{stats_stock_only["sharpe"]:.3f}',   f'{stats_cross["sharpe"]-stats_stock_only["sharpe"]:+.3f}'),
        ('最大回撤', f'{stats_cross["max_dd"]:.1f}%',   f'{stats_stock_only["max_dd"]:.1f}%',   f'{stats_cross["max_dd"]-stats_stock_only["max_dd"]:+.1f}%'),
    ]
    for row in rows:
        print(f'  │  {row[0]:<12} {row[1]:>12} {row[2]:>12} {row[3]:>8}')
    print(f'  └')

    # 特征类型统计
    n_stock = len([c for c in feature_cols if c.startswith('stk_')])
    n_mkt   = len([c for c in feature_cols if c.startswith('mkt_')])
    n_cross = len([c for c in feature_cols if c not in [f'stk_{x}' for x in ['stk_ret1d']] and
                   not c.startswith('stk_') and not c.startswith('mkt_')])
    print(f'\n  ┌─ 🏗️ 特征构成')
    print(f'  │  个股特征: {n_stock} 个  |  大盘特征: {n_mkt} 个  |  联动特征: {n_cross} 个  |  总计: {len(feature_cols)} 个')
    print(f'  └')
    print()
    print('═' * 70)


# ─────────────────────────────────────────────
# 11. 主程序
# ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    sym  = next((a for a in args if a.startswith('sh') or a.startswith('sz')), 'sh600519')

    print_banner()
    print(f'\n获取 {sym} 个股数据...')
    stock_rows = fetch_kline(sym, 240, 900)
    if not stock_rows:
        print('个股数据获取失败'); return

    print(f'获取上证指数 sh000001 数据...')
    index_rows = fetch_kline('sh000001', 240, 900)
    if not index_rows:
        print('大盘数据获取失败'); return

    # 转DataFrame并对齐日期
    sdf_raw = pd.DataFrame(stock_rows)
    mdf_raw = pd.DataFrame(index_rows)
    sdf_raw['date'] = pd.to_datetime(sdf_raw['date'])
    mdf_raw['date'] = pd.to_datetime(mdf_raw['date'])

    # 保留两者共同的日期
    common_dates = set(sdf_raw['date']) & set(mdf_raw['date'])
    sdf_raw = sdf_raw[sdf_raw['date'].isin(common_dates)].sort_values('date').reset_index(drop=True)
    mdf_raw = mdf_raw[mdf_raw['date'].isin(common_dates)].sort_values('date').reset_index(drop=True)

    print(f'共同交易日: {len(sdf_raw)} 天 ({sdf_raw["date"].iloc[0].date()} ~ {sdf_raw["date"].iloc[-1].date()})')

    # 构建特征
    print('\n构建特征（个股 + 大盘 + 联动）...')
    merged, sdf, mdf_feat, crs = merge_features(sdf_raw, mdf_raw)
    feature_cols = get_feature_cols(sdf, mdf_feat, crs)
    merged = merged.dropna(subset=feature_cols + ['target']).reset_index(drop=True)

    if len(merged) < 300:
        print(f'有效数据不足 ({len(merged)} 天)'); return

    print(f'有效数据: {len(merged)} 天, 特征总数: {len(feature_cols)} 个')
    n_stock = len([c for c in feature_cols if c.startswith('stk_')])
    n_mkt   = len([c for c in feature_cols if c.startswith('mkt_')])
    n_cross = len(feature_cols) - n_stock - n_mkt
    print(f'  - 个股特征: {n_stock} 个')
    print(f'  - 大盘特征: {n_mkt} 个')
    print(f'  - 联动特征: {n_cross} 个')

    # ── Walk-Forward 回测 ──
    print('\n运行 Walk-Forward 回测...')

    # 配置1：个股+大盘+联动特征
    print('  [1/2] 个股+大盘+联动特征...')
    res_cross, _ = walkforward(merged, feature_cols, '个股+大盘',
                               train_w=250, test_w=30, step=10)
    stats_cross = compute_stats(res_cross) if res_cross is not None else {}

    # 配置2：仅个股特征（对比基准）
    stock_only_cols = [c for c in feature_cols if c.startswith('stk_')]
    print('  [2/2] 仅个股特征（基准对照）...')
    res_stock, _ = walkforward(merged, stock_only_cols, '仅个股',
                                train_w=250, test_w=30, step=10)
    stats_stock = compute_stats(res_stock) if res_stock is not None else {}

    # ── 今日预测 ──
    print('\n生成今日预测...')
    pred, prob_up, threshold, importance = predict_today(merged, feature_cols)

    # ── 打印结果 ──
    print_prediction_result(
        sym, merged, pred, prob_up, threshold, importance,
        stats_cross, stats_stock, feature_cols, sdf, mdf_feat, crs
    )

    # ── 保存结果 ──
    if res_cross is not None:
        out_csv = f'/Users/jjjj/Documents/股票/predict_v2_{sym}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        res_cross.to_csv(out_csv, index=False, encoding='utf-8-sig')
        print(f'  📄 明细已保存: {out_csv}')

    # ── 批量回测演示 ──
    if '--batch' in args:
        print('\n\n' + '═' * 70)
        print('  批量回测：个股+大盘 vs 仅个股 对比')
        print('═' * 70)
        batch_stocks = [
            ('贵州茅台', 'sh600519'),
            ('招商银行', 'sh600036'),
            ('中国平安', 'sh601318'),
            ('五粮液',   'sz000858'),
            ('宁德时代', 'sz300750'),
        ]
        print(f'\n  {"股票":<12} {"个股+大盘":>10} {"仅个股":>10} {"提升":>8} {"大盘特征贡献"}')
        print(f'  {"-"*12} {"-"*10} {"-"*10} {"-"*8} {"-"*15}')
        for name, code in batch_stocks:
            sr = fetch_kline(code, 240, 900)
            if not sr:
                print(f'  {name:<12} 数据获取失败'); continue
            ir = fetch_kline('sh000001', 240, 900)
            if not ir:
                print(f'  {name:<12} 指数获取失败'); continue
            sd = pd.DataFrame(sr); sd['date'] = pd.to_datetime(sd['date'])
            id_ = pd.DataFrame(ir); id_['date'] = pd.to_datetime(id_['date'])
            common = set(sd['date']) & set(id_['date'])
            sd = sd[sd['date'].isin(common)].sort_values('date').reset_index(drop=True)
            id_ = id_[id_['date'].isin(common)].sort_values('date').reset_index(drop=True)
            mg, sf, mf, cf = merge_features(sd, id_)
            fc = get_feature_cols(sf, mf, cf)
            mg = mg.dropna(subset=fc + ['target']).reset_index(drop=True)
            if len(mg) < 280:
                print(f'  {name:<12} 数据不足'); continue
            rc, _ = walkforward(mg, fc, '', train_w=250, test_w=30, step=10)
            sc = [c for c in fc if c.startswith('stk_')]
            rs, _ = walkforward(mg, sc, '', train_w=250, test_w=30, step=10)
            st_c = compute_stats(rc) if rc is not None else {}
            st_s = compute_stats(rs) if rs is not None else {}
            acc_c = st_c.get('accuracy', 0)
            acc_s = st_s.get('accuracy', 0)
            imp    = acc_c - acc_s
            e = '🟢' if imp > 0 else ('🔴' if imp < 0 else '⚪')
            print(f'  {name:<12} {acc_c:>9.1f}% {acc_s:>9.1f}% {imp:>+7.1f}%  {e}')


if __name__ == '__main__':
    main()
