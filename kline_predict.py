"""
股票明日涨跌预测系统 v4（优化版）
核心：用今日及之前的数据预测明日涨跌

策略重点：
1. 增强特征工程（动量、滞后序列、结构特征）
2. 类别不平衡处理（阈值优化 + SMOTE）
3. 集成学习（RF + GBM + LR 多模型加权）
4. Walk-Forward 时序严格回测
5. 阈值调优（找最优决策边界）
"""

import sys
import os
import json
import math
import warnings
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.pip_libs'))
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import cross_val_score

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# 1. 数据获取
# ─────────────────────────────────────────────

def fetch_kline(symbol='sh600519', scale=240, datalen=800):
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
        print(f'数据获取失败: {e}')
        return []


# ─────────────────────────────────────────────
# 2. 特征工程（无未来函数）
# ─────────────────────────────────────────────

def build_features(df):
    """所有特征仅用当日及之前数据，目标 = 次日涨跌（0/1）"""
    df = df.copy().reset_index(drop=True)
    n_rows = len(df)
    _n = len(df)  # keep as local var for compatibility

    # ── 基础收益率 ──
    for d in [1, 2, 3, 5, 8, 10]:
        df[f'ret_{d}d'] = df['close'].pct_change(d)

    # ── 移动平均 ──
    for w in [3, 5, 10, 20, 60]:
        df[f'ma{w}']        = df['close'].rolling(w).mean()
        df[f'ma{w}_ratio']  = df['close'] / df[f'ma{w}'] - 1

    # ── 均线方向 ──
    for w in [5, 10, 20]:
        df[f'ma{w}_up']    = (df[f'ma{w}'] > df[f'ma{w}'].shift(1)).astype(int)
        df[f'ma{w}_slope'] = (df[f'ma{w}'] - df[f'ma{w}'].shift(3)) / df[f'ma{w}'].shift(3)

    # ── 均线状态 ──
    df['ma5_above_10']   = (df['ma5'] > df['ma10']).astype(int)
    df['ma5_above_20']   = (df['ma5'] > df['ma20']).astype(int)
    df['ma10_above_20']  = (df['ma10'] > df['ma20']).astype(int)
    df['ma_bull']        = ((df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20'])).astype(int)
    df['ma_bear']        = ((df['ma5'] < df['ma10']) & (df['ma10'] < df['ma20'])).astype(int)
    df['ma_diff_5_20']   = (df['ma5'] - df['ma20']) / df['ma20']

    # ── ATR ──
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low']  - df['close'].shift(1)).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    for p in [7, 14, 28]:
        df[f'atr{p}'] = tr.rolling(p).mean()
        df[f'atr{p}_ratio'] = df[f'atr{p}'] / (df['close'] + 1e-10)

    # ── RSI ──
    def calc_rsi(series, period):
        delta = series.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / (loss + 1e-10)
        return 100 - 100 / (1 + rs)
    for period in [6, 9, 14, 21]:
        df[f'rsi{period}'] = calc_rsi(df['close'], period)

    # ── KDJ ──
    k_list = [None] * n_rows
    d_list = [None] * n_rows
    for i in range(8, n_rows):
        ln = df['low'].iloc[i-8:i+1].min()
        hn = df['high'].iloc[i-8:i+1].max()
        rsv = (df['close'].iloc[i] - ln) / (hn - ln) * 100 if hn != ln else 50
        k_prev = k_list[i-1] if k_list[i-1] is not None else 50
        d_prev = d_list[i-1] if d_list[i-1] is not None else 50
        k_list[i] = 2/3 * k_prev + 1/3 * rsv
        d_list[i] = 2/3 * d_prev + 1/3 * k_list[i]
    df = df.assign(kdj_k=pd.Series(k_list, index=df.index))
    df['kdj_d']     = pd.Series(d_list, index=df.index)
    df['kdj_j']     = [3*k-2*d if k is not None and d is not None else None
                        for k, d in zip(k_list, d_list)]
    df['kdj_kd_diff'] = pd.Series([k-d if k is not None and d is not None else None
                                     for k, d in zip(k_list, d_list)], index=df.index)

    # ── MACD ──
    def ema(s, period):
        k = 2/(period+1)
        r = [s.iloc[0]]
        for i in range(1, len(s)): r.append(s.iloc[i]*k + r[-1]*(1-k))
        return pd.Series(r, index=s.index)
    e12 = ema(df['close'], 12)
    e26 = ema(df['close'], 26)
    dif, dea = e12 - e26, ema(e12 - e26, 9)
    df['macd_hist']     = (dif - dea) * 2
    df['macd_hist_prev'] = df['macd_hist'].shift(1)
    df['macd_dif']     = dif
    df['macd_dea']     = dea
    df['macd_cross']   = ((dif > dea) & (dif.shift(1) <= dea.shift(1))).astype(int)
    df['macd_death']   = ((dif < dea) & (dif.shift(1) >= dea.shift(1))).astype(int)
    df['macd_bull']    = (df['macd_hist'] > 0).astype(int)
    df['macd_expanding'] = (df['macd_hist'] > df['macd_hist'].shift(1)).astype(int)

    # ── 布林带 ──
    bm = df['close'].rolling(20).mean()
    bs = df['close'].rolling(20).std()
    df['boll_upper'] = bm + 2*bs
    df['boll_lower'] = bm - 2*bs
    df['boll_ratio'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'] + 1e-10)
    df['boll_pos']   = (df['close'] - bm) / (2*bs + 1e-10)
    df['boll_width']  = 2*bs / bm

    # ── Williams%R + CCI + MFI ──
    rh14 = df['high'].rolling(14).max()
    rl14 = df['low'].rolling(14).min()
    df['williams_r'] = -100 * (rh14 - df['close']) / (rh14 - rl14 + 1e-10)
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(14).mean()
    mad = tp.rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df['cci'] = (tp - sma_tp) / (0.015 * mad + 1e-10)
    # MFI
    mf = tp * df['volume']
    pos_flow = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_flow = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
    mfr = pos_flow / (neg_flow + 1)
    df['mfi'] = 100 - 100 / (1 + mfr)

    # ── OBV ──
    obv = [0.0] * n_rows
    for i in range(1, n_rows):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv[i] = obv[i-1] + df['volume'].iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv[i] = obv[i-1] - df['volume'].iloc[i]
        else:
            obv[i] = obv[i-1]
    df['obv']        = obv
    df['obv_ma5']   = df['obv'].rolling(5).mean()
    df['obv_ratio'] = df['obv'] / (df['obv_ma5'] + 1)

    # ── 成交量 ──
    for w in [5, 10]:
        df[f'vol_ma{w}'] = df['volume'].rolling(w).mean()
    df['vol_ratio'] = df['volume'] / (df['vol_ma5'] + 1)
    df['vol_up']    = (df['close'] > df['open']).astype(int)
    df['vol_up3']   = df['vol_up'].rolling(3).sum()
    df['vol_up5']   = df['vol_up'].rolling(5).sum()

    # ── 连续涨跌 ──
    streak_up = [None] * n_rows
    streak_dn = [None] * n_rows
    cu, cd = 0, 0
    streak_up[0] = 0
    streak_dn[0] = 0
    for i in range(1, n_rows):
        if df['close'].iloc[i] >= df['close'].iloc[i-1]:
            cu = cu + 1 if cu > 0 else 1
            cd = 0
        else:
            cd = cd + 1 if cd > 0 else 1
            cu = 0
        streak_up[i] = cu
        streak_dn[i] = cd
    df['streak_up'] = streak_up
    df['streak_dn'] = streak_dn

    # ── 价格位置 ──
    df['high20_max'] = df['high'].rolling(20).max()
    df['low20_min']  = df['low'].rolling(20).min()
    df['price_pos20'] = (df['close'] - df['low20_min']) / (df['high20_max'] - df['low20_min'] + 1e-10)
    df['price_pos5'] = (df['close'] - df['close'].rolling(5).min()) / \
                        (df['close'].rolling(5).max() - df['close'].rolling(5).min() + 1e-10)

    # ── 日内结构 ──
    df['body']        = df['close'] - df['open']
    df['body_ratio']  = df['body'] / (df['high'] - df['low'] + 1e-10)
    df['amplitude']   = (df['high'] - df['low']) / df['close']
    df['upper_shadow'] = (df['high'] - df[['open','close']].max(axis=1)) / (df['high'] - df['low'] + 1e-10)
    df['lower_shadow'] = (df[['open','close']].min(axis=1) - df['low']) / (df['high'] - df['low'] + 1e-10)

    # ── 动量 ──
    df['roc5']    = (df['close'] / df['close'].shift(5) - 1) * 100
    df['roc10']   = (df['close'] / df['close'].shift(10) - 1) * 100
    df['momentum'] = df['close'] - df['close'].shift(5)
    df['momentum10'] = df['close'] - df['close'].shift(10)

    # ── 滞后特征（历史模式）──
    for d in [1, 2, 3]:
        df[f'ret_lag{d}d'] = df['close'].pct_change(d).shift(1)
        df[f'vol_lag{d}d'] = df['volume'].pct_change(d).shift(1)

    # ── 成交量加权价格变化 ──
    df['vwap_ret'] = (df['close'] - df['open']) / (df['volume'] + 1)

    # ── 目标：次日涨跌（今日收盘后可计算）──
    df['next_return'] = df['close'].shift(-1) / df['close'] - 1
    df['target']      = (df['next_return'] > 0).astype(int)

    return df


# ─────────────────────────────────────────────
# 3. 精选特征列表
# ─────────────────────────────────────────────

FEATURES = [
    # 收益率
    'ret_1d', 'ret_2d', 'ret_3d', 'ret_5d', 'ret_8d', 'ret_10d',
    # 均线比值
    'ma3_ratio', 'ma5_ratio', 'ma10_ratio', 'ma20_ratio', 'ma60_ratio',
    'ma_diff_5_20',
    # 均线方向
    'ma5_up', 'ma10_up', 'ma20_up',
    'ma5_slope', 'ma10_slope', 'ma20_slope',
    # 均线状态
    'ma5_above_10', 'ma5_above_20', 'ma10_above_20', 'ma_bull', 'ma_bear',
    # ATR
    'atr7', 'atr14', 'atr28', 'atr7_ratio', 'atr14_ratio',
    # RSI
    'rsi6', 'rsi9', 'rsi14', 'rsi21',
    # KDJ
    'kdj_k', 'kdj_d', 'kdj_j', 'kdj_kd_diff',
    # MACD
    'macd_hist', 'macd_hist_prev', 'macd_dif', 'macd_dea',
    'macd_cross', 'macd_death', 'macd_bull', 'macd_expanding',
    # 布林带
    'boll_ratio', 'boll_pos', 'boll_width',
    # 辅助指标
    'williams_r', 'cci', 'mfi',
    # OBV
    'obv_ratio',
    # 成交量
    'vol_ratio', 'vol_up3', 'vol_up5',
    # 连续涨跌
    'streak_up', 'streak_dn',
    # 价格位置
    'price_pos20', 'price_pos5',
    # 日内
    'body_ratio', 'amplitude', 'upper_shadow', 'lower_shadow',
    # 动量
    'roc5', 'roc10', 'momentum', 'momentum10',
    # 滞后
    'ret_lag1d', 'ret_lag2d', 'ret_lag3d',
    'vol_lag1d', 'vol_lag2d', 'vol_lag3d',
    # VWAP
    'vwap_ret',
]


# ─────────────────────────────────────────────
# 4. 数据准备
# ─────────────────────────────────────────────

def prepare(df_raw):
    if len(df_raw) < 100:
        return None
    df = df_raw.copy().reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df = build_features(df)
    df = df.dropna(subset=FEATURES + ['target'])
    df = df.reset_index(drop=True)
    return df


# ─────────────────────────────────────────────
# 5. 模型工厂
# ─────────────────────────────────────────────

def get_base_models():
    """保守模型集合（防止过拟合）"""
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


def train_ensemble(X, y):
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    up_ratio = y.mean()
    threshold = 1.0 - up_ratio
    threshold = max(0.38, min(0.62, threshold))

    trained = {}
    for name, model in get_base_models():
        m = model.__class__(**model.get_params())
        m.fit(Xs, y)
        trained[name] = m

    weights = {'RF1': 1.0, 'RF2': 1.0, 'ET1': 1.0,
                'ET2': 1.0, 'GBM': 2.0, 'LR': 1.0}

    def predict_fn(X_new):
        X_new_s = scaler.transform(X_new)
        probs = np.array([m.predict_proba(X_new_s)[:, 1] for m in trained.values()])
        w = np.array([weights.get(n, 1.0) for n in trained.keys()])
        avg_prob = np.average(probs, axis=0, weights=w)
        preds = (avg_prob > threshold).astype(int)
        return preds, avg_prob

    return predict_fn, scaler, trained, threshold


def find_optimal_threshold(y_true, y_prob, thresholds=None):
    """遍历阈值找最优准确率"""
    if thresholds is None:
        thresholds = np.arange(0.40, 0.65, 0.01)
    best_th, best_acc = 0.5, 0
    for th in thresholds:
        preds = (y_prob > th).astype(int)
        acc = accuracy_score(y_true, preds)
        if acc > best_acc:
            best_acc = acc
            best_th  = th
    return best_th, best_acc


# ─────────────────────────────────────────────
# 6. Walk-Forward 回测（核心）
# ─────────────────────────────────────────────

def walkforward(df, symbol, train_w=250, test_w=30, step=10):
    """
    模拟真实预测：
    - 用 train_w 天历史训练
    - 预测接下来 test_w 天
    - 每 step 天重新训练
    """
    X   = df[FEATURES].values
    y   = df['target'].values
    n   = len(df)

    if n < train_w + test_w:
        return None, '数据不足'

    results   = []
    equity    = 1.0

    i = train_w
    while i + test_w <= n:
        X_train = X[i - train_w:i]
        y_train = y[i - train_w:i]

        if y_train.sum() < 10 or (len(y_train) - y_train.sum()) < 10:
            i += step; continue

        try:
            predict_fn, scaler, models, threshold = train_ensemble(X_train, y_train)
        except Exception:
            i += step; continue

        for j in range(i, min(i + test_w, n)):
            Xj = X[j].reshape(1, -1)
            pred, prob_up = predict_fn(Xj)
            real = int(y[j])
            ret  = df['next_return'].iloc[j] if not pd.isna(df['next_return'].iloc[j]) else 0

            pos_ret = ret if pred[0] == 1 else 0
            equity *= (1 + pos_ret)

            results.append({
                'date':    str(df['date'].iloc[j])[:10],
                'close':   df['close'].iloc[j],
                'predict': '涨↑' if pred[0] else '跌↓',
                'prob_up': round(prob_up[0] * 100, 1),
                'real':    '涨↑' if real else '跌↓',
                'correct': '✓' if pred[0] == real else '✗',
                'ret':     f'{ret*100:+.2f}%',
                'equity':  round(equity, 4),
            })
        i += step

    if not results:
        return None, '回测无结果'

    return pd.DataFrame(results), None


# ─────────────────────────────────────────────
# 7. 统计计算
# ─────────────────────────────────────────────

def compute_stats(res_df):
    n       = len(res_df)
    correct = (res_df['correct'] == '✓').sum()
    acc     = correct / n * 100 if n else 0

    up_df   = res_df[res_df['predict'] == '涨↑']
    dn_df   = res_df[res_df['predict'] == '跌↓']
    win_up  = (up_df['correct'] == '✓').sum() / max(len(up_df), 1) * 100
    win_dn  = (dn_df['correct'] == '✓').sum() / max(len(dn_df), 1) * 100

    equity  = res_df['equity'].iloc[-1]
    total_r = (equity - 1) * 100

    dates   = pd.to_datetime(res_df['date'])
    days    = (dates.max() - dates.min()).days or 1
    ann_ret = total_r * 365 / days

    # 日收益序列
    daily_rets = []
    for _, r in res_df.iterrows():
        v = float(r['ret'].replace('%','').replace('+','')) / 100
        daily_rets.append(v if r['predict'] == '涨↑' else 0)
    ann_vol = np.std(daily_rets) * math.sqrt(252) * 100 if daily_rets else 0
    sharpe  = ann_ret / ann_vol if ann_vol > 0.01 else 0

    peak, max_dd = 1.0, 0
    for eq in res_df['equity']:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd: max_dd = dd

    return {
        'total':    n, 'correct': int(correct), 'accuracy': round(acc, 2),
        'win_up':   round(win_up, 2), 'win_dn': round(win_dn, 2),
        'equity':   round(equity, 4), 'total_ret': round(total_r, 2),
        'ann_ret':  round(ann_ret, 2), 'ann_vol': round(ann_vol, 2),
        'sharpe':   round(sharpe, 3), 'max_dd': round(max_dd, 2),
        'days':     days, 'up_preds': len(up_df), 'dn_preds': len(dn_df),
    }


# ─────────────────────────────────────────────
# 8. 今日预测
# ─────────────────────────────────────────────

def predict_today(df, symbol):
    X_all = df[FEATURES].values
    y_all = df['target'].values

    predict_fn, scaler, models, threshold = train_ensemble(X_all, y_all)
    X_last = X_all[-1].reshape(1, -1)
    pred, prob_up = predict_fn(X_last)

    # 特征重要性
    importance = None
    for name, m in models.items():
        if hasattr(m, 'feature_importances_'):
            fi = sorted(zip(FEATURES, m.feature_importances_), key=lambda x: x[1], reverse=True)
            importance = fi[:12]
            break

    # 各模型意见
    X_last_s = scaler.transform(X_last)
    model_probs = {name: m.predict_proba(X_last_s)[0][1] for name, m in models.items()}

    return {
        'date':         str(df['date'].iloc[-1])[:10],
        'close':        df['close'].iloc[-1],
        'prob_up':     round(prob_up[0] * 100, 1),
        'prob_down':   round((1 - prob_up[0]) * 100, 1),
        'pred':        '涨↑' if pred[0] else '跌↓',
        'confidence':  round(abs(prob_up[0] - 0.5) * 200, 1),
        'model_probs': model_probs,
        'top_features': importance,
    }


# ─────────────────────────────────────────────
# 9. 批量回测
# ─────────────────────────────────────────────

SAMPLE_STOCKS = [
    'sh600519', 'sh600036', 'sh601318', 'sz000858', 'sz300750',
    'sh600276', 'sz000001', 'sh601888', 'sh600900', 'sz002594',
    'sh603259', 'sh600030', 'sz002415', 'sh600887', 'sh601012',
]


def batch_backtest(stocks):
    print(f'\n{"="*62}')
    print(f'  批量 Walk-Forward 回测: {len(stocks)} 只股票')
    print(f'{"="*62}\n')

    all_stats = []
    for sym in stocks:
        print(f'  {sym}...', end=' ', flush=True)
        rows = fetch_kline(sym, 240, 800)
        if not rows:
            print('数据获取失败'); continue
        df = prepare(pd.DataFrame(rows))
        if df is None:
            print('数据不足'); continue

        res_df, err = walkforward(df, sym, train_w=250, test_w=30, step=10)
        if err or res_df is None:
            print(f'失败: {err}'); continue

        stats = compute_stats(res_df)
        stats['symbol'] = sym
        all_stats.append(stats)

        print(f"准确率 {stats['accuracy']:>5.1f}% | 涨胜率 {stats['win_up']:.1f}% | 跌胜率 {stats['win_dn']:.1f}% | 收益 {stats['total_ret']:>+6.1f}%")

    if not all_stats:
        print('无有效结果'); return

    sdf = pd.DataFrame(all_stats)
    print(f'\n{"="*62}')
    print(f'  📊 批量回测汇总（{len(all_stats)} 只）')
    print(f'{"="*62}')
    print(f'  平均准确率:   {sdf["accuracy"].mean():.1f}%')
    print(f'  胜率(≥55%):  {(sdf["accuracy"]>=55).sum()}/{len(sdf)} ({(sdf["accuracy"]>=55).mean()*100:.0f}%)')
    print(f'  胜率(≥60%):  {(sdf["accuracy"]>=60).sum()}/{len(sdf)} ({(sdf["accuracy"]>=60).mean()*100:.0f}%)')
    print(f'  胜率(≥65%):  {(sdf["accuracy"]>=65).sum()}/{len(sdf)} ({(sdf["accuracy"]>=65).mean()*100:.0f}%)')
    print(f'  最高准确率:   {sdf["accuracy"].max():.1f}%  最低: {sdf["accuracy"].min():.1f}%')
    print(f'  平均模拟收益: {sdf["total_ret"].mean():+.1f}%')
    print(f'  平均夏普比率: {sdf["sharpe"].mean():.3f}')
    print(f'{"="*62}\n')

    print(f'  {"股票":<12} {"准确率":>8} {"涨胜率":>8} {"跌胜率":>8} {"模拟收益":>10} {"夏普":>8}')
    print(f'  {"-"*12} {"-"*8} {"-"*8} {"-"*8} {"-"*10} {"-"*8}')
    for _, r in sdf.sort_values('accuracy', ascending=False).iterrows():
        e = '🟢' if r['accuracy'] >= 60 else ('🔴' if r['accuracy'] < 50 else '🟡')
        print(f'  {r["symbol"]:<12} {e}{r["accuracy"]:>7.1f}% {r["win_up"]:>7.1f}% {r["win_dn"]:>7.1f}% {r["total_ret"]:>+9.1f}% {r["sharpe"]:>8.3f}')

    return sdf


# ─────────────────────────────────────────────
# 10. 报告输出
# ─────────────────────────────────────────────

def print_report(df, pred, stats=None, res_df=None):
    print()
    print('═' * 62)
    print(f'  🔮 明日涨跌预测  |  {str(df["symbol"].iloc[-1]).upper()}  |  数据日: {pred["date"]}')
    print(f'  今日收盘价: {pred["close"]}')
    print('═' * 62)
    print()
    emoji = '🟢' if '涨' in pred['pred'] else '🔴'
    print(f'  ┌─ 🎯 预测结果')
    print(f'  │  {emoji} {pred["pred"]}  上涨概率: {pred["prob_up"]}%  下跌概率: {pred["prob_down"]}%')
    print(f'  │  置信度: {pred["confidence"]}%')
    print(f'  └')
    print()
    print(f'  ┌─ 📊 各模型投票')
    for name, prob in pred['model_probs'].items():
        e = '🟢' if prob > 0.5 else '🔴'
        print(f'  │  {name:<6} {e} 涨:{prob*100:.0f}% 跌:{(1-prob)*100:.0f}%')
    print(f'  └')
    if pred['top_features']:
        print()
        print(f'  ┌─ 📌 关键因子')
        for fname, imp in pred['top_features'][:10]:
            bar = '█' * int(imp * 500)
            print(f'  │  {fname:<22} {bar} {imp:.4f}')
        print(f'  └')
    if stats:
        print()
        acc_e = '🟢' if stats['accuracy'] >= 55 else ('🔴' if stats['accuracy'] < 50 else '🟡')
        bar   = '█' * int(stats['accuracy'] / 5) + '░' * (20 - int(stats['accuracy'] / 5))
        print(f'  ┌─ 📈 Walk-Forward 回测（{stats["days"]}天）')
        print(f'  │  {acc_e} [{bar}] {stats["accuracy"]}%  ({stats["correct"]}/{stats["total"]} 正确)')
        print(f'  │  预测涨胜率: {stats["win_up"]:.1f}%  预测跌胜率: {stats["win_dn"]:.1f}%')
        print(f'  │  模拟收益: {stats["total_ret"]:+.1f}%  夏普: {stats["sharpe"]:.3f}  最大回撤: {stats["max_dd"]:.1f}%')
        print(f'  └')
        if res_df is not None:
            print()
            print(f'  ┌─ 📋 近期预测（最后20条）')
            print(f'  │  {"日期":<12} {"收盘":>8} {"预测":>4} {"概率":>6} {"实际":>4} {"结果":>2} {"收益":>8} {"净值":>8}')
            print(f'  │  {"-"*12} {"-"*8} {"-"*4} {"-"*6} {"-"*4} {"-"*2} {"-"*8} {"-"*8}')
            for _, r in res_df.tail(20).iterrows():
                print(f'  │  {r["date"]:<12} {r["close"]:>8.2f} {r["predict"]:>4} {r["prob_up"]:>5.1f}% {r["real"]:>4} {r["correct"]:>2} {r["ret"]:>8} {r["equity"]:>8.4f}')
            print(f'  └')
    print()
    print('═' * 62)


# ─────────────────────────────────────────────
# 11. 主程序
# ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    sym  = next((a for a in args if a.startswith('sh') or a.startswith('sz')), 'sh600519')
    is_batch = '--backtest' in args and sym == 'sh600519' and not any(a.startswith(('sh', 'sz')) for a in args)

    # 如果有明确的股票参数加--backtest，只跑单只
    single_back = '--backtest' in args and any(a.startswith(('sh', 'sz')) for a in args)

    if is_batch and len([a for a in args if a.startswith(('sh','sz'))]) == 0:
        batch_backtest(SAMPLE_STOCKS)
        return

    print(f'\n{"="*62}')
    print(f'  股票明日涨跌预测系统 v4')
    print(f'  生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*62}')

    print(f'\n获取 {sym} 历史数据...')
    rows = fetch_kline(sym, 240, 800)
    if not rows:
        print('数据获取失败'); return
    df = prepare(pd.DataFrame(rows))
    if df is None:
        print('数据不足'); return
    df['symbol'] = sym
    print(f'有效数据 {len(df)} 条，特征 {len(FEATURES)} 个')

    print('\n运行 Walk-Forward 回测...')
    res_df, err = walkforward(df, sym, train_w=250, test_w=30, step=10)
    stats = compute_stats(res_df) if res_df is not None else None

    print()
    pred = predict_today(df, sym)
    print_report(df, pred, stats, res_df)

    if res_df is not None:
        out_csv = f'/Users/jjjj/Documents/股票/predict_{sym}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        res_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
        print(f'  📄 预测明细: {out_csv}')


if __name__ == '__main__':
    main()
