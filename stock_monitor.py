import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import yfinance as yf

# ==================== Email 參數設定 ====================
# 優先讀取雲端環境變數，若本機執行沒有設定則使用你原本寫的帳密
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "你的信箱@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "你的16碼應用程式密碼")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "你的收信信箱@gmail.com")

# ==================== 監控魚池參數設定 (加入真實配息) ====================
WATCHLIST = {
    "0050.TW":   {"name": "元大台灣50", "div": 3.0},     
    "006208.TW": {"name": "富邦台50", "div": 2.8},       
    "00878.TW":  {"name": "國泰永續高股息", "div": 1.6}, 
    "0056.TW":   {"name": "元大高股息", "div": 2.2},     
    "2886.TW":   {"name": "兆豐金", "div": 1.8},         
    "00923.TW":  {"name": "群益ESG低碳50", "div": 1.1},  
    "00881.TW":  {"name": "國泰台灣5G+", "div": 1.2},    
    "2330.TW":   {"name": "台積電", "div": 16.0},         
    "2382.TW":   {"name": "廣達", "div": 9.0},           
    "2308.TW":   {"name": "台達電", "div": 6.4}          
}

def send_email_notification(subject, message):
    """透過 Gmail 發送郵件"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ Email 通知已成功寄出！")
    except Exception as e:
        print(f"❌ 寄信失敗：{e}")

def scan_with_auto_dividend():
    print("=" * 65)
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 啟動智慧投資雷達...")
    print("=" * 65)
    
    yield_ranking = []

    for stock_id, info in WATCHLIST.items():
        name = info["name"]
        annual_div = info["div"]  # 修正：直接讀取我們設定好的正確配息
        
        print(f"🔄 正在分析: {name} ({stock_id})...")
        
        try:
            ticker = yf.Ticker(stock_id)
            df_price = ticker.history(period="1d")
            if df_price.empty:
                print(f"  ❌ {name} 無法取得股價，跳過。")
                continue
            current_price = round(df_price['Close'].iloc[-1], 2)
            
            # 計算殖利率
            current_yield = round((annual_div / current_price) * 100, 2) if current_price > 0 else 0.0
            
            yield_ranking.append({
                "name": name,
                "price": current_price,
                "annual_div": annual_div,
                "yield_pct": current_yield
            })
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 處理 {name} 時發生錯誤：{e}")

    # 依照殖利率排序
    yield_ranking = sorted(yield_ranking, key=lambda x: x['yield_pct'], reverse=True)

    # 總結報告與寄信
    print("\n" + "=" * 65)
    print("🏆 【智慧配息掃描與推薦報告】 🏆")
    
    if yield_ranking:
        print(f"{'排名':<4} | {'股票名稱':<12} | {'現價(元)':<8} | {'預估配息(元)':<12} | {'預估殖利率':<10}")
        print("-" * 65)
        
        for i, item in enumerate(yield_ranking, start=1):
            print(f"第 {i:<2}名 | {item['name']:<10} | {item['price']:<8} | {item['annual_div']:<14} | {item['yield_pct']:<8}%")
            
        print("=" * 65)
        
        # 修正：將前 3 名都整理進 Email 裡面
        top_3 = yield_ranking[:3]
        report_text = f"今日最高殖利率 Top 3 推薦：\n\n"
        
        for i, stock in enumerate(top_3, start=1):
            report_text += f"🏆 第 {i} 名：{stock['name']}\n"
            report_text += f"• 現價：{stock['price']} 元\n"
            report_text += f"• 預估配息：{stock['annual_div']} 元\n"
            report_text += f"• 預估殖利率：{stock['yield_pct']}%\n\n"
            
        report_text += f"👉 建議開啟永豐大戶投 APP，善用「盤後零股」預約進場！"
        
        best_stock = top_3[0]
        print(f"💡 系統首選推薦：{best_stock['name']} (殖利率 {best_stock['yield_pct']}%)")
        
        # 執行寄信
        if "gmail.com" in SENDER_EMAIL:
            subject = f"📊 【股市雷達日報】今日 Top 3 推薦！首選 {best_stock['name']} ({best_stock['yield_pct']}%)"
            send_email_notification(subject, report_text)
        else:
            print("⚠️ 尚未設定真實的 SENDER_EMAIL，請確認環境變數。")
    else:
        print("❌ 未能取得任何有效數據。")
        
    print("=" * 65)
    # 修正：這裡已經刪除 input()，讓 GitHub Actions 可以順利亮綠燈結束！

if __name__ == "__main__":
    scan_with_auto_dividend()
