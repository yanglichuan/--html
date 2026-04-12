"""
新浪股票接口代理服务（独立版本）
不依赖现有的 stock_proxy.py
"""
from flask import Flask, request, Response
import urllib.request
import urllib.error
import json

app = Flask(__name__)

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Referer, User-Agent'
    return response

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        resp = Response('', status=204)
        return add_cors_headers(resp)

@app.route('/sina/rt', methods=['GET'])
def sina_realtime():
    """新浪实时行情 hq.sinajs.cn"""
    codes = request.args.get('codes', '')
    if not codes:
        return add_cors_headers(Response(json.dumps({'error': 'missing codes'}), mimetype='application/json', status=400))

    url = f'https://hq.sinajs.cn/list={codes}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://finance.sina.com.cn/',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        resp = Response(data, mimetype='text/plain; charset=gbk')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(json.dumps({'error': str(e)}), mimetype='application/json', status=502))

@app.route('/sina/kline', methods=['GET'])
def sina_kline():
    """新浪K线数据 money.finance.sina.com.cn"""
    symbol = request.args.get('symbol', '')
    scale = request.args.get('scale', '240')
    datalen = request.args.get('datalen', '60')
    if not symbol:
        return add_cors_headers(Response(json.dumps({'error': 'missing symbol'}), mimetype='application/json', status=400))

    url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale={scale}&ma=no&datalen={datalen}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://finance.sina.com.cn/',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        resp = Response(data, mimetype='application/json')
        return add_cors_headers(resp)
    except Exception as e:
        return add_cors_headers(Response(json.dumps({'error': str(e)}), mimetype='application/json', status=502))

@app.route('/health', methods=['GET'])
def health():
    resp = Response(json.dumps({'status': 'ok', 'service': 'sina-proxy'}), mimetype='application/json')
    return add_cors_headers(resp)

if __name__ == '__main__':
    print('=' * 50)
    print('新浪股票接口代理服务 (独立版)')
    print('服务地址: http://localhost:9600')
    print('接口:')
    print('  /sina/rt?codes=sh600519,sz000858')
    print('  /sina/kline?symbol=sh600519&scale=240&datalen=60')
    print('=' * 50)
    app.run(host='0.0.0.0', port=9600, debug=False)
