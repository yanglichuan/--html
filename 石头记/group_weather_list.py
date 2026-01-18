import pandas as pd
import json
import random

# File paths
excel_path = '/Users/jjjj/Documents/股票/石头记/AMap_adcode_citycode.xlsx'
output_html_path = '/Users/jjjj/Documents/股票/石头记/weather_list.html'

# 1. Load Data
try:
    df = pd.read_excel(excel_path)
    df['adcode'] = df['adcode'].astype(str)
except Exception as e:
    print(f"Error reading Excel: {e}")
    exit(1)

# 2. Extract Provinces (ends with 0000) to build a map: prefix -> Province Name
provinces = df[df['adcode'].str.endswith('0000')].copy()
provinces['prefix'] = provinces['adcode'].str.slice(0, 2)
province_map = dict(zip(provinces['prefix'], provinces['中文名']))

# 3. Extract Cities (ends with '市')
# This includes Direct-controlled municipalities like Beijing (110000) which are also provinces.
cities_df = df[df['中文名'].str.endswith('市')].copy()
cities_df['prefix'] = cities_df['adcode'].str.slice(0, 2)

# 4. Group Cities by Province
grouped_data = {} # { province_name: [city_rows] }

for _, row in cities_df.iterrows():
    prefix = row['prefix']
    province_name = province_map.get(prefix, "其他区域")
    
    if province_name not in grouped_data:
        grouped_data[province_name] = []
    
    # Identify level
    level = 'county'
    if row['adcode'].endswith('0000'):
        level = 'province'
    elif row['adcode'].endswith('00'):
        level = 'prefecture'
        
    city_info = {
        "中文名": row['中文名'],
        "adcode": row['adcode'],
        "citycode": str(row['citycode']),
        "level": level
    }
    grouped_data[province_name].append(city_info)

# 5. Generate Colors for Provinces
# A palette of distinct, nice distinct colors (gradients)
COLORS = [
    ("rgba(255, 107, 107, 0.2)", "#ff6b6b"), # Red
    ("rgba(78, 205, 196, 0.2)", "#4ecdc4"),  # Teal
    ("rgba(255, 230, 109, 0.2)", "#ffe66d"), # Yellow
    ("rgba(26, 83, 92, 0.4)", "#1a535c"),    # Dark Blue
    ("rgba(247, 255, 247, 0.2)", "#f7fff7"), # White/Green
    ("rgba(255, 51, 102, 0.2)", "#ff3366"),  # Pink
    ("rgba(51, 102, 255, 0.2)", "#3366ff"),  # Blue
    ("rgba(153, 51, 255, 0.2)", "#9933ff"),  # Purple
    ("rgba(0, 204, 153, 0.2)", "#00cc99"),   # Green
    ("rgba(255, 153, 51, 0.2)", "#ff9933"),  # Orange
    ("rgba(0, 191, 255, 0.2)", "#00bfff"),   # Deep Sky Blue
    ("rgba(255, 20, 147, 0.2)", "#ff1493"),  # Deep Pink
    ("rgba(123, 104, 238, 0.2)", "#7b68ee"), # Medium Slate Blue
    ("rgba(0, 250, 154, 0.2)", "#00fa9a"),   # Medium Spring Green
    ("rgba(255, 215, 0, 0.2)", "#ffd700"),   # Gold
]

# 6. HTML Construction
html_head = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>全国天气监控 - 分省版</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-bg: #0f2027;
            --text-color: #ffffff;
            --accent-color: #00d2ff;
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        
        body {
            margin: 0; padding: 0;
            font-family: 'Montserrat', -apple-system, sans-serif;
            background: var(--primary-bg);
            color: var(--text-color);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Fixed Background */
        #bg-canvas {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            z-index: -1;
            background: linear-gradient(to bottom, #203a43, #2c5364);
        }

        /* Header */
        .header {
            padding: 15px 20px;
            padding-top: max(15px, env(safe-area-inset-top));
            background: rgba(15, 32, 39, 0.95);
            backdrop-filter: blur(20px);
            z-index: 10;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }

        .app-title { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .status-bar { font-size: 12px; opacity: 0.7; display: flex; align-items: center; gap: 10px; }
        .progress-bar { width: 100px; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden; }
        .progress-fill { height: 100%; width: 0%; background: var(--accent-color); transition: width 0.3s; }
        .retry-badge { background: #e74c3c; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; display: none; }

        /* Main Content Area */
        .content-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            scroll-behavior: smooth;
        }

        /* Province Section */
        .province-section { margin-bottom: 30px; }
        
        .province-header {
            font-size: 18px; font-weight: 800; margin-bottom: 15px;
            display: flex; align-items: center;
            position: sticky; top: 0;
            z-index: 5;
            padding: 10px 0;
            background: rgba(15, 32, 39, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .province-dot {
            width: 12px; height: 12px; border-radius: 50%; margin-right: 10px;
            box-shadow: 0 0 10px currentColor;
        }

        .city-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 12px;
        }

        /* City Card - UPDATED for better visibility */
        .city-card {
            background: var(--card-bg, rgba(255,255,255,0.05));
            border: 1px solid rgba(255,255,255,0.1);
            border-left: 3px solid var(--province-color, #fff);
            border-radius: 12px;
            padding: 14px; /* Increased padding */
            display: flex; flex-direction: column; justify-content: space-between;
            min-height: 120px; /* Increased min-height */
            height: auto; /* Allow growth */
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative; overflow: hidden;
        }
        
        .city-card:active { transform: scale(0.96); }

        .city-name { font-size: 15px; font-weight: 700; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .city-temp { font-size: 32px; font-weight: 300; margin: 5px 0; }
        .city-weather { font-size: 13px; opacity: 0.9; display: flex; align-items: center; gap: 5px; }
        .city-meta { font-size: 11px; opacity: 0.6; margin-top: 8px; display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 4px; }
        
        .loading-shimmer {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
            transform: translateX(-100%);
            animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer { 100% { transform: translateX(100%); } }
        
        .error-text { color: #e74c3c !important; }

        /* Detail Modal */
        .detail-modal {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(15, 32, 39, 0.95); backdrop-filter: blur(20px);
            z-index: 100; display: flex; flex-direction: column;
            transform: translateY(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 20px; padding-top: max(20px, env(safe-area-inset-top)); overflow-y: auto;
        }
        .detail-modal.active { transform: translateY(0); }
        .close-btn {
            position: absolute; top: max(20px, env(safe-area-inset-top)); right: 20px;
            width: 40px; height: 40px; border-radius: 50%; background: rgba(255,255,255,0.1);
            display: flex; align-items: center; justify-content: center; border: none; color: white; cursor: pointer; z-index: 101;
        }
        .glass-card {
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 24px; padding: 24px; margin-bottom: 20px;
        }
        .main-card { min-height: 300px; display: flex; flex-direction: column; justify-content: space-between; margin-top: 40px; }
        .temp-display-lg { font-size: 72px; font-weight: 200; margin: 10px 0; }
        .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .grid-item { padding: 15px; background: rgba(255,255,255,0.05); border-radius: 16px; }

        /* Search Bar */
        .search-wrapper {
            padding: 10px 20px;
            background: rgba(15, 32, 39, 0.6);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            gap: 10px;
            flex-shrink: 0;
            z-index: 9;
        }
        .search-input {
            flex: 1;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            padding: 8px 16px;
            color: white;
            font-size: 14px;
            outline: none;
            transition: background 0.3s;
        }
        .search-input:focus { background: rgba(255,255,255,0.15); border-color: var(--accent-color); }
        .search-btn {
            background: var(--accent-color);
            border: none;
            border-radius: 20px;
            padding: 0 20px;
            color: #0f2027;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
        }
        
        /* Highlight Animation */
        @keyframes highlight-pulse {
            0% { box-shadow: 0 0 0 0 rgba(0, 210, 255, 0.7); border-color: #00d2ff; transform: scale(1.02); }
            70% { box-shadow: 0 0 0 10px rgba(0, 210, 255, 0); border-color: #00d2ff; transform: scale(1.02); }
            100% { box-shadow: 0 0 0 0 rgba(0, 210, 255, 0); transform: scale(1); }
        }
        .highlight-target {
            animation: highlight-pulse 1.5s ease-in-out 3;
            z-index: 2;
            position: relative;
        }

    </style>
</head>
<body>
    <canvas id="bg-canvas"></canvas>
    
    <div class="header">
        <div class="app-title">
            <span>🗺 全国气象全景</span>
            <span style="font-size:12px; opacity:0.6; font-weight:400" id="city-count">0/0</span>
            <span class="retry-badge" id="retry-badge">重试中...</span>
        </div>
        <div class="status-bar">
            <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
        </div>
    </div>
    
    <div class="search-wrapper">
        <input type="text" class="search-input" id="search-input" placeholder="输入城市或省份 (如: 成都, 四川)...">
        <button class="search-btn" onclick="performSearch()">定位</button>
    </div>

    <div class="content-area" id="content-area">
        <!-- JS Generated Provinces -->
    </div>

    <!-- Detail View -->
    <div class="detail-modal" id="detail-modal">
        <button class="close-btn" onclick="closeDetail()">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
        <div class="glass-card main-card">
            <div><h2 id="detail-city" style="margin:0">--</h2><div id="detail-weather" style="font-size:20px; opacity:0.8; margin-top:5px">--</div></div>
            <div class="temp-display-lg" id="detail-temp">--°</div>
            <div style="opacity:0.6; font-size:14px" id="detail-time">更新于 --:--</div>
        </div>
        <div class="grid-container">
            <div class="grid-item"><span style="opacity:0.6; font-size:12px">湿度</span><span style="font-size:20px" id="detail-humidity">--%</span></div>
            <div class="grid-item"><span style="opacity:0.6; font-size:12px">风力</span><span style="font-size:20px" id="detail-wind">--</span></div>
            <div class="grid-item"><span style="opacity:0.6; font-size:12px">风向</span><span style="font-size:20px" id="detail-wind-dir">--</span></div>
            <div class="grid-item"><span style="opacity:0.6; font-size:12px">空气质量</span><span style="font-size:20px">良</span></div>
        </div>
    </div>

    <script>
        // 1. Embedded Grouped Data
"""

structured_data = []
all_cities_flat = []

sorted_provinces = sorted(grouped_data.keys())

for idx, prov in enumerate(sorted_provinces):
    cities = grouped_data[prov]
    color_bg, color_accent = COLORS[idx % len(COLORS)]
    
    structured_data.append({
        "province": prov,
        "color_bg": color_bg,
        "color_accent": color_accent,
        "cities": cities
    })
    
    for c in cities:
        c['province_idx'] = idx 
        all_cities_flat.append(c)

# Construct JS data strings
js_data = f"""
        const PROVINCE_DATA = {json.dumps(structured_data, ensure_ascii=False)};
        const ALL_CITIES = {json.dumps(all_cities_flat, ensure_ascii=False)};
        const API_KEY = '00d7800439d0976895b3ae049f384892';
"""

# Rest of JS (Static)
js_logic = """
        // 2. Render Structure
        function initView() {
            const container = document.getElementById('content-area');
            const fragment = document.createDocumentFragment();

            PROVINCE_DATA.forEach(group => {
                const section = document.createElement('div');
                section.className = 'province-section';
                
                const header = document.createElement('div');
                header.className = 'province-header';
                header.id = `prov-${group.province}`;
                header.style.color = group.color_accent;
                header.innerHTML = `<div class="province-dot" style="background:${group.color_accent}"></div>${group.province} <span style="font-size:12px; opacity:0.5; margin-left:10px; font-weight:400">(${group.cities.length})</span>`;
                
                const grid = document.createElement('div');
                grid.className = 'city-grid';
                
                group.cities.forEach(city => {
                    const card = document.createElement('div');
                    card.className = 'city-card';
                    card.id = `card-${city.adcode}`;
                    card.dataset.adcode = city.adcode;
                    // Set custom properties for colors
                    card.style.setProperty('--card-bg', group.color_bg);
                    card.style.setProperty('--province-color', group.color_accent);
                    
                    card.onclick = () => showDetail(city.adcode);
                    
                    card.innerHTML = `
                        <div class="loading-shimmer"></div>
                        <div>
                            <div class="city-name">${city.中文名}</div>
                            <div class="city-weather" id="weather-${city.adcode}">加载中...</div>
                        </div>
                        <div>
                            <div class="city-temp" id="temp-${city.adcode}">--°</div>
                            <div class="city-meta">
                                <span id="humid-${city.adcode}"></span>
                                <span id="wind-${city.adcode}"></span>
                            </div>
                        </div>
                    `;
                    grid.appendChild(card);
                });
                
                section.appendChild(header);
                section.appendChild(grid);
                fragment.appendChild(section);
            });
            
            container.appendChild(fragment);
            startFetching();
        }
        
        // 3. Web Worker Code (Blob)
        // Includes IndexedDB logic and Concurrent Fetching (20 threads)
        const workerCode = `
            const DB_NAME = 'WeatherDB';
            const DB_VERSION = 1;
            const STORE_NAME = 'weather_cache';
            const CACHE_DURATION = 3600 * 1000; // 1 hour

            let db;
            let apiKey;

            // Initialize IndexedDB
            function initDB() {
                return new Promise((resolve, reject) => {
                    const request = indexedDB.open(DB_NAME, DB_VERSION);
                    request.onerror = (e) => reject(e);
                    request.onsuccess = (e) => {
                        db = e.target.result;
                        resolve(db);
                    };
                    request.onupgradeneeded = (e) => {
                        const db = e.target.result;
                        if (!db.objectStoreNames.contains(STORE_NAME)) {
                            db.createObjectStore(STORE_NAME, { keyPath: 'adcode' });
                        }
                    };
                });
            }

            // DB Helpers
            function getFromCache(adcode) {
                return new Promise((resolve) => {
                    if (!db) return resolve(null);
                    const tx = db.transaction(STORE_NAME, 'readonly');
                    const store = tx.objectStore(STORE_NAME);
                    const req = store.get(adcode);
                    req.onsuccess = () => {
                        const record = req.result;
                        if (record && (Date.now() - record.timestamp < CACHE_DURATION)) {
                            resolve(record.data);
                        } else {
                            resolve(null);
                        }
                    };
                    req.onerror = () => resolve(null);
                });
            }

            function saveToCache(adcode, data) {
                if (!db) return;
                const tx = db.transaction(STORE_NAME, 'readwrite');
                const store = tx.objectStore(STORE_NAME);
                store.put({ adcode: adcode, data: data, timestamp: Date.now() });
            }

            let queue = [];
            let priorityQueue = [];
            let activeCount = 0;
            let successCount = 0;
            let failCount = 0;
            const poolSize = 20;

            // Worker Logic
            self.onmessage = async function(e) {
                const { type, cities, key, adcodes, adcode } = e.data;
                if (type === 'start') {
                    apiKey = key;
                    queue = [...cities];
                    await initDB();
                    processNext();
                } else if (type === 'PRIORITIZE') {
                    const targets = new Set(adcodes);
                    const moved = [];
                    let newQueue = [];
                    for (let c of queue) {
                        if (targets.has(c.adcode)) moved.push(c);
                        else newQueue.push(c);
                    }
                    queue = newQueue;
                    priorityQueue.push(...moved);
                    processNext();
                } else if (type === 'RETRY') {
                    priorityQueue.unshift({ adcode: adcode });
                    processNext();
                }
            };

            async function processNext() {
                if (queue.length === 0 && priorityQueue.length === 0 && activeCount === 0) {
                    self.postMessage({ type: 'DONE', success: successCount, fail: failCount });
                    return;
                }

                while (activeCount < poolSize && (priorityQueue.length > 0 || queue.length > 0)) {
                    let city;
                    if (priorityQueue.length > 0) city = priorityQueue.shift();
                    else city = queue.shift();
                    
                    activeCount++;
                    handleCity(city).then(() => {
                        activeCount--;
                        processNext();
                    });
                }
            }

            async function handleCity(city) {
                const adcode = city.adcode;
                
                // 1. Check Cache
                try {
                    const cached = await getFromCache(adcode);
                    if (cached) {
                        self.postMessage({ type: 'UPDATE', adcode, data: cached, source: 'cache' });
                        return;
                    }
                } catch (e) {
                    console.warn('Cache check failed', e);
                }

                // 2. Fetch Network
                await fetchWithRetry(adcode);
            }
            
            async function fetchWithRetry(adcode, retry = 0) {
                try {
                    const res = await fetch(\`https://restapi.amap.com/v3/weather/weatherInfo?key=\${apiKey}&city=\${adcode}&extensions=base&output=JSON\`);
                    if (!res.ok) throw new Error(\`HTTP \${res.status}\`);
                    const data = await res.json();

                    if (data.status === '1' && data.lives && data.lives.length > 0) {
                        const live = data.lives[0];
                        // Save to Cache
                        saveToCache(adcode, live);
                        // Notify Main Thread
                        self.postMessage({ type: 'UPDATE', adcode, data: live, source: 'network' });
                    } else {
                        if (data.info && (data.info.includes('LIMIT') || data.info.includes('QPS'))) {
                            throw new Error('LIMIT_EXCEEDED');
                        }
                        self.postMessage({ type: 'ERROR', adcode, msg: '无数据' });
                    }
                } catch (e) {
                    if (retry < 3) { // 3 Retries
                        const waitTime = 1000 * Math.pow(2, retry);
                        // Notify retry status (optional, maybe too noisy for 20 threads)
                        // self.postMessage({ type: 'RETRYING', adcode }); 
                        await new Promise(r => setTimeout(r, waitTime));
                        await fetchWithRetry(adcode, retry + 1);
                    } else {
                        self.postMessage({ type: 'ERROR', adcode, msg: '失败' });
                    }
                }
            }
        `;

        // 4. Main Thread Logic
        let weatherCache = new Map();
        let completedCount = 0;
        const totalCities = ALL_CITIES.length;
        let worker;

        function startFetching() {
            const blob = new Blob([workerCode], { type: 'application/javascript' });
            worker = new Worker(URL.createObjectURL(blob));
            
            worker.onmessage = function(e) {
                const msg = e.data;
                if (msg.type === 'UPDATE') {
                    weatherCache.set(msg.adcode, msg.data);
                    updateCard(msg.adcode, msg.data);
                    updateProgress();
                } else if (msg.type === 'ERROR') {
                    markError(msg.adcode, msg.msg);
                    updateProgress();
                } else if (msg.type === 'DONE') {
                    console.log('Worker finished all tasks.');
                    document.getElementById('retry-badge').style.display = 'none';
                }
            };

            const observer = new IntersectionObserver((entries) => {
                 const visibleAdcodes = [];
                 entries.forEach(entry => {
                     if (entry.isIntersecting) {
                         visibleAdcodes.push(entry.target.dataset.adcode);
                         observer.unobserve(entry.target);
                     }
                 });
                 if (visibleAdcodes.length > 0) {
                     worker.postMessage({ type: 'PRIORITIZE', adcodes: visibleAdcodes });
                 }
            }, { rootMargin: '200px' });
            
            document.querySelectorAll('.city-card').forEach(card => observer.observe(card));
            
            worker.postMessage({ type: 'start', cities: ALL_CITIES, key: API_KEY });
        }
        
        function updateCard(adcode, live) {
            const card = document.getElementById(`card-${adcode}`);
            if (!card) return;
            
            const temp = parseFloat(live.temperature);
            if (!isNaN(temp)) card.style.order = -Math.round(temp);
            else card.style.order = 1000;

            const shimmer = card.querySelector('.loading-shimmer');
            if (shimmer) shimmer.remove();
            
            document.getElementById(`temp-${adcode}`).innerText = live.temperature + '°';
            document.getElementById(`weather-${adcode}`).innerText = `${getEmoji(live.weather)} ${live.weather}`;
            document.getElementById(`humid-${adcode}`).innerText = `💧${live.humidity}%`;
            document.getElementById(`wind-${adcode}`).innerText = `💨${live.windpower}级`;

            card.onclick = () => showDetail(adcode);
            card.style.cursor = 'pointer';
            const retryInd = card.querySelector('.retry-indicator');
            if(retryInd) retryInd.remove();
        }
        
        function markError(adcode, msg) {
            const card = document.getElementById(`card-${adcode}`);
            const el = document.getElementById(`weather-${adcode}`);
            if(el) { el.innerText = msg; el.classList.add('error-text'); }
            
            const shimmer = card.querySelector('.loading-shimmer');
            if (shimmer) shimmer.remove();
            
            card.style.order = 9999;
            card.onclick = (e) => { e.stopPropagation(); retryFetch(adcode); };
            card.style.cursor = 'pointer';
            
            if(!card.querySelector('.retry-indicator')) {
                const retryInd = document.createElement('div');
                retryInd.className = 'retry-indicator';
                retryInd.innerText = '↺ 点击重试';
                retryInd.style.cssText = 'font-size:10px; color:#e74c3c; margin-top:5px;';
                card.querySelector('.city-meta').parentNode.appendChild(retryInd);
            }
        }
        
        function retryFetch(adcode) {
             const card = document.getElementById(`card-${adcode}`);
             const el = document.getElementById(`weather-${adcode}`);
             if(el) { el.innerText = "重试中..."; el.classList.remove('error-text'); }
             worker.postMessage({ type: 'RETRY', adcode: adcode });
        }
        
        function updateProgress() {
            completedCount++;
            if (completedCount > totalCities) completedCount = totalCities;
            const pct = (completedCount / totalCities) * 100;
            document.getElementById('progress-fill').style.width = `${pct}%`;
            document.getElementById('city-count').innerText = `${completedCount}/${totalCities}`;
        }
        
        function getEmoji(weather) {
            if (!weather) return '';
            if (weather.includes('晴')) return '☀️';
            if (weather.includes('雨')) return '🌧';
            if (weather.includes('云') || weather.includes('阴')) return '☁️';
            if (weather.includes('雪')) return '❄️';
            if (weather.includes('雾') || weather.includes('霾')) return '🌫';
            return '🌤';
        }

        // 5. Detail View Logic
        function showDetail(adcode) {
            const data = weatherCache.get(adcode);
            const city = ALL_CITIES.find(c => c.adcode === adcode);
            document.getElementById('detail-city').innerText = city.中文名;
            
            if (data) {
                document.getElementById('detail-weather').innerText = data.weather;
                document.getElementById('detail-temp').innerText = data.temperature + '°';
                document.getElementById('detail-time').innerText = '更新于 ' + data.reporttime;
                document.getElementById('detail-humidity').innerText = data.humidity + '%';
                document.getElementById('detail-wind').innerText = data.windpower + '级';
                document.getElementById('detail-wind-dir').innerText = data.winddirection;
            } else {
                 document.getElementById('detail-weather').innerText = "暂无数据";
                 document.getElementById('detail-temp').innerText = "--";
            }
            document.getElementById('detail-modal').classList.add('active');
        }
        function closeDetail() { document.getElementById('detail-modal').classList.remove('active'); }

        // 6. BG Animation
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');
        let particles = [];
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.addEventListener('resize', resize); resize();
        class Particle {
            constructor() { this.x = Math.random()*canvas.width; this.y = Math.random()*canvas.height; this.size = Math.random()*2; this.speedY = Math.random()*0.5; this.opacity = Math.random()*0.5; }
            update() { this.y -= this.speedY; if(this.y<0) this.y = canvas.height; }
            draw() { ctx.fillStyle = `rgba(255,255,255,${this.opacity})`; ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI*2); ctx.fill(); }
        }
        for(let i=0; i<50; i++) particles.push(new Particle());
        function animate() { ctx.clearRect(0,0,canvas.width,canvas.height); particles.forEach(p => {p.update(); p.draw();}); requestAnimationFrame(animate); }
        animate();

        // 7. Search Logic
        function performSearch() {
            const query = document.getElementById('search-input').value.trim();
            if (!query) return;

            // 1. Search Province
            const province = PROVINCE_DATA.find(p => p.province.includes(query) || query.includes(p.province));
            if (province) {
                const el = document.getElementById(`prov-${province.province}`);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    triggerHighlight(el);
                    return;
                }
            }

            // 2. Search City
            const city = ALL_CITIES.find(c => c.中文名.includes(query) || query.includes(c.中文名));
            if (city) {
                const el = document.getElementById(`card-${city.adcode}`);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    triggerHighlight(el);
                    return;
                }
            }
            
            alert('未找到相关省份或城市: ' + query);
        }

        function triggerHighlight(el) {
            document.querySelectorAll('.highlight-target').forEach(e => e.classList.remove('highlight-target'));
            void el.offsetWidth; // trigger reflow
            el.classList.add('highlight-target');
        }
        
        // Enter key to search
        document.getElementById('search-input').addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        // Start
        initView();
    </script>
</body>
</html>
"""

# Combine parts
full_html = html_head + js_data + js_logic

with open(output_html_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f"Generated grouped weather list with {len(grouped_data)} provinces.")
