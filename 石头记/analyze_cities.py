import pandas as pd
import json

file_path = '/Users/jjjj/Documents/股票/石头记/AMap_adcode_citycode.xlsx'
output_json_path = '/Users/jjjj/Documents/股票/石头记/cities.json'

try:
    df = pd.read_excel(file_path)
    
    # Ensure adcode is string
    df['adcode'] = df['adcode'].astype(str)
    
    # Filter for cities (ending in '市')
    cities_df = df[df['中文名'].str.endswith('市')]
    
    # Additional logic: Identify level based on adcode
    # Province: ends with 0000
    # Prefecture: ends with 00 (but not 0000)
    # County: others
    
    def get_level(adcode):
        if adcode.endswith('0000'):
            return 'province'
        elif adcode.endswith('00'):
            return 'prefecture'
        else:
            return 'county'

    cities_df['level'] = cities_df['adcode'].apply(get_level)
    
    total_cities = len(cities_df)
    province_level_cities = len(cities_df[cities_df['level'] == 'province'])
    prefecture_level_cities = len(cities_df[cities_df['level'] == 'prefecture'])
    county_level_cities = len(cities_df[cities_df['level'] == 'county'])
    
    print(f"Total entries ending with '市': {total_cities}")
    print(f"Province-level cities (Direct-controlled municipalities): {province_level_cities}")
    print(f"Prefecture-level cities (e.g. Hangzhou): {prefecture_level_cities}")
    print(f"County-level cities (e.g. Yiwu): {county_level_cities}")
    
    # Prepare JSON data
    cities_list = cities_df[['中文名', 'adcode', 'citycode', 'level']].to_dict(orient='records')
    
    # Save to JSON
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(cities_list, f, ensure_ascii=False, indent=2)
        
    print(f"\nSaved city list to {output_json_path}")
    
    # Also count all prefecture-level divisions (including 州, 盟, 地区)
    prefecture_divisions = df[df['adcode'].str.endswith('00') & ~df['adcode'].str.endswith('0000')]
    print(f"\nTotal Prefecture-level divisions (ending in 00, excluding provinces): {len(prefecture_divisions)}")
    
    # Print first 5 cities as example
    print("\nExample cities:")
    print(cities_df[['中文名', 'adcode', 'level']].head())

except Exception as e:
    print(f"Error processing data: {e}")
