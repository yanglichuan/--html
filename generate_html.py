import json
import re

data = """
- 深华发Ａ (000020)
- 中国天楹 (000035)
- 深南电A (000037)
- 中洲控股 (000042)
- 粤高速Ａ (000429)
- 珠海港 (000507)
- 华塑控股 (000509)
- 荣安地产 (000517)
- 建投能源 (000600)
- 盈方微 (000670)
- 宝新能源 (000690)
- 湖南发展 (000722)
- 四川美丰 (000731)
- 和展能源 (000809)
- 冀东装备 (000856)
- 湖北能源 (000883)
- 中粮科技 (000930)
- 冀中能源 (000937)
- 中捷资源 (002021)
- 登海种业 (002041)
- 中泰化学 (002092)
- 兴化股份 (002109)
- 兆新股份 (002256)
- 陕天然气 (002267)
- 理工能科 (002322)
- 雅博股份 (002323)
- 棕榈股份 (002431)
- 山东墨龙 (002490)
- 协鑫集成 (002506)
- 江苏国信 (002608)
- 贝肯能源 (002828)
- 苏州银行 (002966)
- 金龙机电 (300032)
- 尤洛卡 (300099)
- 通裕重工 (300185)
- 日科化学 (300214)
- 开尔新材 (300234)
- 珈伟新能 (300317)
- 天壕能源 (300332)
- 天能重工 (300569)
- 迦南智能 (300880)
- 尤安设计 (300983)
- 扬电科技 (301012)
- 科源制药 (301281)
- 皖通高速 (600012)
- 新疆天业 (600075)
- 中信尼雅 (600084)
- 广州发展 (600098)
- 三峡水利 (600116)
- 中闽能源 (600163)
- 红星发展 (600367)
- 盘江股份 (600395)
- 宁夏建材 (600449)
- 六国化工 (600470)
- 上海能源 (600508)
- 淮河能源 (600575)
- 国新能源 (600617)
- 太极实业 (600667)
- 金瑞矿业 (600714)
- 华银电力 (600744)
- 辽宁能源 (600758)
- 洲际油气 (600759)
- 通宝能源 (600780)
- 新奥股份 (600803)
- 新天绿能 (600956)
- 大秦铁路 (601006)
- 厦门银行 (601187)
- 林洋能源 (601222)
- 绿色动力 (601330)
- 北元集团 (601568)
- 中国电建 (601669)
- 潞安环能 (601699)
- 宁波建工 (601789)
- 中衡设计 (603017)
- 德力佳 (603092)
- 芯能科技 (603105)
- 镇洋发展 (603213)
- 日月股份 (603218)
- 振德医疗 (603301)
- 水发燃气 (603318)
- 鼎信通讯 (603421)
- 韩建河山 (603616)
- 江苏新能 (603693)
- 南卫股份 (603880)
- 城地香江 (603887)
- 同力天启 (605286)
- 博睿数据 (688229)
- 英诺特 (688253)
- 固德威 (688390)
"""

stocks = []
for line in data.strip().split('\n'):
    match = re.search(r'-\s*(.+?)\s*\((\d{6})\)', line)
    if match:
        stocks.append({'name': match.group(1).strip(), 'code': match.group(2)})

html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回调反弹分析 - 股票查看器</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; background-color: #f5f5f5; }
        #sidebar { width: 320px; background: #fff; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; box-shadow: 2px 0 5px rgba(0,0,0,0.05); z-index: 10; }
        .instructions { padding: 15px; background: #e3f2fd; color: #0d47a1; font-size: 14px; text-align: center; border-bottom: 1px solid #bbdefb; font-weight: 500; }
        .instructions kbd { background: #fff; border: 1px solid #ccc; padding: 2px 6px; border-radius: 4px; box-shadow: 0 1px 1px rgba(0,0,0,0.2); margin: 0 3px; font-family: monospace; }
        #stock-list { flex: 1; overflow-y: auto; }
        .stock-item { padding: 12px 20px; border-bottom: 1px solid #f0f0f0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background-color 0.2s; }
        .stock-item:hover { background: #f9f9f9; }
        .stock-item.active { background: #e3f2fd; border-left: 4px solid #1976d2; padding-left: 16px; }
        .stock-name { font-weight: 500; color: #333; }
        .stock-code { font-family: monospace; color: #666; font-size: 13px; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
        .stock-item.active .stock-name { color: #1976d2; }
        .stock-item.active .stock-code { background: #bbdefb; color: #0d47a1; }
        #content { flex: 1; display: flex; flex-direction: column; background: #fff; }
        #header { padding: 15px 20px; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; justify-content: space-between; }
        #header h2 { margin: 0; font-size: 20px; color: #333; }
        #header .selected-stock-info { font-size: 14px; color: #666; }
        #chart-container { flex: 1; position: relative; }
        /* Scrollbar styles */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="instructions">
            支持使用键盘 <kbd>↑</kbd> <kbd>↓</kbd> 快速切换股票
        </div>
        <div id="stock-list"></div>
    </div>
    <div id="content">
        <div id="header">
            <h2 id="current-title">正在加载...</h2>
            <div class="selected-stock-info" id="current-info"></div>
        </div>
        <div id="chart-container">
            <!-- TradingView Widget BEGIN -->
            <div class="tradingview-widget-container" style="height:100%;width:100%">
              <div id="tradingview_chart" style="height:100%;width:100%"></div>
            </div>
            <!-- TradingView Widget END -->
        </div>
    </div>

    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script>
        const stocks = __STOCKS_JSON__;
        let currentIndex = 0;
        let widget = null;

        function getTVSymbol(code) {
            // TradingView expects SSE/SZSE prefix for Chinese stocks
            if (code.startsWith('6')) return 'SSE:' + code;
            return 'SZSE:' + code;
        }

        function renderList() {
            const listEl = document.getElementById('stock-list');
            listEl.innerHTML = '';
            stocks.forEach((stock, index) => {
                const div = document.createElement('div');
                div.className = 'stock-item' + (index === currentIndex ? ' active' : '');
                div.innerHTML = `<span class="stock-name">${stock.name}</span><span class="stock-code">${stock.code}</span>`;
                div.onclick = () => selectStock(index);
                div.id = 'stock-' + index;
                listEl.appendChild(div);
            });
        }

        function selectStock(index) {
            if (index < 0) index = 0;
            if (index >= stocks.length) index = stocks.length - 1;
            
            const oldIndex = currentIndex;
            currentIndex = index;
            
            // Update UI list without full re-render
            const oldItem = document.getElementById('stock-' + oldIndex);
            if (oldItem) oldItem.classList.remove('active');
            
            const newItem = document.getElementById('stock-' + currentIndex);
            if (newItem) {
                newItem.classList.add('active');
                // Scroll into view if needed
                newItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

            const stock = stocks[currentIndex];
            document.getElementById('current-title').innerText = `${stock.name} (${stock.code})`;
            document.getElementById('current-info').innerText = `第 ${currentIndex + 1} / ${stocks.length} 只`;

            updateChart(stock.code);
        }

        function updateChart(code) {
            const symbol = getTVSymbol(code);
            const widgetConfig = {
                "autosize": true,
                "symbol": symbol,
                "interval": "D",
                "range": "12M",  // 1 Year range
                "timezone": "Asia/Shanghai",
                "theme": "light",
                "style": "1",    // Candlesticks
                "locale": "zh_CN",
                "enable_publishing": false,
                "hide_top_toolbar": false,
                "hide_legend": false,
                "save_image": false,
                "container_id": "tradingview_chart"
            };

            // TradingView widget doesn't have a clean update method that works reliably across all setups,
            // re-initializing is fast enough and ensures the correct range and symbol.
            document.getElementById('tradingview_chart').innerHTML = '';
            widget = new TradingView.widget(widgetConfig);
        }

        window.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectStock(currentIndex - 1);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectStock(currentIndex + 1);
            }
        });

        // Init
        renderList();
        if (stocks.length > 0) {
            selectStock(0);
        }
    </script>
</body>
</html>"""

html_content = html_template.replace('__STOCKS_JSON__', json.dumps(stocks, ensure_ascii=False))

with open('/Users/jjjj/Documents/股票/stock_viewer.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Successfully generated /Users/jjjj/Documents/股票/stock_viewer.html")
