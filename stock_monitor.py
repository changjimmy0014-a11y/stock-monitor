import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import yfinance as yf
from google import genai  # 確保使用最新版 SDK

# ==================== 環境變數與密碼設定 ====================
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "Changjimmy0014@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "aqgyyucarfphwlcl")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "Cshen0525@gmail.com")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 初始化新版 AI 用戶端
ai_client = None
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)

WATCHLIST = {
    "0050.TW": {"name": "元大台灣50", "div": 3.0},
    "006208.TW": {"name": "富邦台50", "div": 2.8},
    "00878.TW": {"name": "國泰永續高股息", "div": 1.6},
    "0056.TW": {"name": "元大高股息", "div": 2.2},
    "2886.TW": {"name": "兆豐金", "div": 1.8},
    "00923.TW": {"name": "群益ESG低碳50", "div": 1.1},
    "00881.TW": {"name": "國泰台灣5G+", "div": 1.2},
    "2330.TW": {"name": "台積電", "div": 16.0},
    "2382.TW": {"name": "廣達", "div": 9.0},
    "2308.TW": {"name": "台達電", "div": 6.4}
}


def get_ai_analysis(ticker_symbol, name):
    """具備終極防禦網的 AI 分析模組，自動測試所有模型名稱"""
    if not ai_client:
        return "⚠️ 系統未偵測到 GEMINI_API_KEY，略過 AI 深度分析。"

    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="5d")
        kline_text = "\n".join([f"[{d.strftime('%m-%d')}] 收盤:{row['Close']:.2f}" for d, row in df.iterrows()])

        news_list = stock.news
        news_text = "\n".join([f"- {n.get('title', '')}" for n in news_list[:3]]) if news_list else "無重大新聞"

        prompt = f"""
        你是一位專業、敏銳的台股操盤手。今日系統篩選出的殖利率冠軍是【{name} ({ticker_symbol})】。
        以下是該標的近5日K線：\n{kline_text}\n
        近期新聞：\n{news_text}\n

        請用繁體中文回答以下兩個部分：
        1. 【首選標的解析】：針對【{name} ({ticker_symbol})】給出簡短的盤勢短評、操作建議（含預約單進場價與防守價）。
        2. 【AI 獨家觀點與個股推薦】：除了上述系統硬編碼的清單外，請根據你對目前台股市場趨勢、產業熱點的觀察，額外推薦 1-2 檔你近期看好的「台股個股」（非ETF），並簡述推薦理由。
        """

        # 💡 終極輪詢清單：把最新指示的 3.6 放在首位，備用軍團排在後面
        model_candidates = [
            'gemini-3.6-flash',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-flash-latest',
            'gemini-pro',
            'gemini-1.5-pro'
        ]

        last_error = None
        for model_name in model_candidates:
            try:
                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                continue  # 遇到錯誤不崩潰，直接換下一個模型繼續測

        return f"❌ 所有模型嘗試皆失敗，最後錯誤訊息：{last_error}"

    except Exception as e:
        return f"❌ AI 模組分析失敗：{e}"


def send_email_notification(subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL

        # 這裡設定收件人，如需增加朋友信箱，請用逗號隔開加在後面，例如: [RECEIVER_EMAIL, "friend@gmail.com"]
        receivers_list = [RECEIVER_EMAIL,"b0981155209@gmail.com"]

        msg['To'] = ", ".join(receivers_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receivers_list, msg.as_string())
        server.quit()
        print("✅ 報告與 AI 分析已成功寄出！")
    except Exception as e:
        print(f"❌ 寄信失敗：{e}")


def main():
    print(f"[{datetime.datetime.now().strftime('%m-%d %H:%M')}] 啟動 MCP 股市決策大腦...")
    yield_ranking = []

    for stock_id, info in WATCHLIST.items():
        name = info["name"]
        annual_div = info["div"]
        try:
            df_price = yf.Ticker(stock_id).history(period="1d")
            if not df_price.empty:
                current_price = round(df_price['Close'].iloc[-1], 2)
                current_yield = round((annual_div / current_price) * 100, 2)
                yield_ranking.append({"id": stock_id, "name": name, "price": current_price, "div": annual_div,
                                      "yield_pct": current_yield})
        except:
            pass

    yield_ranking = sorted(yield_ranking, key=lambda x: x['yield_pct'], reverse=True)
    if not yield_ranking:
        return

    top_3 = yield_ranking[:3]
    best_stock = top_3[0]

    report_text = "🏆 今日最高殖利率 Top 3 推薦：\n\n"
    for i, stock in enumerate(top_3, start=1):
        report_text += f"第 {i} 名：{stock['name']} | 現價: {stock['price']} | 預估殖利率: {stock['yield_pct']}%\n"

    report_text += "\n" + "=" * 40 + "\n"
    report_text += f"🧠 【AI 代理人深度解析與個股推薦】\n"
    report_text += "-" * 40 + "\n"

    print(f"正在呼叫 Gemini 分析首選標的並尋找額外個股推薦...")
    ai_report = get_ai_analysis(best_stock['id'], best_stock['name'])
    report_text += ai_report
    report_text += "\n\n👉 建議開啟永豐大戶投 APP，評估是否掛預約單進場！"

    subject = f"🧠 AI 戰報：首選 {best_stock['name']} 暨獨家個股推薦"
    send_email_notification(subject, report_text)


if __name__ == "__main__":
    main()
