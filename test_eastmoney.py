import asyncio
import aiohttp
import pandas as pd

async def fetch_kline(secid):
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=1&end=20500101&lmt=200"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if not data or not data['data'] or not data['data']['klines']:
                return None
            klines = data['data']['klines']
            rows = []
            for k in klines:
                parts = k.split(',')
                rows.append({
                    'date': parts[0],
                    'open': float(parts[1]),
                    'close': float(parts[2]),
                    'high': float(parts[3]),
                    'low': float(parts[4]),
                    import asyncio