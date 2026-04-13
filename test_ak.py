import akshare as ak
try:
    print("Testing hist data Sina with qfq...")
    df = ak.stock_zh_a_daily(symbol="sz002625", start_date="20250101", end_date="20250410", adjust="qfq")
    print(df.head())
except Exception as e:
    print(f"Hist Sina failed: {e}")
