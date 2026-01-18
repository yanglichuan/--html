import pandas as pd

file_path = '/Users/jjjj/Documents/股票/石头记/AMap_adcode_citycode.xlsx'
try:
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    print("First 5 rows:")
    print(df.head())
except Exception as e:
    print(f"Error reading excel: {e}")
