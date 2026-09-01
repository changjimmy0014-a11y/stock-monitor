import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import yfinance as yf
from google import genai
from google.genai import types

# ==================== 環境變數與密碼設定 ====================
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "")

# 💡 請在下方引號中貼入真實的 API Key（例如 "AIzaSy..."）
RAW_KEYS = [
    os.environ.get("GEMINI_API_KEY", ""),
    os.environ.get("GEMINI_API_KEY_BACKUP", "")
]

# 自動過濾無效金鑰與預設提示字串
GEMINI_API_KEYS = [k for k in RAW_KEYS if k and not k.startswith("在此處貼上")]

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
    """具備 Google 即時搜尋能力與多重模型/Key 自動備援機制的 AI 決策模組"""
    if not GEMINI_API_KEYS:
        return "⚠️ 系統未檢測到有效的 GEMINI_API_KEY，請在 RAW_KEYS 處填入 API 金鑰。"

    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="5d")
        kline_text = "\n".join([f"[{d.strftime('%m-%d')}] 收盤:{row['Close']:.2f}" for d, row in df.iterrows()])

        news_list = stock.news
        news_text = "\n".join([f"- {n.get('title', '')}" for n in news_list[:3]]) if news_list else "無重大新聞"

        prompt = f"""
        你是一位專業、具備即時資訊檢索能力的台股操盤手。今日系統篩選出的殖利率冠軍是【{name} ({ticker_symbol})】。
        以下是該標的近5日K線：\n{kline_text}\n
        近期新聞：\n{news_text}\n

        請用繁體中文回答以下三個部分：
        1. 【首選存股解析】：針對【{name} ({ticker_symbol})】給出簡短的盤勢短評、操作建議（含預約單進場價與防守價）。

        2. 【市場多空雷達 (動態搜尋)】：請利用你的網路搜尋能力，檢索「今日台股 焦點新聞 營收 醜聞」等最新資訊。跳脫原本的清單，找出：
           - 🔥 利多潛力股 (1~2檔)：近期發布好消息（如營收創高、新產品發表、接到大單）預期股價看漲的個股，並附上新聞原因。
           - ⚠️ 利空避雷針 (1~2檔)：近期爆出壞消息（如財報不佳、高層醜聞、掉單）預期股價看跌或建議避開的個股，並附上新聞原因。

        3. 【明日當沖雷達】：依據今日盤面資金流向與爆量強勢股，推薦 1 檔適合「明日早盤當沖（或隔日沖）」的標的。請務必給出明確的「預估進場價區間」、「目標停利價」與「嚴格停損價」，並簡述當沖理由。
        """

        # 📋 完整的四階備援模型清單（由最新版依序降級試驗）
        model_candidates = [
            'gemini-3.6-flash',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-1.5-flash'
        ]

        last_error = None

        # 雙層備援機制：外層輪替 Key，內層依序嘗試模型
        for api_key in GEMINI_API_KEYS:
            try:
                ai_client = genai.Client(api_key=api_key)

                for model_name in model_candidates:
                    try:
                        config = types.GenerateContentConfig(
                            tools=[{"google_search": {}}],
                            temperature=0.7
                        )

                        response = ai_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            print(f"✅ 成功使用模型 [{model_name}] 產出分析報告！")
                            return response.text
                    except Exception as model_err:
                        last_error = model_err
                        print(f"⚠️ 模型 [{model_name}] 呼叫失敗: {model_err}")
                        time.sleep(1.5)  # 微幅延遲避開 API Rate Limit (429)
                        continue

            except Exception as key_err:
                last_error = key_err
                print(f"⚠️ API Key (...{api_key[-4:]}) 失敗，切換至下一組 Key...")
                continue

        return f"❌ 所有 API Key 及模型嘗試皆失敗，最後錯誤訊息：{last_error}"

    except Exception as e:
        return f"❌ AI 模組分析失敗：{e}"


def send_email_notification(subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL

        receivers_list = [RECEIVER_EMAIL, "b0981155209@gmail.com"]

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

    report_text = "🏆 今日最高殖利率 Top 3 推薦 (防守型存股)：\n\n"
    for i, stock in enumerate(top_3, start=1):
        report_text += f"第 {i} 名：{stock['name']} | 現價: {stock['price']} | 預估殖利率: {stock['yield_pct']}%\n"

    report_text += "\n" + "=" * 40 + "\n"
    report_text += f"🧠 【AI 代理人市場深度解析與多空雷達】\n"
    report_text += "-" * 40 + "\n"

    print(f"正在呼叫 Gemini 連線網路搜尋最新市場動態...")
    ai_report = get_ai_analysis(best_stock['id'], best_stock['name'])
    report_text += ai_report

    report_text += "\n\n" + "=" * 40 + "\n"
    report_text += "⏰ 【大戶投零股作戰時間表】\n"
    report_text += "▶ 方案A (盤中零股)：13:30 前完成掛單 (依據即時跳動價格撮合)\n"
    report_text += "▶ 方案B (盤後零股)：13:40 ~ 14:30 掛單 (只能以當天「收盤價」進行單一價格撮合)\n\n"
    report_text += "⚠️ 當沖與避雷提醒：AI 推薦之當沖標的為「明日早盤」之規劃；利空標的請檢查自身持股，適時避開風險！"

    subject = f"🧠 MCP 戰報：首選 {best_stock['name']} 暨動態多空雷達"
    send_email_notification(subject, report_text)


if __name__ == "__main__":
    main()
