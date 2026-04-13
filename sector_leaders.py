#!/usr/bin/env python3
"""获取每个板块的前5龙头股 - 东方财富接口"""

import ssl, urllib.request, json, time, csv

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UT = 'b2884a393a59ad64002292a3e90d46a5'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}

FIELDS_SECTOR = 'f12,f14,f3,f5,f6,f7'          # 板块列表字段
FIELDS_STOCK  = 'f12,f14,f3,f5,f6,f7,f8,f9,f10' # 个股字段

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
        text = r.read().decode('utf-8', errors='replace')
        # jsonp包装
        text = text.strip()
        if text.startswith('jQuery('):
            text = text[len('jQuery('):]
            if text.endswith(')'):
                text = text[:-1]
        return json.loads(text)

def get_all_sectors():
    """获取所有行业板块列表"""
    url = (f'https://push2.eastmoney.com/api/qt/clist/get?'
           f'pn=1&pz=200&po=1&np=1&ut={UT}&fltt=2&invt=2&fid=f6&fs=m:90+t:2'
           f'&fields=f12,f14,f3,f5,f6,f7,f8,f9,f10')
    data = fetch(url)
    return data.get('data', {}).get('diff', [])

def get_sector_stocks(bk_code, pn=1, pz=30):
    """获取某板块的成分股（按成交额排序）"""
    url = (f'https://push2.eastmoney.com/api/qt/clist/get?'
           f'pn={pn}&pz={pz}&po=1&np=1&ut={UT}&fltt=2&invt=2&fid=f6&fs=b:{bk_code}'
           f'&fields={FIELDS_STOCK}')
    data = fetch(url)
    total = data.get('data', {}).get('total', 0)
    diff  = data.get('data', {}).get('diff', [])
    return total, diff

def main():
    print('获取行业板块列表...')
    sectors = get_all_sectors()
    print(f'共 {len(sectors)} 个板块')

    # 板块按总成交额排序
    sectors.sort(key=lambda x: float(x.get('f6', 0)), reverse=True)

    results = []
    for i, sec in enumerate(sectors):
        bk_code  = sec.get('f12', '')
        bk_name  = sec.get('f14', bk_code)
        bk_chg   = sec.get('f3', 0)
        bk_amt   = float(sec.get('f6', 0))

        if bk_amt < 1e8:  # 成交额小于1亿跳过
            continue

        print(f'[{i+1}/{len(sectors)}] {bk_name}({bk_code}) 成交额{sec.get("f7","-"):}亿...', end='', flush=True)
        time.sleep(0.12)

        total, stocks = get_sector_stocks(bk_code, pz=30)
        if not stocks:
            print(' 无数据')
            continue

        # 按成交额排序取前5
        stocks.sort(key=lambda x: float(x.get('f6', 0)), reverse=True)
        top5 = stocks[:5]

        results.append({
            '板块名': bk_name,
            '板块代码': bk_code,
            '板块涨跌': bk_chg,
            '板块成交额亿': bk_amt / 1e8,
            'top5': top5
        })
        print(f' OK ({len(top5)}只)')

    print(f'\n共获取 {len(results)} 个板块数据')
    print('='*90)
    print('                    各板块前5龙头汇总')
    print('='*90)

    results.sort(key=lambda x: x['板块成交额亿'], reverse=True)

    all_rows = []
    for r in results:
        bk  = r['板块名']
        chg = r['板块涨跌']
        amt = r['板块成交额亿']
        top5 = r['top5']
        if not top5:
            continue
        print(f'\n【{bk}】{f"+{chg}" if chg>0 else str(chg)}%  板块成交额: {amt:.1f}亿')
        print(f'  {"代码":<10} {"名称":<12} {"现价":>8} {"涨跌%":>8} {"成交额(亿)":>10} {"换手%":>8}')
        print(f'  {"-"*58}')
        for s in top5:
            sym    = s.get('f12', '')
            name   = s.get('f14', sym)
            price  = s.get('f7', '-')
            schg   = s.get('f3', 0)
            vol_amt = float(s.get('f6', 0)) / 1e8
            turnover = s.get('f8', '-')  # 换手率
            chg_str  = f"{schg:+.2f}%" if schg != '-' else '-'
            print(f'  {sym:<10} {name:<12} {str(price):>8} {chg_str:>8} {vol_amt:>10.3f} {str(turnover):>8}')

        for s in top5:
            sym    = s.get('f12', '')
            name   = s.get('f14', sym)
            price  = s.get('f7', '-')
            schg   = s.get('f3', 0)
            vol_amt = float(s.get('f6', 0)) / 1e8
            turnover = s.get('f8', '-')
            all_rows.append([bk, sym, name, price,
                             f"{schg:+.2f}%" if schg != '-' else '-',
                             f"{vol_amt:.3f}",
                             str(turnover),
                             f"{amt:.1f}"])

    # 保存CSV
    with open('板块龙头汇总.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['板块', '代码', '名称', '现价', '涨跌%', '成交额(亿)', '换手%', '板块总成交额(亿)'])
        w.writerows(all_rows)

    print(f'\n已保存: 板块龙头汇总.csv (共{len(all_rows)}条)')

if __name__ == '__main__':
    main()