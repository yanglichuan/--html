import akshare as ak
try:
    print("Testing stock_info_a_code_name...")
    df = ak.stock_info_a_code_name()
    print(df.head())
    print("Total:", len(df))
except Exception as e:
    print(f"Failed: {e}")
