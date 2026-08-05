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
        <p style="text-align:center; color:#666;">（已過濾，僅顯示成形標的）</p>
        {cards_html}
        <div class="footer">最後更新時間 (台灣時間)：{update_time}</div>
    </div>
</body>
</html>
"""

def analyze_stock(ticker, stock_name):
    stock = yf.Ticker(ticker)
    # 變更為抓取過去 1 年的「週 K 線 (interval='1wk')」
    df = stock.history(period="1y", interval="1wk")
    
    if df.empty:
        return "" # 如果沒抓到資料，直接回傳空字串 (不顯示)
    
    prices = df['Close'].values
    
    # 週 K 的比較週期可以稍微縮短，這裡設為前後 3 週
    local_min_idx = argrelextrema(prices, np.less, order=3)[0]
    local_max_idx = argrelextrema(prices, np.greater, order=3)[0]
    
    supports = prices[local_min_idx]
    resistances = prices[local_max_idx]
    current_price = round(prices[-1], 2)
    
    is_w_bottom = False
    if len(supports) >= 2:
        last_low = supports[-1]
        prev_low = supports[-2]
        # 判斷 W 底：兩個低點相近，且目前股價已反彈
        if abs(last_low - prev_low) / prev_low < 0.05 and current_price > last_low:
            is_w_bottom = True

    # 核心邏輯：如果「不是」W底，就直接結束，什麼都不印！
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
    # 這裡以台灣 50 成分股的部分名單為例，避免被 Yahoo 封鎖
    # 你可以自行擴充這個字典，建議總數控制在 100 檔以內
    watch_list = {
        '2330.TW': '台積電', '2317.TW': '鴻海', '2454.TW': '聯發科',
        '2308.TW': '台達電', '2881.TW': '富邦金', '2891.TW': '中信金',
        '2382.TW': '廣達', '2303.TW': '聯電', '2882.TW': '國泰金',
        '3231.TW': '緯創', '2603.TW': '長榮', '2886.TW': '兆豐金'
    }
    
    all_cards = ""
    for ticker, name in watch_list.items():
        # 加上 try-except 防止單一股票抓取失敗導致整個程式崩潰
        try:
            all_cards += analyze_stock(ticker, name)
        except:
            continue
    
    # 如果全市場今天都沒有 W 底，給一個提示訊息
    if all_cards == "":
        all_cards = '<div class="empty-msg">目前監控名單中，無任何股票符合週 K 線 W 底型態。持續等待機會！</div>'
        
    tw_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    final_html = HTML_TEMPLATE.replace('{cards_html}', all_cards).replace('{update_time}', tw_time)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
