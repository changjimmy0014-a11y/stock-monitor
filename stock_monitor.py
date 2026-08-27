import time
import os
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import yfinance as yf

# 優先讀取雲端環境變數，若本機執行沒有設定則使用你原本寫的帳密
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "Changjimmy0014@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "aggvyucarfphwlcl")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "Cshen0525@gmail.com")


# ==================== 監控魚池參數設定 ====================
WATCHLIST = {
    "0050.TW": {"name": "元大台灣50"},
    "006208.TW": {"name": "富邦台50"},
    "00878.TW": {"name": "國泰永續高股息"},
    "0056.TW": {"name": "元大高股息"},
    "2886.TW": {"name": "兆豐金"},
    "00923.TW": {"name": "群益ESG低碳50"},
    "00881.TW": {"name": "國泰台灣5G+"},
    "2330.TW": {"name": "台積電"},
    "2382.TW": {"name": "廣達"},
    "2308.TW": {"name": "台達電"}
}


def send_email_notification(subject, message):
    """透過 Gmail 發送郵件到你的信箱"""
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
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 啟動智慧投資雷達（自動抓取配息中）...")
    print("=" * 65)

    yield_ranking = []

    for stock_id, info in WATCHLIST.items():
        name = info["name"]
        print(f"🔄 正在分析: {name} ({stock_id})...")

        try:
            ticker = yf.Ticker(stock_id)
            df_price = ticker.history(period="1d")
            if df_price.empty:
                print(f"  ❌ {name} 無法取得股價，跳過。")
                continue
            current_price = round(df_price['Close'].iloc[-1], 2)

            dividends = ticker.dividends
            if dividends.empty:
                annual_div = 0.0
            else:
                one_year_ago = pd.Timestamp.now(tz=dividends.index.tz) - pd.DateOffset(years=1)
                recent_divs = dividends[dividends.index >= one_year_ago]
                annual_div = round(recent_divs.sum(), 2)

            current_yield = round((annual_div / current_price) * 100,
                                  2) if current_price > 0 and annual_div > 0 else 0.0

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
        print(f"{'排名':<4} | {'股票名稱':<12} | {'現價(元)':<8} | {'近一年配息(元)':<12} | {'預估殖利率':<10}")
        print("-" * 65)

        for i, item in enumerate(yield_ranking, start=1):
            print(
                f"第 {i:<2}名 | {item['name']:<10} | {item['price']:<8} | {item['annual_div']:<14} | {item['yield_pct']:<8}%")

        print("=" * 65)

        best_stock = yield_ranking[0]
        report_text = f"今日最高殖利率推薦：\n\n"
        report_text += f"⭐ 標的名稱：{best_stock['name']}\n"
        report_text += f"• 現價：{best_stock['price']} 元\n"
        report_text += f"• 近一年配息：{best_stock['annual_div']} 元\n"
        report_text += f"• 預估殖利率：{best_stock['yield_pct']}%\n\n"
        report_text += f"👉 建議開啟永豐 APP 評估進場！"

        print(f"💡 系統推薦：{best_stock['name']} (殖利率 {best_stock['yield_pct']}%)")

        # 執行寄信
        if SENDER_EMAIL != "你的信箱@gmail.com":
            subject = f"📊 【股市雷達日報】今日推薦：{best_stock['name']} (殖利率 {best_stock['yield_pct']}%)"
            send_email_notification(subject, report_text)
        else:
            print("⚠️ 尚未設定真實的 SENDER_EMAIL，略過自動寄信。")
    else:
        print("❌ 未能取得任何有效數據。")

    print("=" * 65)
    input("\n分析完畢！按下 Enter 鍵結束程式...")


if __name__ == "__main__":
    scan_with_auto_dividend()
