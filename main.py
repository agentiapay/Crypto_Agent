from fastapi import FastAPI
from playwright.async_api import async_playwright
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import asyncio

from google import genai
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from pydantic import BaseModel
from prompt_data import Trend_Data, Coins_Data, MA_Data, Volume_Data, Candles_Data

app = FastAPI()

class Trader_Class(BaseModel):
    pair: str
    price: float
    signal: str
    Confidence_Level: int

client = genai.Client(api_key="AIzaSyAxz3kNZLBz2PH124b-pfqVuulj960QvKo")
client1 = AsyncOpenAI(
    api_key="AIzaSyCMpBWF-tOzuVQ9inIyVlPo7VFCJ6b9dd0",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai"
)
model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=client1)

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    "SHIBUSDT", "LTCUSDT", "TRXUSDT", "LINKUSDT", "OPUSDT",
    "PEPEUSDT", "WIFUSDT", "SUIUSDT", "SEIUSDT", "FETUSDT"
]

crypto_signals = []

@app.get("/")
async def get_latest_signal():
    if crypto_signals:
        return JSONResponse(content=jsonable_encoder(crypto_signals[-1]))
    return JSONResponse(content={"message": "No signals yet"}, status_code=404)


@app.get("/capture")
async def capture():
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await context.new_page()

            coin = COINS[0]  # For Vercel, run one coin at a time
            url = f"https://www.binance.com/en/futures/{coin}"
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # allow page render

            screenshot = await page.screenshot(full_page=False)
            await browser.close()

            async def crypto_trader(screenshot_bytes, prompt):
                binance_screenshot = client.files.upload(file=screenshot_bytes)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[binance_screenshot, prompt],
                )
                return response.text

            Trend, Coins, MA, Volume, Candles = await asyncio.gather(
                crypto_trader(screenshot, Trend_Data),
                crypto_trader(screenshot, Coins_Data),
                crypto_trader(screenshot, MA_Data),
                crypto_trader(screenshot, Volume_Data),
                crypto_trader(screenshot, Candles_Data),
            )

            instructions = f"""
You are a highly skilled crypto trading agent equipped with expert-level knowledge, advanced chart reading skills, and strong decision-making logic. 

You must analyze the market with deep insight like a professional trader who considers not just indicators, but also market psychology, other traders’ intentions, risk management, and mind management.

Below are key observations extracted from a recent chart screenshot:

- Market Trend Analysis: {Trend}
- Coin Pair & Current Price: {Coins}
- Moving Averages (MA): {MA}
- Volume Indicator Insights: {Volume}
- Candlestick Pattern (last 3 candles): {Candles}

Now, act like a real-time crypto strategist and give a final decision:
- BUY, SELL, or HOLD
- Confidence level (0-100)
- Pair
- Price
- Signals
"""

            agent = Agent(
                name="Crypto_Trader_Agent",
                instructions=instructions,
                model=model,
                output_type=Trader_Class,
            )

            result = await Runner.run(agent, "give me crypto signals")
            signals = result.final_output
            crypto_signals.append(signals)

            return JSONResponse(content=jsonable_encoder(signals))

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
