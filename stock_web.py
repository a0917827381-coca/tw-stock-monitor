from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
from scipy.signal import argrelextrema
import numpy as np

app = Flask(__name__)

# 網頁的版面設計 (HTML + CSS)，有做手機版響應式設計 (RWD)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的台股監控儀表板</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        .card { border-left: 5px solid #007bff; background: #f9f9f9; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
        .card.w-bottom { border-left-color: #ffc107; background: #fff8e1; }
        .stock-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .price-info { color: #555; line-height: 1.6; }
        .highlight { color: #d9534f; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 台股型態監控</h1>
        {% for result in results %}
            <div class="card {% if result.is_w %}w-bottom{% endif %}">
                <div class="stock-title">{{ result.ticker }}</div>
                <div class="price-info">
                    最新收盤價：{{ result.price }}<br>
                    {% if result.support %}近端支撐：{{ result.support }}<br>{% endif %}
                    {% if result.resist %}近端壓力：{{ result.resist }}<br>{% endif %}
                    {% if result.is_w %}<span class="highlight">⚠️ 疑似 W 底型態已成形！</span>{% endif %}
                </div>
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def analyze_stock(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="6mo")
    if df.empty:
        return {'ticker': ticker, 'price': '無資料', 'support': None, 'resist': None, 'is_w': False}
    
    prices = df['Close'].values
    local_min_idx = argrelextrema(prices, np.less, order=5)[0]
    local_max_idx = argrelextrema(prices, np.greater, order=5)[0]
    
    supports = prices[local_min_idx]
    resistances = prices[local_max_idx]
    current_price = round(prices[-1], 2)
    
    is_w_bottom = False
    if len(supports) >= 2:
        last_low = supports[-1]
        prev_low = supports[-2]
        if abs(last_low - prev_low) / prev_low < 0.03 and current_price > last_low:
            is_w_bottom = True

    return {
        'ticker': ticker,
        'price': current_price,
        'support': round(supports[-1], 2) if len(supports) > 0 else None,
        'resist': round(resistances[-1], 2) if len(resistances) > 0 else None,
        'is_w': is_w_bottom
    }

@app.route('/')
def index():
    watch_list = ['2330.TW', '2317.TW', '2454.TW'] # 你的觀察名單
    results = [analyze_stock(ticker) for ticker in watch_list]
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == '__main__':
    # 啟動網頁伺服器，port 設為 5000，host 設為 0.0.0.0 允許外部網路連線
    app.run(host='0.0.0.0', port=5000)