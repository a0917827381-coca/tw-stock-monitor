import yfinance as yf
import pandas as pd
from scipy.signal import argrelextrema
import numpy as np
import datetime

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
        .footer { text-align: center; font-size: 0.8em; color: #888; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 台股型態監控</h1>
        {cards_html}
        <div class="footer">最後更新時間 (台灣時間)：{update_time}</div>
    </div>
</body>
</html>
"""

# 將函數多增加一個 stock_name 參數來接收中文名稱
def analyze_stock(ticker, stock_name):
    stock = yf.Ticker(ticker)
    df = stock.history(period="6mo")
    
    # 將 "2330.TW" 去掉 ".TW"，並與中文名組合，例如 "2330-台積電"
    display_title = f"{ticker.replace('.TW', '')}-{stock_name}"
    
    if df.empty:
        return f'<div class="card"><div class="stock-title">{display_title}</div><div class="price-info">無資料</div></div>'
    
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

    support_str = f"近端支撐：{round(supports[-1], 2)}<br>" if len(supports) > 0 else ""
    resist_str = f"近端壓力：{round(resistances[-1], 2)}<br>" if len(resistances) > 0 else ""
    w_alert = '<span class="highlight">⚠️ 疑似 W 底型態已成形！</span>' if is_w_bottom else ""
    css_class = "card w-bottom" if is_w_bottom else "card"

    card_html = f"""
    <div class="{css_class}">
        <div class="stock-title">{display_title}</div>
        <div class="price-info">
            最新收盤價：{current_price}<br>
            {support_str}{resist_str}{w_alert}
        </div>
    </div>
    """
    return card_html

if __name__ == '__main__':
    # 這裡改成「字典(Dictionary)」格式，你可以依樣畫葫蘆，在這裡無限新增你要的股票！
    watch_list = {
        '2330.TW': '台積電',
        '2317.TW': '鴻海',
        '2454.TW': '聯發科',
        '2308.TW': '台達電',  # 新增的範例
        '2881.TW': '富邦金'   # 新增的範例
    }
    
    all_cards = ""
    # 同時把代碼 (ticker) 跟 名稱 (name) 抓出來丟給函數計算
    for ticker, name in watch_list.items():
        all_cards += analyze_stock(ticker, name)
    
    tw_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    final_html = HTML_TEMPLATE.replace('{cards_html}', all_cards).replace('{update_time}', tw_time)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
