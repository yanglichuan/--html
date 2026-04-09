"""
股票数据本地代理服务
用 python 内置 urllib 绕过拦截，解决 eastmoney 访问限制
"""
from flask import Flask, request, Response
import urllib.request
import urllib.error

app = Flask(__name__)

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

EM_BASE = 'https://push2delay.eastmoney.com'
EM_HIS = 'https://push2his.eastmoney.com'
EM_STOCK = 'https://push2delay.eastmoney.com'

def fetch_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://quote.eastmoney.com/',
        'Origin': 'https://quote.eastmoney.com'
    }
    
    # 测试：不使用任何 IP 替换，完全直接使用原始域名
    req_url = url
    if 'push2his.eastmoney.com' in url:
        try:
            import socket
            bypass_ip = socket.gethostbyname('push2delay.eastmoney.com')
            req_url = url.replace('push2his.eastmoney.com', bypass_ip)
        except Exception:
            pass
        headers['Host'] = 'push2his.eastmoney.com'
    elif 'push2delay.eastmoney.com' in url:
        try:
            import socket
            bypass_ip = socket.gethostbyname('push2delay.eastmoney.com')
            req_url = url.replace('push2delay.eastmoney.com', bypass_ip)
        except Exception:
            pass
        headers['Host'] = 'push2delay.eastmoney.com'

    # 当外层使用 HTTPS 时，由于我们将请求地址替换为了 IP，会导致 SSL 证书校验失败 (证书的主机名是 *.eastmoney.com 而不是 IP)
    # 所以当我们将域名替换为 IP 时，必须将协议降级为 HTTP，因为纯 HTTP 请求不校验 SSL 证书
    # 放心，对于这种公开的数据接口，降级到 HTTP 对业务本身没有任何影响
    if req_url.startswith('https://') and bypass_ip in req_url:
        req_url = req_url.replace('https://', 'http://')
        
    req = urllib.request.Request(req_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except urllib.error.URLError as e:
        raise Exception(f'Fetch failed: {e}')

@app.route('/proxy/clist', methods=['GET'])
def proxy_clist():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_BASE}/api/qt/clist/get?{qs}'
    try:
        data = fetch_data(url)
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))

@app.route('/proxy/stock', methods=['GET'])
def proxy_stock():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_STOCK}/api/qt/stock/get?{qs}'
    try:
        data = fetch_data(url)
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))

@app.route('/proxy/kline', methods=['GET'])
def proxy_kline():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_HIS}/api/qt/stock/kline/get?{qs}'
    try:
        data = fetch_data(url)
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))

@app.route('/proxy/trends', methods=['GET'])
def proxy_trends():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_STOCK}/api/qt/stock/trends/get?{qs}'
    try:
        data = fetch_data(url)
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
    print('服务地址: http://localhost:9500')
    print('=' * 50)
    app.run(host='0.0.0.0', port=9500, debug=False)
