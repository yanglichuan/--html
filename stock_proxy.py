"""
股票数据本地代理服务
用 curl 作为后端绕过 TLS 指纹检测，解决 eastmoney 访问限制
"""
from flask import Flask, request, Response
import subprocess
import shlex

app = Flask(__name__)

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

EM_BASE = 'https://push2delay.eastmoney.com'
EM_HIS = 'https://push2his.eastmoney.com'
EM_STOCK = 'https://push2delay.eastmoney.com'


def curl_get(url, host=None):
    cmd = [
        'curl', '-s', '--max-time', '15',
        '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
        '-H', 'Referer: https://quote.eastmoney.com/',
        '-H', 'Origin: https://quote.eastmoney.com',
    ]
    if host:
        cmd.extend(['-H', f'Host: {host}'])
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace')
        raise Exception(f'curl failed: {err}')
    return result.stdout


@app.route('/proxy/clist', methods=['GET'])
def proxy_clist():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_BASE}/api/qt/clist/get?{qs}'
    try:
        data = curl_get(url)
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/proxy/stock', methods=['GET'])
def proxy_stock():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_STOCK}/api/qt/stock/get?{qs}'
    try:
        data = curl_get(url)
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/proxy/kline', methods=['GET'])
def proxy_kline():
    qs = request.query_string.decode('utf-8')
    # Use push2delay's IP directly to bypass TLS/curl block on push2his edge nodes
    url = f'http://101.226.30.136/api/qt/stock/kline/get?{qs}'
    try:
        data = curl_get(url, host='push2his.eastmoney.com')
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(f'{{"error":"{e}"}}', mimetype='application/json', status=502))


@app.route('/proxy/trends', methods=['GET'])
def proxy_trends():
    qs = request.query_string.decode('utf-8')
    url = f'{EM_STOCK}/api/qt/stock/trends/get?{qs}'
    try:
        data = curl_get(url)
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
    print('股票数据本地代理服务 (curl 后端)')
    print('服务地址: http://localhost:9500')
    print('=' * 50)
    app.run(host='0.0.0.0', port=9500, debug=False)
