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
        
        .filters { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .filters input, .filters select { padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 1em; flex: 1; min-width: 140px; }
        
        .card { border-left: 5px solid #ccc; background: #fff; padding: 15px; margin-bottom: 15px; border-radius: 5px; display: block; }
        .card.w-forming { border-left-color: #ffc107; background: #fff8e1; } 
        .card.w-formed { border-left-color: #28a745; background: #e8f5e9; } 
        .card.w-none { border-left-color: #999; background: #f1f1f1; opacity: 0.8; }
        
        .stock-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .stock-category { font-size: 0.75em; color: #fff; background-color: #555; padding: 3px 6px; border-radius: 4px; margin-left: 8px; vertical-align: middle; }
        .price-info { color: #555; line-height: 1.6; }
        .tag-forming { color: #d9534f; font-weight: bold; }
        .tag-formed { color: #28a745; font-weight: bold; }
        .tag-none { color: #666; font-style: italic; }
        
        .btn-group { display: flex; gap: 10px; margin-top: 15px; }
        .chart-btn { flex: 1; padding: 10px 12px; background-color: #2962FF; color: white; border: none; border-radius: 4px; text-align: center; text-decoration: none; font-size: 0.9em; font-weight: bold; transition: opacity 0.2s; }
        .chart-btn:hover { opacity: 0.8; }
        .chart-btn.yahoo { background-color: #720e9e; }
        
        .footer { text-align: center; font-size: 0.8em; color: #888; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 台股「週K線」W底潛力股</h1>
        
        <div class="filters">
            <input type="text" id="searchInput" placeholder="🔍 搜尋代碼或名稱 (未達標也會顯示)" onkeyup="filterCards()">
            <select id="categoryFilter" onchange="filterCards()">
                <option value="all">📁 所有產業分類</option>
                <option value="電子科技股">💻 電子科技股</option>
                <option value="金融保險股">🏦 金融保險股</option>
                <option value="傳統產業與其他">🏭 傳統產業與其他</option>
            </select>
            <select id="statusFilter" onchange="filterCards()">
                <option value="all">📊 顯示成形與快成形</option>
                <option value="formed">🚀 只看【已成形】</option>
                <option value="forming">⚠️ 只看【快成形】</option>
            </select>
        </div>

        <div id="cardContainer">
            {cards_html}
        </div>
        
        <div class="footer">最後更新時間 (台灣時間)：{update_time}</div>
    </div>

    <script>
    function filterCards() {
        var searchText = document.getElementById('searchInput').value.toLowerCase().trim();
        var statusFilter = document.getElementById('statusFilter').value;
        var categoryFilter = document.getElementById('categoryFilter').value;
        var cards = document.querySelectorAll('.card');
        
        cards.forEach(function(card) {
            var text = card.querySelector('.stock-title').textContent.toLowerCase();
            var status = card.getAttribute('data-status');
            var category = card.getAttribute('data-category');
            
            var matchText = text.includes(searchText);
            var matchCategory = (categoryFilter === 'all') || (category === categoryFilter);
            
            if (searchText !== "") {
                if (matchText && matchCategory) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            } else {
                var matchStatus = false;
                if (statusFilter === 'all' && (status === 'formed' || status === 'forming')) {
                    matchStatus = true;
                } else if (status === statusFilter) {
                    matchStatus = true;
                }
                
                if (matchStatus && matchCategory) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            }
        });
    }
    
    window.onload = filterCards;
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

def get_category(ticker):
    code = ticker.split('.')[0]
    if code.startswith('28'):
        return '金融保險股'
    tech_prefixes = ('23','24','30','31','32','33','34','35','36','37','49','52','53','54','61','62','64','65','80','81','82','66','84')
    if code.startswith(tech_prefixes):
        return '電子科技股'
    return '傳統產業與其他'

def analyze_stock(ticker, stock_name):
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y", interval="1wk")
    
    category = get_category(ticker)
    raw_code = ticker.replace('.TW', '')
    display_title = f"{raw_code}-{stock_name}"
    
    if df.empty or len(df) < 10:
        return "" 
    
    prices = df['Close'].values
    local_min_idx = argrelextrema(prices, np.less, order=3)[0]
    
    is_forming = False
    is_formed = False
    neckline = 0
    last_low = 0
    current_price = round(prices[-1], 2)

    if len(local_min_idx) >= 2:
        last_low_idx = local_min_idx[-1]
        prev_low_idx = local_min_idx[-2]
        
        last_low = prices[last_low_idx]
        prev_low = prices[prev_low_idx]
        
        if prev_low_idx < last_low_idx:
            between_prices = prices[prev_low_idx:last_low_idx+1]
            if len(between_prices) > 0:
                neckline = np.max(between_prices)
                
        if abs(last_low - prev_low) / prev_low < 0.05:
            if current_price > last_low:
                if neckline > 0 and current_price > neckline:
                    is_formed = True
                else:
                    is_forming = True

    if is_formed:
        status_class = "w-formed"
        data_status = "formed"
        tag_html = '<span class="tag-formed">🚀 已成形 (已突破頸線)</span>'
        detail_str = f"關鍵頸線：{round(neckline, 2)}<br>右腳支撐：{round(last_low, 2)}<br>"
    elif is_forming:
        status_class = "w-forming"
        data_status = "forming"
        tag_html = '<span class="tag-forming">⚠️ 快成形 (右腳剛反彈)</span>'
        detail_str = f"關鍵頸線：{round(neckline, 2)}<br>右腳支撐：{round(last_low, 2)}<br>"
    else:
        status_class = "w-none"
        data_status = "none"
        tag_html = '<span class="tag-none">❌ 此股票目前未達 W 底標準</span>'
        detail_str = ""

    display_style = "display: none;" if data_status == "none" else ""

    card_html = f"""
    <div class="card {status_class}" data-status="{data_status}" data-category="{category}" style="{display_style}">
        <div class="stock-title">{display_title} <span class="stock-category">{category}</span></div>
        <div class="price-info">
            最新週收盤價：{current_price}<br>
            {detail_str}
            {tag_html}
        </div>
        <div class="btn-group">
            <a href="https://tw.tradingview.com/chart/?symbol=TWSE:{raw_code}" target="_blank" class="chart-btn">📊 TradingView K線</a>
            <a href="https://tw.stock.yahoo.com/quote/{raw_code}" target="_blank" class="chart-btn yahoo">🟣 Yahoo 綜合資訊</a>
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
            
    tw_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    final_html = HTML_TEMPLATE.replace('{cards_html}', all_cards).replace('{update_time}', tw_time)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
