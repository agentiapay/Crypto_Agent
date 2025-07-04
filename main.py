# app.py
from fastapi import FastAPI,WebSocket
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import asyncio
from fastapi.encoders import jsonable_encoder

from google import genai
from agents import Agent,Runner,AsyncOpenAI,OpenAIChatCompletionsModel
from pydantic import BaseModel
from prompt_data import Trend_Data,Coins_Data,MA_Data,Volume_Data,Candles_Data
import json
from fastapi import WebSocketDisconnect

class Trader_Class(BaseModel):
  pair:str
  price:float
  signal:str
  Confidence_Level:int
# api keye setip for agent

client = genai.Client(api_key="AIzaSyAxz3kNZLBz2PH124b-pfqVuulj960QvKo")

client1 = AsyncOpenAI(
api_key="AIzaSyCMpBWF-tOzuVQ9inIyVlPo7VFCJ6b9dd0",
base_url="https://generativelanguage.googleapis.com/v1beta/openai"
                      )
model=OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=client1)

app = FastAPI()

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "SHIBUSDT", "LTCUSDT", "TRXUSDT", "LINKUSDT", "OPUSDT",
    "PEPEUSDT", "WIFUSDT", "SUIUSDT", "SEIUSDT", "FETUSDT"
]

SCREENSHOT_PATH = "screenshot.png"

# Globals
playwright = None
browser: Browser = None
context: BrowserContext = None
page: Page = None
crypto_signals = []

# @app.post("/signals")
# async def get_latest_signal(request: Request):
#     if crypto_signals:
#         latest_signal = crypto_signals[-1]
#         return JSONResponse(content=jsonable_encoder(latest_signal))
#     else:
#         return JSONResponse(content={"message": "No signals yet"}, status_code=404)
        
@app.get("capture")
async def capture():
    global playwright, browser, context, page
    print("🚀 Launching browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )
    page = await context.new_page()
    asyncio.create_task(capture_loop())  # Background screenshot loop

async def capture_loop():
    while True:
        for coin in COINS:
            try:
                print(f"🌐 Opening {coin} page...")
                url = f"https://www.binance.com/en/futures/{coin}"
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)  # Ensure full render

                # 📸 Take full page screenshot
                await page.screenshot(path=SCREENSHOT_PATH, full_page=False)
                print(f"📸 Screenshot saved for {coin}")
                await page.close()

                # gemini
                async def crypto_trader(screenshot,prompt):

                    binance_screenshot = client.files.upload(file=screenshot)

                    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[binance_screenshot,prompt
],
)

                    Signals_Data = response.text
                    return Signals_Data

                Trend, Coins, MA, Volume, Candles = await asyncio.gather(
    crypto_trader("screenshot.png", Trend_Data),
    crypto_trader("screenshot.png", Coins_Data),
    crypto_trader("screenshot.png", MA_Data),
    crypto_trader("screenshot.png", Volume_Data),
    crypto_trader("screenshot.png", Candles_Data),
)

                Crypto_Coins_Extracted_Details = f"""
You are a highly skilled crypto trading agent equipped with expert-level knowledge, advanced chart reading skills, and strong decision-making logic. 

You must analyze the market with deep insight like a professional trader who considers not just indicators, but also **market psychology**, **other traders’ intentions**, **risk management**, and **mind management**.

Below are key observations extracted from a recent chart screenshot:

- 📉 **Market Trend Analysis:** {Trend}
- 💰 **Coin Pair & Current Price:** {Coins}
- 📊 **Moving Averages (MA):** {MA}
- 📈 **Volume Indicator Insights:** {Volume}
- 🕯️ **Candlestick Pattern (last 3 candles):** {Candles}

---

Now, act like a real-time crypto strategist. Ask yourself:

- What might **other traders** (buyers/sellers) be planning right now based on this market behavior?
- Is this a **trap**, **genuine breakout**, or **fakeout**?
- Would entering a trade here be **low risk** and **high probability**?
- How can I **protect capital** and still **maximize profit**?

❗ Based on this, give a **final decision**:
- 🟢 BUY
- 🔴 SELL
- ⏸️ HOLD

Along with your decision, include:
1. A **confidence level** from 0 to 100.
2. A **Pair**
3. A **price** 
4. Your **Signals** 
note: don't give 'Perp' with coin pair.


Be decisive, think deeply, and aim to give a **profitable signal**.
"""

                # agent
                Crypto_Trader_Agent = Agent(
    name="Crypto_Trader_Agent",
    instructions=Crypto_Coins_Extracted_Details,
    model=model,
    output_type=Trader_Class,
)

                result = await Runner.run(Crypto_Trader_Agent,"give me crypto signals")
                global signals
                signals = result.final_output
                print(signals)
                crypto_signals.append(signals)

            except Exception as e:
                print(f"❌ Failed for {coin}: {e}")
            await asyncio.sleep(60)  # 5-minute wait before next coin

        print("🔁 All coins done. Restarting...\n")

@app.get("/")
def Crypto_Agent():
  
  return {"trader":crypto_signals[-1]}

