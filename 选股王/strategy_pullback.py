import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta
import os

def get_target_stock_list(retries=3):
    """
    获取A股标的池：全市场5000多只股票。
    过滤掉ST股、退市股等。
    """
    print("正在获取A股全市场股票列表...")
    
    try:
        if os.path.exists('stock_list_cache.csv'):
            print("  [提示] 正在使用本地缓存的股票列表...")
            df = pd.read_csv('stock_list_cache.csv')
            return df
    except Exception:
        pass

    for attempt in range(retries):
        try:
            df = ak.stock_info_a_code_name()
            df = df.rename(columns={'code': '代码', 'name': '名称'})
            df = df[~df['名称'].astype(str).str.contains('ST|退')]
            try:
                df[['代码', '名称']].to_csv('stock_list_cache.csv', index=False)
            except:
                pass
            return df[['代码', '名称']]
        except Exception as e:
            print(f"  [警告] 第 {attempt + 1} 次尝试获取股票列表失败: {e}")
            time.sleep(3)
            
    print("多次尝试获取股票列表失败，请检查您的网络连接或稍后再试。")
    return pd.DataFrame()

def fetch_kline_data(stock_code, retries=3):
    """
    通过 akshare 获取K线数据(前复权)
    """
    for attempt in range(retries):
        try:
            # 获取最近200个交易日的日K线，前复权
            df = ak.stock_zh_a_hist(symbol=str(stock_code), period="daily", adjust="qq")
            if df.empty or len(df) < 60:
                return None
            
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            })
            return df
        except Exception:
            time.sleep(0.5)
            continue
    return None

def check_pullback_and_rebound(stock_code, name):
    """
    核心选股逻辑：回调到位，企稳反弹
    """
    df = fetch_kline_data(stock_code)
    
    if df is None or len(df) < 60:
        return None

    try:
        # 计算移动平均线
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()

        last_row = df.iloc[-1]       # 今日
        prev_row = df.iloc[-2]       # 昨日
        row_5_ago = df.iloc[-5]      # 5天前

        # ----------------------------------------------------
        # 策略 1：长期趋势向上（60日均线必须是上升趋势）
        # ----------------------------------------------------
        if last_row['MA60'] <= row_5_ago['MA60']:
            return None

        # ----------------------------------------------------
        # 策略 2：短期回调到位（股价近期跌破20日均线，且靠近60日强支撑线）
        # ----------------------------------------------------
        if last_row['close'] > last_row['MA20']:
            return None # 还在20日线上方，不算充分回调
            
        # 距离60日均线的偏离度在3%以内（说明回踩到了支撑位）
        distance_to_ma60 = abs(last_row['close'] - last_row['MA60']) / last_row['MA60']
        if distance_to_ma60 > 0.03:
            return None

        # ----------------------------------------------------
        # 策略 3：企稳反弹信号（今日收红盘，且收盘价高于昨日）
        # ----------------------------------------------------
        if last_row['close'] <= last_row['open']:
            return None # 今日没收红（阴线），说明还在跌
            
        if last_row['close'] <= prev_row['close']:
            return None # 没能超越昨日收盘价，反弹力度不够

        # 满足所有条件，主力洗盘结束，即将开启新一轮上涨！
        return (stock_code, name)

    except Exception as e:
        return None

def run_scan(stock_list):
    total_stocks = len(stock_list)
    print(f"\n成功获取数据！共筛选出 {total_stocks} 只标的（已剔除ST和退市股）。")
    print("正在进行全市场5000多只股票的形态扫描...")
    print("由于股票数量庞大，扫描过程大约需要 15-20 分钟，请耐心等待...\n")

    selected_stocks = []
    count = 0
    
    for index, row in stock_list.iterrows():
        code = row['代码']
        name = row['名称']
        
        res = check_pullback_and_rebound(code, name)
        if res:
            selected_stocks.append(res)
            print(f"\n⭐ 发现目标: {name} ({code}) - 形态符合：回踩60日线并企稳收阳")
            
        count += 1
        if count % 100 == 0 or count == total_stocks:
            print(f"进度: 已扫描 {count} / {total_stocks} ...")
                
    return selected_stocks

def main():
    print("=====================================================")
    print("   选股王系统启动：【回调到位，即将启动】全市场扫描")
    print("=====================================================\n")
    
    start_time = time.time()
    stock_list = get_target_stock_list()
    if stock_list.empty:
        print("\n股票池为空，选股已终止。")
        return

    # 运行同步任务
    selected_stocks = run_scan(stock_list)

    print("\n=====================================================")
    print(f"扫描完成！全市场共发现 {len(selected_stocks)} 只符合【回调到位反弹】的股票：")
    print("=====================================================")
    if not selected_stocks:
        print("当前市场环境下，全市场中没有找到完全符合该严苛形态的股票。")
    else:
        for code, name in selected_stocks:
            print(f"- {name} ({code})")
            
    end_time = time.time()
    print(f"\n扫描总耗时: {end_time - start_time:.2f} 秒")
    print("\n提示：本系统选股结果仅供参考，不构成投资建议。")

if __name__ == "__main__":
    main()