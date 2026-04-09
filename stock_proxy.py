"""
股票数据本地代理服务
用 curl 作为后端绕过 TLS 指纹检测，解决 eastmoney 访问限制
"""
from flask import Flask, request, Response
import urllib.request
import urllib.error
import socket

app = Flask(__name__)

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

EM_BASE = 'http://push2delay.eastmoney.com'
EM_HIS = 'http://push2his.eastmoney.com'
EM_STOCK = 'http://push2delay.eastmoney.com'

# 解析可以绕过限制的 IP
try:
    BYPASS_IP = socket.gethostbyname('push2delay.eastmoney.com')
except Exception:
    BYPASS_IP = '101.226.30.136' # Fallback IP

def fetch_data(url, host=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://quote.eastmoney.com/',
        'Origin': 'https://quote.eastmoney.com'
    }
    if host:
        headers['Host'] = host
        
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except urllib.error.URLError as e:
        raise Exception(f'Fetch failed: {e}')


@app.route('/proxy/clist', methods=['GET'])
def proxy_clist():
    qs = request.query_string.decode('utf-8')
    url = f'http://{BYPASS_IP}/api/qt/clist/get?{qs}'
    try:
        data = fetch_data(url, host='push2delay.eastmoney.com')
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/proxy/stock', methods=['GET'])
def proxy_stock():
    qs = request.query_string.decode('utf-8')
    url = f'http://{BYPASS_IP}/api/qt/stock/get?{qs}'
    try:
        data = fetch_data(url, host='push2delay.eastmoney.com')
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/proxy/kline', methods=['GET'])
def proxy_kline():
    qs = request.query_string.decode('utf-8')
    # Use bypass IP directly to bypass TLS/curl block on push2his edge nodes
    url = f'http://{BYPASS_IP}/api/qt/stock/kline/get?{qs}'
    try:
        data = fetch_data(url, host='push2his.eastmoney.com')
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/proxy/trends', methods=['GET'])
def proxy_trends():
    qs = request.query_string.decode('utf-8')
    url = f'http://{BYPASS_IP}/api/qt/stock/trends/get?{qs}'
    try:
        data = fetch_data(url, host='push2delay.eastmoney.com')
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/health', methods=['GET'])
def health():
    import json
    resp = Response(json.dumps({'status': 'ok'}), mimetype='application/json')
    return add_cors_headers(resp)


if __name__ == '__main__':
    print('=' * 50)
    print('股票数据本地代理服务 (urllib 后端)')
    print(f'动态绕过 IP: {BYPASS_IP}')
    print('服务地址: http://localhost:9500')
    print('=' * 50)
    app.run(host='0.0.0.0', port=9500, debug=False)
