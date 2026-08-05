import yfinance as yf
import pandas as pd
from scipy.signal import argrelextrema
import numpy as np
import datetime
import requests
import time

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的台股週 K 監控儀表板</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        .card { border-left: 5px solid #ffc107; background: #fff8e1; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
        .stock-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .price-info { color: #555; line-height: 1.6; }
        .highlight { color: #d9534f; font-weight: bold; }
        .footer { text-align: center; font-size: 0.8em; color: #888; margin-top: 20px; }
        .empty-msg { text-align: center; color: #888; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 台股「週K線」W底潛力股</h1>
        <p style="text-align:center; color:#666;">（已自動掃描上市普通股，僅顯示成形標的）</p>
        {cards_html}
        <div class="footer">最後更新時間 (台灣時間)：{update_time}</div>
    </div>
</body>
</html>
"""

def get_twse_all_stocks():
    """自動從證交所開放 API 抓取所有上市股票名單"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    stock_dict = {}
    try:
        response = requests.get(url)
        data = response.json()
        
        for item in data:
            code = item['Code']
            name = item['Name']
            # 過濾條件：只抓取長度為 4 碼的純數字代碼 (排除權證、ETF、特別股等)
            if len(code) == 4 and code.isdigit():
                stock_dict[f"{code}.TW"] = name
        return stock_dict
    except Exception as e:
        print(f"抓取清單失敗: {e}")
        return {}

def analyze_stock(ticker, stock_name):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y", interval="1wk")
    
    if df.empty:
        return ""
    
    prices = df['Close'].values
    
    # 這裡必須加一個防呆機制，避免剛上市不到 1 個月的股票因為資料太少而報錯
    if len(prices) < 10:
        return ""

    local_min_idx = argrelextrema(prices, np.less, order=3)[0]
    local_max_idx = argrelextrema(prices, np.greater, order=3)[0]
    
    supports = prices[local_min_idx]
    resistances = prices[local_max_idx]
    current_price = round(prices[-1], 2)
    
    is_w_bottom = False
    if len(supports) >= 2:
        last_low = supports[-1]
        prev_low = supports[-2]
        if abs(last_low - prev_low) / prev_low < 0.05 and current_price > last_low:
            is_w_bottom = True

    if not is_w_bottom:
        return ""

    display_title = f"{ticker.replace('.TW', '')}-{stock_name}"
    support_str = f"近端支撐：{round(supports[-1], 2)}<br>" if len(supports) > 0 else ""
    resist_str = f"近端壓力：{round(resistances[-1], 2)}<br>" if len(resistances) > 0 else ""

    card_html = f"""
    <div class="card">
        <div class="stock-title">{display_title}</div>
        <div class="price-info">
            最新週收盤價：{current_price}<br>
            {support_str}{resist_str}
            <span class="highlight">⚠️ 週 K 級別 W 底浮現！</span>
        </div>
    </div>
    """
    return card_html

if __name__ == '__main__':
    # 1. 啟動時，先去證交所把一千多檔股票名單自動抓回來！
    watch_list = get_twse_all_stocks()
    
    # ⚠️【重要防護機制】⚠️
    # 雖然抓到了 1000 多檔，但為了避免被 Yahoo 瞬間封鎖 IP
    # 我們在迴圈內強制加入 time.sleep(0.5) 讓機器人每查一檔就休息半秒
    watch_items = list(watch_list.items())
    
    all_cards = ""
    for ticker, name in watch_items:
        try:
            all_cards += analyze_stock(ticker, name)
            time.sleep(0.5) # 這是掃描全市場必須付出的時間代價
        except:
            continue
    
    if all_cards == "":
        all_cards = '<div class="empty-msg">目前上市普通股中，無任何股票符合週 K 線 W 底型態。持續等待機會！</div>'
        
    tw_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    final_html = HTML_TEMPLATE.replace('{cards_html}', all_cards).replace('{update_time}', tw_time)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
