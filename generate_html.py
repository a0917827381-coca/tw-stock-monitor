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
        h1 { text-align: center; color: #333; font-size: 1.5em; }
        
        /* 篩選器介面設計 */
        .filters { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .filters input, .filters select { padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 1em; flex: 1; min-width: 140px; }
        
        /* 卡片設計與顏色區分 */
        .card { border-left: 5px solid #ccc; background: #fff; padding: 15px; margin-bottom: 15px; border-radius: 5px; display: block; }
        .card.w-forming { border-left-color: #ffc107; background: #fff8e1; } /* 黃色：快成形 */
        .card.w-formed { border-left-color: #28a745; background: #e8f5e9; } /* 綠色：已成形 */
        
        .stock-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .price-info { color: #555; line-height: 1.6; }
        .tag-forming { color: #d9534f; font-weight: bold; }
        .tag-formed { color: #28a745; font-weight: bold; }
        .footer { text-align: center; font-size: 0.8em; color: #888; margin-top: 20px; }
        .empty-msg { text-align: center; color: #888; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 台股「週K線」W底潛力股</h1>
        
        <!-- 搜尋與篩選器 -->
        <div class="filters">
            <input type="text" id="searchInput" placeholder="🔍 輸入代碼或名稱 (如: 台積電)" onkeyup="filterCards()">
            <select id="statusFilter" onchange="filterCards()">
                <option value="all">📊 顯示全部型態</option>
                <option value="formed">🚀 只看【已成形】(突破頸線)</option>
                <option value="forming">⚠️ 只看【快成形】(右腳反彈)</option>
            </select>
        </div>

        <div id="cardContainer">
            {cards_html}
        </div>
        
        <div class="footer">最後更新時間 (台灣時間)：{update_time}</div>
    </div>

    <!-- JavaScript 篩選邏輯 -->
    <script>
    function filterCards() {
        var searchText = document.getElementById('searchInput').value.toLowerCase();
        var statusFilter = document.getElementById('statusFilter').value;
        var cards = document.querySelectorAll('.card');
        
        cards.forEach(function(card) {
            var text = card.textContent.toLowerCase();
            var status = card.getAttribute('data-status');
            
            var matchText = text.includes(searchText);
            var matchStatus = (statusFilter === 'all') || (status === statusFilter);
            
            // 同時符合文字搜尋與狀態篩選，才顯示卡片
            if (matchText && matchStatus) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
    </script>
</body>
</html>
"""

def get_twse_all_stocks():
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    stock_dict = {}
    try:
        response = requests.get(url)
        data = response.json()
        for item in data:
            code = item['Code']
            name = item['Name']
            if len(code) == 4 and code.isdigit():
                stock_dict[f"{code}.TW"] = name
        return stock_dict
    except Exception as e:
        print(f"抓取清單失敗: {e}")
        return {}

def analyze_stock(ticker, stock_name):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y", interval="1wk")
    
    if df.empty or len(df) < 10:
        return ""
    
    prices = df['Close'].values
    local_min_idx = argrelextrema(prices, np.less, order=3)[0]
    
    is_forming = False
    is_formed = False
    neckline = 0

    if len(local_min_idx) >= 2:
        last_low_idx = local_min_idx[-1]
        prev_low_idx = local_min_idx[-2]
        
        last_low = prices[last_low_idx]
        prev_low = prices[prev_low_idx]
        
        # 計算「頸線」：兩次低點之間的最高價
        if prev_low_idx < last_low_idx:
            between_prices = prices[prev_low_idx:last_low_idx+1]
            if len(between_prices) > 0:
                neckline = np.max(between_prices)
                
        # 條件 1：兩個低點相近 (誤差 5% 內)
        if abs(last_low - prev_low) / prev_low < 0.05:
            # 條件 2：目前價格是否已經從右腳反彈
            if current_price := round(prices[-1], 2) > last_low:
                current_price = round(prices[-1], 2)
                # 條件 3：是否已經突破頸線
                if neckline > 0 and current_price > neckline:
                    is_formed = True
                else:
                    is_forming = True

    # 如果什麼都不是，直接丟棄
    if not (is_forming or is_formed):
        return ""

    display_title = f"{ticker.replace('.TW', '')}-{stock_name}"
    
    # 根據狀態決定卡片的顏色與標籤
    status_class = "w-formed" if is_formed else "w-forming"
    data_status = "formed" if is_formed else "forming"
    tag_html = '<span class="tag-formed">🚀 已成形 (已突破頸線)</span>' if is_formed else '<span class="tag-forming">⚠️ 快成形 (右腳剛反彈)</span>'
    
    neckline_str = f"關鍵頸線：{round(neckline, 2)}<br>" if neckline > 0 else ""
    support_str = f"右腳支撐：{round(last_low, 2)}<br>"

    card_html = f"""
    <div class="card {status_class}" data-status="{data_status}">
        <div class="stock-title">{display_title}</div>
        <div class="price-info">
            最新週收盤價：{current_price}<br>
            {neckline_str}{support_str}
            {tag_html}
        </div>
    </div>
    """
    return card_html

if __name__ == '__main__':
    watch_list = get_twse_all_stocks()
    watch_items = list(watch_list.items())
    
    all_cards = ""
    for ticker, name in watch_items:
        try:
            all_cards += analyze_stock(ticker, name)
            time.sleep(0.5) 
        except:
            continue
    
    if all_cards == "":
        all_cards = '<div class="empty-msg">目前上市普通股中，無任何股票符合週 K 線 W 底型態。</div>'
        
    tw_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    final_html = HTML_TEMPLATE.replace('{cards_html}', all_cards).replace('{update_time}', tw_time)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
